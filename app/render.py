"""Turn the verified JSON into a friendly chat message (Telegram-flavoured Markdown-free plain text)."""

LABELS = {
    "hi": {
        "what": "📄 Ye kya hai", "do": "✅ Aapko kya karna hai", "when": "⏰ Kab tak",
        "amount": "💰 Rakam", "ignore": "⚠️ Na kiya to", "check": "🔍 Khud check karein",
        "pro": "👨‍⚖️ Ye zaroori maamla hai. Kisi CA / vakeel / bank se ek baar zaroor baat karein.",
        "days_left": "({n} din baaki)", "today": "(aaj hi aakhri din hai!)", "passed": "(tareekh nikal chuki hai!)",
        "not_doc": "🤔 Ye koi document nahi lag raha. Bill, notice ya letter ki saaf photo bhejein.",
        "footer": "ℹ️ Samjho galti kar sakta hai. Zaroori faisle se pehle original document dekhein.",
        "more_pages": "(Sirf pehle {n} page padhe gaye.)",
    },
    "en": {
        "what": "📄 What this is", "do": "✅ What you need to do", "when": "⏰ By when",
        "amount": "💰 Amount", "ignore": "⚠️ If you ignore it", "check": "🔍 Please check yourself",
        "pro": "👨‍⚖️ This is important. Please talk to a CA / lawyer / your bank before acting.",
        "days_left": "({n} days left)", "today": "(today is the last day!)", "passed": "(this date has passed!)",
        "not_doc": "🤔 This doesn't look like a document. Please send a clear photo of a bill, notice or letter.",
        "footer": "ℹ️ Samjho can make mistakes. Check the original before important decisions.",
        "more_pages": "(Only the first {n} pages were read.)",
    },
}


SYMBOLS = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£", "AED": "AED "}


def _fmt_amount(value: float, currency: str | None = "INR") -> str:
    sym = SYMBOLS.get((currency or "INR").upper(), f"{currency} ")
    v = round(float(value), 2)
    return f"{sym}{v:,.0f}" if v == int(v) else f"{sym}{v:,.2f}"


def render(data: dict, lang: str = "hi", pages_read: int | None = None, truncated: int = 0) -> str:
    L = LABELS.get(lang, LABELS["en"])
    if data.get("doc_type") == "not_a_document":
        return L["not_doc"]

    lines = [f"{L['what']}: {data.get('summary') or '-'}"]

    actions = [a for a in (data.get("actions") or []) if a]
    if actions:
        lines.append(f"\n{L['do']}:")
        lines += [f"  • {a}" for a in actions]

    dl = data.get("deadline") or {}
    if dl.get("date"):
        n = dl.get("days_left")
        hint = "" if n is None else (L["passed"] if n < 0 else L["today"] if n == 0 else L["days_left"].format(n=n))
        lines.append(f"\n{L['when']}: {dl['date']} {hint}".rstrip())

    amt = data.get("amount") or {}
    if amt.get("value") is not None:
        lines.append(f"{L['amount']}: {_fmt_amount(amt['value'], amt.get('currency'))}")

    if data.get("if_ignored"):
        lines.append(f"\n{L['ignore']}: {data['if_ignored']}")
    if data.get("notes"):
        lines.append(f"\n📝 {data['notes']}")

    unclear = list(dict.fromkeys(data.get("unreadable_parts") or []))
    if unclear:
        lines.append(f"\n{L['check']}: " + ", ".join(unclear))
    if data.get("needs_professional"):
        lines.append(f"\n{L['pro']}")
    if truncated and pages_read:
        lines.append(L["more_pages"].format(n=pages_read))

    lines.append(f"\n{L['footer']}")
    return "\n".join(lines)
