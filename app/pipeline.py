"""Prepare → Understand → Verify → Explain. Used by both the Telegram bot and the web API."""
from app.llm import analyze
from app.prepare import prepare
from app.render import render
from app.verify import verify


def explain(data: bytes, filename: str = "", mime: str = "", lang: str = "hi") -> dict:
    doc = prepare(data, filename, mime)          # in memory only; nothing is saved to disk
    result = analyze(doc.images, lang)
    result = verify(result, doc.text_layer)
    message = render(result, lang, pages_read=len(doc.images), truncated=doc.truncated_pages)
    return {"result": result, "message": message}
