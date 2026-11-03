"""Web API + upload page, and (when deployed) the Telegram webhook.

Local:   uvicorn app.api:app --reload
Online:  uvicorn app.api:app --host 0.0.0.0 --port $PORT   (with PUBLIC_URL or RENDER_EXTERNAL_URL set)
"""
import asyncio
import hmac
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from telegram import Update

from app import config
from app.llm import ModelError
from app.pipeline import explain
from app.prepare import UnsupportedFile

log = logging.getLogger("samjho.api")
WEB_DIR = Path(__file__).resolve().parent.parent / "web"
WEBHOOK_PATH = "/telegram/webhook"

_tg_app = None            # telegram Application, only in webhook mode
_tasks: set = set()       # keep references to running update tasks


def webhook_enabled() -> bool:
    return bool(config.TELEGRAM_BOT_TOKEN and config.PUBLIC_URL)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _tg_app
    if webhook_enabled():
        from app.bot import build_application, webhook_secret
        _tg_app = build_application(webhook=True)
        await _tg_app.initialize()
        await _tg_app.start()
        await _tg_app.bot.set_webhook(
            url=config.PUBLIC_URL + WEBHOOK_PATH,
            secret_token=webhook_secret(),
            allowed_updates=["message"],
            drop_pending_updates=True,
        )
        log.info("Telegram webhook set for %s", config.PUBLIC_URL)
    yield
    if _tg_app:
        await _tg_app.stop()
        await _tg_app.shutdown()


app = FastAPI(title="Samjho", description="Explains official documents in simple Hindi/English.", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["POST", "GET"], allow_headers=["*"])


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.api_route("/health", methods=["GET", "HEAD"])
def health() -> dict:
    return {"ok": True, "model": config.LLM_MODEL, "telegram": "webhook" if _tg_app else "off"}


@app.post("/api/explain")
async def explain_endpoint(file: UploadFile = File(...), lang: str = Form("hi")) -> dict:
    if lang not in ("hi", "en"):
        raise HTTPException(400, "lang must be 'hi' or 'en'")
    data = await file.read(config.MAX_UPLOAD_MB * 1024 * 1024 + 1)
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File too large (max {config.MAX_UPLOAD_MB} MB)")
    try:
        return await run_in_threadpool(explain, data, file.filename or "", file.content_type or "", lang)
    except UnsupportedFile as exc:
        raise HTTPException(400, str(exc))
    except ModelError as exc:
        raise HTTPException(503, str(exc))


@app.post(WEBHOOK_PATH)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(default=""),
) -> dict:
    if not _tg_app:
        raise HTTPException(404, "Telegram webhook is not enabled")
    from app.bot import webhook_secret
    if not hmac.compare_digest(x_telegram_bot_api_secret_token, webhook_secret()):
        raise HTTPException(403, "Bad secret")
    update = Update.de_json(await request.json(), _tg_app.bot)
    # Answer Telegram immediately; reading a document takes 10-20 s.
    task = asyncio.create_task(_tg_app.process_update(update))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return {"ok": True}
