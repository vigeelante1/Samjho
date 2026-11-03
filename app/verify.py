"""Don't trust the model on numbers that matter.

Every deadline and amount must come with the exact printed text it was taken from.
We check that:
  1. the value actually appears inside its own source_quote (the model didn't invent it), and
  2. for digital PDFs, the source_quote really exists in the document's text layer.
Anything that fails is removed and reported as "please check this yourself".
"""
import re
from datetime import date

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def _norm(s: str) -> str:
    return re.sub(r"[\s,.:/\-₹]|rs", "", (s or "").lower())


def _quote_dates(quote: str) -> set[date]:
    """All plausible dates written in the quote, in common Indian formats."""
    found: set[date] = set()
    q = quote.lower()
    for d, m, y in re.findall(r"(\d{1,2})[./\- ](\d{1,2})[./\- ](\d{2,4})", q):       # 15/11/2026, 15-11-26
        _add(found, y, m, d)
    for y, m, d in re.findall(r"(\d{4})[./\-](\d{1,2})[./\-](\d{1,2})", q):           # 2026-11-15
        _add(found, y, m, d)
    for d, mon, y in re.findall(r"(\d{1,2})(?:st|nd|rd|th)?[ \-.]*([a-z]{3})[a-z]*[ \-.,]*(\d{2,4})", q):  # 15 Nov 2026
        if mon in MONTHS:
            _add(found, y, MONTHS[mon], d)
    for mon, d, y in re.findall(r"([a-z]{3})[a-z]*[ .]+(\d{1,2})(?:st|nd|rd|th)?,?[ ]+(\d{2,4})", q):  # Nov 15, 2026
        if mon in MONTHS:
            _add(found, y, MONTHS[mon], d)
    return found


def _add(found: set, y, m, d) -> None:
    y = int(y)
    y = y + 2000 if y < 100 else y
    try:
        found.add(date(y, int(m), int(d)))
    except ValueError:
        pass


def _amount_in_quote(value: float, quote: str) -> bool:
    numbers = re.findall(r"\d[\d,]*(?:\.\d+)?", quote)
    return any(abs(float(n.replace(",", "")) - float(value)) < 0.01 for n in numbers)


def _quote_in_document(quote: str, text_layer: str) -> bool:
    return not text_layer.strip() or _norm(quote) in _norm(text_layer)


def verify(data: dict, text_layer: str = "", today: date | None = None) -> dict:
    today = today or date.today()
    data.setdefault("unreadable_parts", [])
    data["checks"] = {"deadline": "none", "amount": "none"}

    dl = data.get("deadline") or {}
    if dl.get("date"):
        quote = dl.get("source_quote") or ""
        try:
            parsed = date.fromisoformat(dl["date"])
        except ValueError:
            parsed = None
        if parsed and parsed in _quote_dates(quote) and _quote_in_document(quote, text_layer):
            data["checks"]["deadline"] = "verified"
            data["deadline"]["days_left"] = (parsed - today).days
        else:
            data["deadline"] = {"date": None, "source_quote": None}
            data["checks"]["deadline"] = "unverified"
            data["unreadable_parts"].append("deadline / due date")

    amt = data.get("amount") or {}
    if amt.get("value") is not None:
        quote = amt.get("source_quote") or ""
        try:
            ok = _amount_in_quote(float(amt["value"]), quote) and _quote_in_document(quote, text_layer)
        except (TypeError, ValueError):
            ok = False
        if ok:
            data["checks"]["amount"] = "verified"
        else:
            data["amount"] = {"value": None, "source_quote": None}
            data["checks"]["amount"] = "unverified"
            data["unreadable_parts"].append("amount")

    return data
