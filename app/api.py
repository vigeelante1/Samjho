"""Web API + upload page. Run with:  uvicorn app.api:app --reload"""
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app import config
from app.llm import ModelError
from app.pipeline import explain
from app.prepare import UnsupportedFile

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="Samjho", description="Explains official documents in simple Hindi/English.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["POST", "GET"], allow_headers=["*"])


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/health")
def health() -> dict:
    return {"ok": True, "model": config.LLM_MODEL}


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
