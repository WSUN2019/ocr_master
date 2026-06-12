"""
Extract structured rows from a PDF using a saved template.
Uses pdfplumber to crop bounding box regions and pull text.
"""
import re
from datetime import datetime
from typing import Optional

import pdfplumber


def _clean(text: Optional[str]) -> str:
    if not text:
        return ""
    return " ".join(text.split())


def _parse_amount(raw: str) -> Optional[float]:
    """Parse a dollar string like '$1,234.56' or '-1,234.56' to float."""
    raw = raw.replace("$", "").replace(",", "").strip()
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_date(raw: str) -> Optional[str]:
    """Try common date formats, return ISO YYYY-MM-DD or original string."""
    raw = raw.strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return raw if raw else None


def _extract_field_text(page, bbox: list[float]) -> str:
    """Crop a pdfplumber page to bbox and extract text."""
    x0, y0, x1, y1 = bbox
    try:
        cropped = page.crop((x0, y0, x1, y1))
        return _clean(cropped.extract_text())
    except Exception:
        return ""


def _row_bboxes(template: dict) -> list[tuple[float, list[dict]]]:
    """
    Generate (row_y_offset, fields) pairs for every transaction row on the page.
    Returns list of y-offsets; caller shifts each field bbox by that offset.
    """
    rd = template.get("row_detection", {})
    strategy = rd.get("strategy", "repeat_vertical")

    if strategy == "repeat_vertical":
        row_h = float(rd.get("row_height_pts", 12.0))
        start_y = float(rd.get("start_y_pts", 0.0))
        end_y = float(rd.get("end_y_pts", 792.0))
        offsets = []
        y = start_y
        while y + row_h <= end_y + 0.5:
            offsets.append(y - start_y)
            y += row_h
        return offsets

    if strategy == "fixed_regions":
        return [0.0]

    return [0.0]


def extract_with_template(pdf_bytes: bytes, template: dict) -> list[dict]:
    """
    Run extraction on every page of the PDF using the given template.
    Returns list of row dicts matching the template field names.
    """
    fields = template.get("fields", [])
    source_page_index = template.get("source_page", 0)
    amount_fields = {f["name"] for f in fields if "amount" in f["name"].lower() or "balance" in f["name"].lower()}
    date_fields = {f["name"] for f in fields if "date" in f["name"].lower()}

    rows = []

    with pdfplumber.open(pdf_bytes if isinstance(pdf_bytes, bytes) else open(pdf_bytes, "rb")) as pdf:
        for page_num, page in enumerate(pdf.pages):
            offsets = _row_bboxes(template)

            for offset in offsets:
                row = {"_page": page_num + 1}
                any_text = False

                for field in fields:
                    bbox = field["bbox"][:]
                    # shift y coords by row offset
                    bbox[1] += offset
                    bbox[3] += offset

                    raw = _extract_field_text(page, bbox)

                    if raw:
                        any_text = True

                    fname = field["name"]
                    if fname in amount_fields:
                        row[fname] = _parse_amount(raw) if raw else None
                    elif fname in date_fields:
                        row[fname] = _parse_date(raw) if raw else None
                    else:
                        row[fname] = raw

                # skip entirely blank rows
                if any_text:
                    rows.append(row)

    return rows


def extract_table_mode(pdf_bytes: bytes, page_index: int = 0) -> list[dict]:
    """
    Auto-detect tables using pdfplumber's built-in table extraction.
    Returns list of row dicts using first row as header.
    """
    rows = []
    with pdfplumber.open(pdf_bytes if isinstance(pdf_bytes, bytes) else open(pdf_bytes, "rb")) as pdf:
        page = pdf.pages[page_index]
        tables = page.extract_tables()
        for table in tables:
            if not table or len(table) < 2:
                continue
            headers = [str(h).strip() if h else f"col_{i}" for i, h in enumerate(table[0])]
            for raw_row in table[1:]:
                row = {}
                for h, cell in zip(headers, raw_row):
                    row[h] = _clean(str(cell)) if cell else ""
                rows.append(row)
    return rows
