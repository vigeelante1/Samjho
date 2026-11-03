"""The single model call: document images in, structured JSON out."""
import base64
import json
import re
import time

from openai import APIStatusError, OpenAI

from app import config
from app.prompts import build_system_prompt

_client: OpenAI | None = None


class ModelError(RuntimeError):
    pass


def client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.llm_api_key(), base_url=config.LLM_BASE_URL, timeout=120)
    return _client


def _image_part(jpeg: bytes) -> dict:
    b64 = base64.b64encode(jpeg).decode()
    return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}


def _parse_json(text: str) -> dict:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)  # model added words around the JSON
        if match:
            return json.loads(match.group(0))
        raise ModelError("The model did not return valid JSON.")


def analyze(images: list[bytes], lang: str) -> dict:
    """Send all pages in one request and return the parsed JSON."""
    messages = [
        {"role": "system", "content": build_system_prompt(lang)},
        {"role": "user", "content": [
            {"type": "text", "text": f"Explain this document ({len(images)} page(s)). Return only the JSON."},
            *[_image_part(img) for img in images],
        ]},
    ]
    kwargs = dict(model=config.LLM_MODEL, messages=messages, max_tokens=config.LLM_MAX_TOKENS,
                  temperature=0.1, response_format={"type": "json_object"})

    for attempt in range(4):
        try:
            resp = client().chat.completions.create(**kwargs)
        except APIStatusError as exc:
            if exc.status_code == 400 and "response_format" in kwargs:
                kwargs.pop("response_format")  # some providers don't support JSON mode; prompt still asks for JSON
                continue
            if exc.status_code in (429, 503) and attempt < 3:  # busy: back off and retry
                time.sleep(2 * (attempt + 1))
                continue
            raise ModelError(f"Model request failed ({exc.status_code}).") from exc

        choice = resp.choices[0]
        if choice.finish_reason == "length":
            raise ModelError("The answer was cut off. Increase LLM_MAX_TOKENS.")
        return _parse_json(choice.message.content)

    raise ModelError("The model is busy. Please try again in a minute.")
