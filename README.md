<div align="center">

# Samjho · समझो

### Send a photo of any bill or notice. Understand it in 10 seconds, in simple Hindi or English.

**[💬 Try on Telegram](https://t.me/samjhoindia_bot)** · **[🌐 Try on the web](https://samjho-6hus.onrender.com)** · Free · No sign-up · Nothing stored

*Built for the BharatCode Build League · Designed for the BharatCode API (qwen-3.8-27b)*

</div>

---

## The problem

Every month, millions of people in India get a document they can't fully understand: an electricity bill with an odd charge, a bank letter full of jargon, an income tax notice, a court summons, an insurance rejection.

Most people do one of three things: ignore it, panic, or wait for a relative to explain it. Missed deadlines mean late fees, disconnections, penalties and legal trouble.

## What Samjho does

Send a photo or PDF. Samjho replies with four answers:

| | |
|---|---|
| 📄 **What is this?** | "PowerGrid Co. का अक्टूबर 2026 का बिजली बिल।" |
| ✅ **What do I have to do?** | "20 नवंबर 2026 तक $134.50 जमा करें।" |
| ⏰ **By when?** | "20 नवंबर 2026 (17 दिन बाकी)" |
| ⚠️ **What if I ignore it?** | "बिजली कट जाएगी, दोबारा कनेक्शन का शुल्क लगेगा।" |

…and one more that people don't expect:

> 🚩 **बिल में गड़बड़ी लग रही है:** रीडिंग के हिसाब से 150 kWh उपयोग हुआ, लेकिन बिल 450 kWh का है।
>
> *(The readings show 150 units used, but the bill charges for 450.)*

## Why it can be trusted

An AI that explains a tax notice must never invent a deadline. Samjho is built so it **can't show a date or amount it can't back up**:

1. The model must copy the **exact printed text** that each date and amount came from.
2. Plain code (not AI) checks that the value really appears in that text.
3. For digital PDFs, it also checks that the text really exists in the document.
4. Anything that fails is hidden and shown as **"🔍 खुद जाँच लें" (please check this yourself)**.

Serious documents (court notices, tax demands, large amounts) always add a line to talk to a CA, lawyer or bank before acting.

## 🔒 Privacy

Documents are processed **in memory only**. They are never written to disk, a database or logs, and are gone the moment the reply is sent.

## How it works

```
 Photo / PDF ──▶ Prepare ──▶ Understand ──▶ Verify ──▶ Explain ──▶ Reply
                 resize,     one vision      check      Hindi or     Telegram
                 PDF→pages   LLM call →      dates &    English      or web
                             strict JSON     amounts    message
```

One model call per document. The AI only reads the document and fills in a fixed set of fields. Everything else (checking, formatting, language) is ordinary, testable code.

| File | Job |
|---|---|
| [`app/prepare.py`](app/prepare.py) | Photos and PDFs → up to 5 page images; keeps PDF text for checking |
| [`app/prompts.py`](app/prompts.py) | The single instruction the model gets, and the JSON it must return |
| [`app/llm.py`](app/llm.py) | One call to any OpenAI-compatible model API (BharatCode `qwen-3.8-27b` by design), retries when busy |
| [`app/verify.py`](app/verify.py) | Rejects any date or amount not grounded in the document |
| [`app/render.py`](app/render.py) | Turns the checked result into a friendly Hindi or English message |
| [`app/bot.py`](app/bot.py) | Telegram bot |
| [`app/api.py`](app/api.py) | Web page, `/api/explain` endpoint and Telegram webhook |

## Model

Samjho is designed for the **BharatCode API** (`qwen-3.8-27b`, vision). The code is provider-agnostic, so switching
is three settings in `.env` (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`). The live demo currently runs on a
temporary OpenAI-compatible model while BharatCode API access is being activated.

## Run it yourself

```bash
git clone https://github.com/vigeelante1/Samjho.git && cd Samjho
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # add your BharatCode API key and Telegram bot token

python -m pytest -q                             # offline tests, no key needed
python -m scripts.try_local path/to/bill.jpg    # explain one file in the terminal
uvicorn app.api:app --reload                    # web page at http://localhost:8000
python -m app.bot                               # Telegram bot (local polling)
```

Works with any OpenAI-compatible model: change `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL` in `.env`.

### Deploy for free on Render

1. Fork this repo.
2. On [render.com](https://render.com): **New → Web Service** → pick the repo → runtime **Docker** → instance **Free**.
3. Add the environment variables from `.env.example`.
4. Deploy. The bot switches to webhook mode automatically using Render's public URL.

## Limitations

- Samjho explains what a document says. It is **not legal or financial advice**.
- Very blurry photos or handwritten documents may not be read correctly. It will say so instead of guessing.
- Up to 5 pages per document.

## Roadmap

- WhatsApp support
- More Indian languages (Tamil, Bengali, Marathi, Kannada…)
- Voice replies for people who prefer listening
- Reminders before a deadline

## License

[MIT](LICENSE) · Made with ❤️ in Faridabad by [Vaibhav Sharma](https://github.com/vigeelante1)
