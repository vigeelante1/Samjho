"""Offline tests: no API key needed. Run with:  python -m pytest -q"""
import io
from datetime import date

import pymupdf as fitz
from PIL import Image

from app import pipeline
from app.prepare import prepare
from app.render import render
from app.verify import verify

TODAY = date(2026, 11, 3)


def good_output() -> dict:
    return {
        "doc_type": "electricity_bill", "issuer": "BSES Rajdhani",
        "summary": "Ye aapka November ka bijli bill hai.",
        "actions": ["₹2,340 ka bill jama karein"],
        "deadline": {"date": "2026-11-15", "source_quote": "Due Date: 15/11/2026"},
        "amount": {"value": 2340, "source_quote": "Total Payable Rs. 2,340.00"},
        "if_ignored": "Late fee lagegi.", "risk_level": "low", "needs_professional": False,
        "unreadable_parts": [], "notes": None,
    }


def test_verify_accepts_grounded_values():
    out = verify(good_output(), today=TODAY)
    assert out["checks"] == {"deadline": "verified", "amount": "verified"}
    assert out["deadline"]["days_left"] == 12


def test_verify_rejects_invented_date_and_amount():
    data = good_output()
    data["deadline"]["date"] = "2026-11-25"     # not what the quote says
    data["amount"]["value"] = 23400              # not what the quote says
    out = verify(data, today=TODAY)
    assert out["deadline"]["date"] is None and out["amount"]["value"] is None
    assert "deadline / due date" in out["unreadable_parts"] and "amount" in out["unreadable_parts"]


def test_verify_month_name_formats():
    data = good_output()
    data["deadline"]["source_quote"] = "Pay before 15th Nov, 2026"
    assert verify(data, today=TODAY)["checks"]["deadline"] == "verified"


def test_verify_checks_quote_exists_in_pdf_text():
    out = verify(good_output(), text_layer="Some other bill. Due Date: 20/11/2026", today=TODAY)
    assert out["checks"]["deadline"] == "unverified"


def test_render_hindi_and_professional_flag():
    data = verify(good_output(), today=TODAY)
    data["needs_professional"] = True
    msg = render(data, "hi")
    assert "यह क्या है" in msg and "₹2,340" in msg and "15 नवंबर 2026" in msg and "12 दिन बाकी" in msg and "CA" in msg


def test_render_shows_discrepancies_in_english():
    data = verify(good_output(), today=TODAY)
    data["discrepancies"] = ["Readings show 150 units, bill charges 450."]
    msg = render(data, "en")
    assert "15 Nov 2026" in msg and "doesn't add up" in msg and "150 units" in msg


def test_prepare_image_and_pdf():
    buf = io.BytesIO()
    Image.new("RGB", (3000, 2000), "white").save(buf, "PNG")
    doc = prepare(buf.getvalue(), "x.png")
    assert len(doc.images) == 1 and max(Image.open(io.BytesIO(doc.images[0])).size) == 1600

    pdf = fitz.open()
    for i in range(7):
        pdf.new_page().insert_text((72, 72), f"Page {i} Due Date: 15/11/2026")
    doc = prepare(pdf.tobytes(), "n.pdf")
    assert len(doc.images) == 5 and doc.truncated_pages == 2 and "Due Date" in doc.text_layer


def test_full_pipeline_with_fake_model(monkeypatch):
    monkeypatch.setattr(pipeline, "analyze", lambda images, lang: good_output())
    buf = io.BytesIO()
    Image.new("RGB", (800, 600), "white").save(buf, "JPEG")
    out = pipeline.explain(buf.getvalue(), "bill.jpg", "image/jpeg", "en")
    assert "What this is" in out["message"]
    assert out["result"]["checks"]["amount"] == "verified"
