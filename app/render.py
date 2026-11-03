"""Turn the verified JSON into a friendly chat message (Telegram-flavoured Markdown-free plain text)."""

LABELS = {
    "hi": {
        "what": "📄 यह क्या है", "do": "✅ आपको क्या करना है", "when": "⏰ कब तक",
        "amount": "💰 रकम", "ignore": "⚠️ न किया तो", "check": "🔍 खुद जाँच लें",
        "mismatch": "🚩 बिल में गड़बड़ी लग रही है",
        "pro": "👨‍⚖️ यह ज़रूरी मामला है। कोई कदम उठाने से पहले किसी CA / वकील / बैंक से बात करें।",
        "days_left": "({n} दिन बाकी)", "today": "(आज आखिरी दिन है!)", "passed": "(तारीख निकल चुकी है!)",
        "not_doc": "🤔 यह कोई दस्तावेज़ नहीं लग रहा। बिल, नोटिस या पत्र की साफ़ फ़ोटो भेजें।",
        "footer": "ℹ️ Samjho से गलती हो सकती है। ज़रूरी फ़ैसले से पहले मूल दस्तावेज़ ज़रूर देखें।",
        "more_pages": "(सिर्फ़ पहले {n} पेज पढ़े गए।)",
        "months": ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"],
    },
    "en": {
        "what": "📄 What this is", "do": "✅ What you need to do", "when": "⏰ By when",
        "amount": "💰 Amount", "ignore": "⚠️ If you ignore it", "check": "🔍 Please check yourself",
        "pro": "👨‍⚖️ This is important. Please talk to a CA / lawyer / your bank before acting.",
        "days_left": "({n} days left)", "today": "(today is the last day!)", "passed": "(this date has passed!)",
        "not_doc": "🤔 This doesn't look like a document. Please send a clear photo of a bill, notice or letter.",
        "footer": "ℹ️ Samjho can make mistakes. Check the original before important decisions.",
        "more_pages": "(Only the first {n} pages were read.)",
        "mismatch": "🚩 Something on this bill doesn't add up",
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    },
}


SYMBOLS = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£", "AED": "AED "}


def _fmt_amount(value: float, currency: str | None = "INR") -> str:
    sym = SYMBOLS.get((currency or "INR").upper(), f"{currency} ")
    v = round(float(value), 2)
    return f"{sym}{v:,.0f}" if v == int(v) else f"{sym}{v:,.2f}"


def _fmt_date(iso: str, months: list[str]) -> str:
    try:
        y, m, d = (int(x) for x in iso.split("-"))
        return f"{d} {months[m - 1]} {y}"
    except (ValueError, IndexError):
        return iso


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
        lines.append(f"\n{L['when']}: {_fmt_date(dl['date'], L['months'])} {hint}".rstrip())

    amt = data.get("amount") or {}
    if amt.get("value") is not None:
        lines.append(f"{L['amount']}: {_fmt_amount(amt['value'], amt.get('currency'))}")

    if data.get("if_ignored"):
        lines.append(f"\n{L['ignore']}: {data['if_ignored']}")
    if data.get("notes"):
        lines.append(f"\n📝 {data['notes']}")

    issues = [x for x in (data.get("discrepancies") or []) if x]
    if issues:
        lines.append(f"\n{L['mismatch']}:")
        lines += [f"  • {x}" for x in issues]

    unclear = list(dict.fromkeys(data.get("unreadable_parts") or []))
    if unclear:
        lines.append(f"\n{L['check']}: " + ", ".join(unclear))
    if data.get("needs_professional"):
        lines.append(f"\n{L['pro']}")
    if truncated and pages_read:
        lines.append(L["more_pages"].format(n=pages_read))

    lines.append(f"\n{L['footer']}")
    return "\n".join(lines)
