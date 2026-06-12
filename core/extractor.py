"""
Extract structured rows from bank statement images (JPG/PNG) or scanned PDFs
using Tesseract OCR on bounding-box crops defined by a saved template.

Two extraction strategies:
  fixed_regions  — user drew tall column boxes; OCR each column, split by line,
                   zip columns into rows. Best for most bank statements.
  repeat_vertical — user drew one row; extractor steps down the page at a
                    fixed row height. Best for perfectly uniform row spacing.
"""
import io
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import fitz  # pymupdf — render scanned PDF pages
import pytesseract
from PIL import Image

# Windows Tesseract path (no-op on Linux/macOS)
if sys.platform == "win32":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

_TSS_BLOCK = "--psm 6"   # uniform block of text (multi-line columns)
_TSS_LINE  = "--psm 7"   # single text line


# ── Text helpers ──────────────────────────────────────────────────────────────

def _clean(text: Optional[str]) -> str:
    if not text:
        return ""
    return " ".join(text.split())


def _parse_amount(raw: str) -> Optional[float]:
    raw = raw.replace("$", "").replace(",", "").replace(" ", "").strip()
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_date(raw: str) -> Optional[str]:
    raw = raw.strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%Y-%m-%d",
                "%B %d, %Y", "%b %d, %Y", "%d %b %Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return raw if raw else None


def _coerce(raw: str, fname: str, amount_fields: set, date_fields: set):
    if fname in amount_fields:
        return _parse_amount(raw) if raw else None
    if fname in date_fields:
        return _parse_date(raw) if raw else None
    return raw


# ── OCR crop ─────────────────────────────────────────────────────────────────

def _ocr_crop(img: Image.Image, bbox: list[float], multiline: bool = True) -> str:
    """Crop img to bbox (source pixels) and run Tesseract OCR."""
    x0, y0, x1, y1 = [int(round(v)) for v in bbox]
    w, h = img.size
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)
    if x1 <= x0 or y1 <= y0:
        return ""

    crop = img.crop((x0, y0, x1, y1))

    # Upscale very small crops for better OCR
    cw, ch = crop.size
    min_w, min_h = (300, 40) if multiline else (100, 20)
    if cw < min_w or ch < min_h:
        scale = max(min_w / cw, min_h / ch, 2.0)
        crop = crop.resize((int(cw * scale), int(ch * scale)), Image.LANCZOS)

    config = _TSS_BLOCK if multiline else _TSS_LINE
    return pytesseract.image_to_string(crop, config=config)


# ── File loader ───────────────────────────────────────────────────────────────

def _load_pages(file_bytes: bytes, filename: str) -> list[Image.Image]:
    """Convert file to list of PIL Images. PDFs rendered at 300 DPI."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages = []
        for page in doc:
            mat = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            pages.append(Image.frombytes("RGB", [pix.width, pix.height], pix.samples))
        doc.close()
        return pages
    else:
        return [Image.open(io.BytesIO(file_bytes)).convert("RGB")]


# ── Extraction strategies ─────────────────────────────────────────────────────

def _extract_fixed_regions(img: Image.Image, fields: list[dict],
                            amount_fields: set, date_fields: set,
                            page_num: int) -> list[dict]:
    """
    Each bbox covers a full column (or a single header field).
    OCR the whole bbox, split by line, zip columns into transaction rows.
    Single-line fields (account number, name, etc.) produce one header row.
    """
    columns: dict[str, list[str]] = {}
    single_line_fields = set()

    for field in fields:
        raw = _ocr_crop(img, field["bbox"], multiline=True)
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        columns[field["name"]] = lines
        # Treat as single-line if the box is short (< 60px tall)
        bbox = field["bbox"]
        if (bbox[3] - bbox[1]) < 60:
            single_line_fields.add(field["name"])

    if not columns:
        return []

    # Header fields (single-line): returned as one metadata row
    header_row = {"_page": page_num + 1, "_row_type": "header"}
    multi_fields = {}
    for fname, lines in columns.items():
        if fname in single_line_fields or len(lines) <= 1:
            raw = lines[0] if lines else ""
            header_row[fname] = _coerce(raw, fname, amount_fields, date_fields)
        else:
            multi_fields[fname] = lines

    rows = []
    if any(v for k, v in header_row.items() if not k.startswith("_")):
        rows.append(header_row)

    if not multi_fields:
        return rows

    # Transaction rows: zip multi-line columns
    max_lines = max(len(v) for v in multi_fields.values())
    for i in range(max_lines):
        row = {"_page": page_num + 1, "_row_type": "transaction"}
        # carry header values into each transaction row for context
        for fname, val in header_row.items():
            if not fname.startswith("_"):
                row[fname] = val
        for fname, lines in multi_fields.items():
            raw = lines[i] if i < len(lines) else ""
            row[fname] = _coerce(raw, fname, amount_fields, date_fields)
        rows.append(row)

    return rows


def _extract_repeat_vertical(img: Image.Image, fields: list[dict],
                              row_detection: dict,
                              amount_fields: set, date_fields: set,
                              page_num: int) -> list[dict]:
    """
    User mapped one row; step down the page at row_height intervals.
    Each step crops each field bbox shifted by the row offset.
    """
    row_h   = float(row_detection.get("row_height_pts", 12.0))
    start_y = float(row_detection.get("start_y_pts", 0.0))
    end_y   = float(row_detection.get("end_y_pts", img.height))

    rows = []
    y = start_y
    while y + row_h <= end_y + 0.5:
        offset = y - start_y
        row = {"_page": page_num + 1, "_row_type": "transaction"}
        any_text = False
        for field in fields:
            bbox = field["bbox"][:]
            bbox[1] += offset
            bbox[3] += offset
            raw = _clean(_ocr_crop(img, bbox, multiline=False))
            if raw:
                any_text = True
            row[field["name"]] = _coerce(raw, field["name"], amount_fields, date_fields)
        if any_text:
            rows.append(row)
        y += row_h

    return rows


# ── Public API ────────────────────────────────────────────────────────────────

def extract_with_template(file_bytes: bytes, filename: str, template: dict) -> list[dict]:
    """
    OCR-extract structured rows from an image or scanned PDF using a template.
    Returns list of row dicts keyed by template field names.
    """
    fields = template.get("fields", [])
    rd = template.get("row_detection", {})
    strategy = rd.get("strategy", "fixed_regions")

    amount_fields = {f["name"] for f in fields
                     if any(k in f["name"].lower()
                            for k in ("amount", "balance", "withdrawal", "deposit", "total", "fee"))}
    date_fields   = {f["name"] for f in fields if "date" in f["name"].lower()}

    pages = _load_pages(file_bytes, filename)
    all_rows = []

    for page_num, img in enumerate(pages):
        if strategy == "repeat_vertical":
            rows = _extract_repeat_vertical(img, fields, rd, amount_fields, date_fields, page_num)
        else:
            rows = _extract_fixed_regions(img, fields, amount_fields, date_fields, page_num)
        all_rows.extend(rows)

    return all_rows


def ocr_full_page(file_bytes: bytes, filename: str, page_index: int = 0) -> str:
    """Run Tesseract on the full page — useful for previewing raw OCR output."""
    pages = _load_pages(file_bytes, filename)
    if page_index >= len(pages):
        return ""
    return pytesseract.image_to_string(pages[page_index], config=_TSS_BLOCK)


def tesseract_available() -> tuple[bool, str]:
    """Return (True, version_string) or (False, error_message)."""
    try:
        ver = str(pytesseract.get_tesseract_version())
        return True, ver
    except Exception as e:
        return False, str(e)
