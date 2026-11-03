"""Turn whatever the user sent (photo or PDF) into a few JPEG pages the model can read."""
import io
from dataclasses import dataclass, field

import pymupdf as fitz
from PIL import Image, ImageOps

from app.config import MAX_PAGES

MAX_SIDE = 1600  # px; enough to read small print, small enough to stay cheap


class UnsupportedFile(ValueError):
    pass


@dataclass
class PreparedDoc:
    images: list[bytes]                 # JPEG bytes, one per page
    text_layer: str = ""                # real text from digital PDFs (used for verification)
    truncated_pages: int = 0            # pages dropped because of MAX_PAGES
    notes: list[str] = field(default_factory=list)


def _to_jpeg(img: Image.Image) -> bytes:
    img = ImageOps.exif_transpose(img)  # phone photos come rotated
    img = img.convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def prepare(data: bytes, filename: str = "", mime: str = "") -> PreparedDoc:
    is_pdf = mime == "application/pdf" or filename.lower().endswith(".pdf") or data[:5] == b"%PDF-"
    if is_pdf:
        return _prepare_pdf(data)
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:
        raise UnsupportedFile("Please send a photo (JPG/PNG) or a PDF.") from exc
    return PreparedDoc(images=[_to_jpeg(img)])


def _prepare_pdf(data: bytes) -> PreparedDoc:
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise UnsupportedFile("This PDF could not be opened.") from exc
    if doc.needs_pass:
        raise UnsupportedFile("This PDF is password-protected. Please send a screenshot instead.")

    images, texts = [], []
    for page in list(doc)[:MAX_PAGES]:
        pix = page.get_pixmap(dpi=150)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        images.append(_to_jpeg(img))
        texts.append(page.get_text())
    return PreparedDoc(
        images=images,
        text_layer="\n".join(texts),
        truncated_pages=max(0, doc.page_count - MAX_PAGES),
    )
