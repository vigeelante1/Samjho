"""Telegram bot.

Local development (polling):   python -m app.bot
Online (webhook):              handled by app/api.py when PUBLIC_URL / RENDER_EXTERNAL_URL is set
"""
import asyncio
import hashlib
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app import config
from app.llm import ModelError
from app.pipeline import explain
from app.prepare import UnsupportedFile

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # don't log request URLs (they contain the bot token)
log = logging.getLogger("samjho")

TEXT = {
    "hi": {
        "start": ("🙏 नमस्ते! मैं Samjho हूँ।\n\n"
                  "किसी भी बिल, बैंक लेटर, टैक्स नोटिस या सरकारी कागज़ की फ़ोटो या PDF भेजिए। "
                  "मैं आसान भाषा में बताऊँगा: यह क्या है, आपको क्या करना है, और कब तक।\n\n"
                  "🔒 आपकी फ़ोटो सेव नहीं होती। पढ़ने के बाद तुरंत हटा दी जाती है।\n"
                  "English के लिए: /lang"),
        "reading": "📖 पढ़ रहा हूँ... 10-20 सेकंड लगेंगे।",
        "send_doc": "कृपया दस्तावेज़ की फ़ोटो या PDF भेजिए 📄",
        "error": "😕 अभी समझ नहीं पाया। थोड़ी देर बाद दोबारा कोशिश करें।",
        "lang": "भाषा: हिंदी ✅  (English के लिए /lang en)",
        "too_big": "फ़ाइल बहुत बड़ी है (अधिकतम {mb} MB)।",
    },
    "en": {
        "start": ("🙏 Hi! I'm Samjho.\n\n"
                  "Send a photo or PDF of any bill, bank letter, tax notice or government document. "
                  "I'll tell you in simple words what it is, what you need to do, and by when.\n\n"
                  "🔒 Your photo is never saved. It is deleted right after reading.\n"
                  "हिंदी के लिए: /lang"),
        "reading": "📖 Reading... this takes 10-20 seconds.",
        "send_doc": "Please send a photo or PDF of the document 📄",
        "error": "😕 Couldn't process that right now. Please try again in a bit.",
        "lang": "Language: English ✅  (for Hindi: /lang hi)",
        "too_big": "File is too large (max {mb} MB).",
    },
}


def _lang(ctx: ContextTypes.DEFAULT_TYPE) -> str:
    return ctx.user_data.get("lang", config.DEFAULT_LANG)


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(TEXT[_lang(ctx)]["start"])


async def set_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    arg = (ctx.args[0].lower() if ctx.args else "")
    new = arg if arg in TEXT else ("en" if _lang(ctx) == "hi" else "hi")  # bare /lang toggles
    ctx.user_data["lang"] = new
    await update.message.reply_text(TEXT[new]["lang"])


async def handle_file(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    lang, msg = _lang(ctx), update.message
    if msg.photo:
        tg_file, filename, mime = msg.photo[-1], "photo.jpg", "image/jpeg"   # largest size
    else:
        tg_file, filename, mime = msg.document, msg.document.file_name or "", msg.document.mime_type or ""

    if (tg_file.file_size or 0) > config.MAX_UPLOAD_MB * 1024 * 1024:
        await msg.reply_text(TEXT[lang]["too_big"].format(mb=config.MAX_UPLOAD_MB))
        return

    status = await msg.reply_text(TEXT[lang]["reading"])
    try:
        data = bytes(await (await tg_file.get_file()).download_as_bytearray())
        out = await asyncio.to_thread(explain, data, filename, mime, lang)  # model call is blocking
        await status.edit_text(out["message"])
    except UnsupportedFile as exc:
        await status.edit_text(f"⚠️ {exc}")
    except ModelError as exc:
        log.warning("model error: %s", exc)
        await status.edit_text(TEXT[lang]["error"])
    except Exception:
        log.exception("unexpected error")
        await status.edit_text(TEXT[lang]["error"])


async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(TEXT[_lang(ctx)]["send_doc"])


def webhook_secret() -> str:
    """Secret Telegram sends back on every webhook call, so random people can't post fake updates."""
    return config.WEBHOOK_SECRET or hashlib.sha256(config.TELEGRAM_BOT_TOKEN.encode()).hexdigest()[:48]


def build_application(webhook: bool = False) -> Application:
    if not config.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN in .env")
    builder = Application.builder().token(config.TELEGRAM_BOT_TOKEN).concurrent_updates(True)
    if webhook:
        builder = builder.updater(None)  # FastAPI receives the updates instead
    app = builder.build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lang", set_lang))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE | filters.Document.PDF, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    return app


def main() -> None:
    config.llm_api_key()  # fail fast if the model key is missing
    app = build_application()
    log.info("Samjho bot running (polling). Press Ctrl+C to stop.")
    # drop_pending_updates + deleting any webhook lets you run locally even after deploying
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
