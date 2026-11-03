"""Settings loaded from environment variables (.env in development)."""
import os

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing {name}. Copy .env.example to .env and fill it in.")
    return value


# Any OpenAI-compatible provider works: BharatCode, Gemini, Groq...
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://bharatcode.ai/api/model/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-3.8-27b")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4000"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

MAX_PAGES = int(os.getenv("MAX_PAGES", "5"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))
DEFAULT_LANG = os.getenv("DEFAULT_LANG", "hi")  # "hi" or "en"


def llm_api_key() -> str:
    return _require("LLM_API_KEY")
