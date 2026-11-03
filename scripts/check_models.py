"""Try a few models quickly and show which ones actually answer.

Usage:  python -m scripts.check_models
        python -m scripts.check_models gemini-3.6-flash gemini-flash-latest
"""
import sys
import time

from openai import OpenAI

from app import config

DEFAULT = ["gemini-flash-latest", "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash",
           "gemini-3.5-flash", "gemini-3-flash-preview", "gemini-2.5-flash"]

client = OpenAI(api_key=config.llm_api_key(), base_url=config.LLM_BASE_URL, timeout=45, max_retries=0)

for model in sys.argv[1:] or DEFAULT:
    start = time.time()
    try:
        r = client.chat.completions.create(
            model=model, max_tokens=500,
            messages=[{"role": "user", "content": "Reply with just: ok"}])
        text = (r.choices[0].message.content or "").strip()[:40]
        print(f"OK    {model:28s} {time.time()-start:5.1f}s  -> {text!r}")
    except Exception as exc:
        body = getattr(getattr(exc, "response", None), "text", "") or str(exc)
        print(f"FAIL  {model:28s} {time.time()-start:5.1f}s  {type(exc).__name__}: {body[:160]}")
