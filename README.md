# Samjho 📄 → 🙂

**Send a photo of any bill, bank letter or government notice. Get back, in simple Hindi or English: what it is, what you need to do, and by when.**

Millions of people in India get documents they can't fully understand: a tax notice, a loan letter, an electricity bill with a strange charge, a court summons. Samjho reads it and explains it like a helpful relative would.

> Built for the **BharatCode Build League** · powered by the BharatCode API (`qwen-3.8-27b`)

<!-- TODO: add demo GIF here -->

## Example

> 📄 **Ye kya hai:** Ye aapka November ka bijli bill hai.
> ✅ **Aapko kya karna hai:** ₹2,340 jama karein
> ⏰ **Kab tak:** 2026-11-15 (12 din baaki)
> ⚠️ **Na kiya to:** Late fee lagegi.

## Why trust it? Every number is checked

An AI explaining a tax notice must not invent a deadline. So Samjho **never shows a date or amount it can't back up**:

1. The model must copy the exact printed text each deadline and amount came from.
2. Code (not the AI) checks that the date/amount really appears in that quote.
3. For digital PDFs, it also checks the quote exists in the document's real text.
4. Anything that fails is hidden and shown as **"🔍 Please check this yourself."**

High-stakes documents (legal, tax demands, large amounts) always add a "talk to a CA / lawyer" note.

## How it works

```
Photo / PDF → Prepare → Understand → Verify → Explain
              (resize,   (1 vision    (check    (Hindi/English
               PDF→img)   LLM call     dates &    message)
                          → JSON)      amounts)
```

| File | Job |
|---|---|
| `app/prepare.py` | Photos/PDFs → JPEG pages (max 5), keeps PDF text for checks |
| `app/llm.py` | One call to any OpenAI-compatible model, JSON out, retries when busy |
| `app/verify.py` | Rejects dates/amounts not grounded in the document |
| `app/render.py` | JSON → friendly Hindi or English message |
| `app/bot.py` | Telegram bot |
| `app/api.py` + `web/` | Web upload page and `/api/explain` endpoint |

## Privacy

Documents are processed **in memory only** and never written to disk or a database.

## Run it yourself

```bash
git clone https://github.com/vigeelante1/Samjho.git && cd Samjho
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then add your API key and Telegram bot token

python -m pytest -q                               # offline tests, no key needed
python -m scripts.try_local samples/bill.jpg      # test on a file
python -m app.bot                                 # start the Telegram bot
uvicorn app.api:app --reload                      # web page at http://localhost:8000
```

Works with any OpenAI-compatible model by changing three lines in `.env` (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`).

## Limitations

Samjho explains what a document says; it is not legal or financial advice. Very blurry photos or handwritten documents may not be read correctly. Always check the original before important decisions.

## License

MIT
