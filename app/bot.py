"""Telegram bot. Run with:  python -m app.bot"""
import asyncio
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app import config
from app.llm import ModelError
from app.pipeline import explain
from app.prepare import UnsupportedFile

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("samjho")

TEXT = {
    "hi": {
        "start": ("🙏 Namaste! Main Samjho hoon.\n\n"
                  "Kisi bhi bill, bank letter, tax notice ya sarkari kaagaz ki photo ya PDF bhejiye. "
                  "Main simple bhasha mein bataunga: ye kya hai, aapko kya karna hai, aur kab tak.\n\n"
                  "🔒 Aapki photo save nahi hoti. Padhne ke baad turant hata di jaati hai.\n"
                  "Bhasha badalne ke liye: /lang"),
        "reading": "📖 Padh raha hoon... 10-20 second lagenge.",
        "send_doc": "Kripya document ki photo ya PDF bhejiye 📄",
        "error": "😕 Abhi samajh nahi paaya. Thodi der baad dobara koshish karein.",
        "lang": "Bhasha: Hindi ✅  (English ke liye /lang en)",
        "too_big": "File bahut badi hai (max {mb} MB).",
    },
    "en": {
        "start": ("🙏 Hi! I'm Samjho.\n\n"
                  "Send a photo or PDF of any bill, bank letter, tax notice or government document. "
                  "I'll tell you in simple words what it is, what you need to do, and by when.\n\n"
                  "🔒 Your photo is never saved. It is deleted right after reading.\n"
                  "Change language: /lang"),
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


def main() -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN in .env")
    config.llm_api_key()  # fail fast if the model key is missing
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lang", set_lang))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE | filters.Document.PDF, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    log.info("Samjho bot running. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
