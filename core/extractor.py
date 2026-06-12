"""
Extract structured rows from bank statement images (JPG/PNG) or scanned PDFs
using Tesseract OCR on bounding-box crops defined by a saved template.

Two extraction strategies:
  fixed_regions   — user drew tall column boxes; OCR each column, split by line,
                    zip columns into rows. Best for most bank statements.
  repeat_vertical — user drew one row; extractor steps down the page at a
                    fixed row height. Best for perfectly uniform row spacing.

Performance: Tesseract is run ONCE per page via image_to_data(), which returns
word-level bounding boxes. Fields are populated by filtering those words into
each template region — no per-field subprocess overhead.
"""
import io
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import fitz
import pytesseract
from PIL import Image

if sys.platform == "win32":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Single-call OCR config: treat page as sparse text with a mix of blocks
_TSS_PAGE = "--psm 11"


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


# ── Single-pass OCR ───────────────────────────────────────────────────────────

def _ocr_page(img: Image.Image) -> list[dict]:
    """
    Run Tesseract once on the full image and return a list of word dicts:
      {text, left, top, right, bottom, line_num (global), conf}
    Words with low confidence or empty text are excluded.
    """
    data = pytesseract.image_to_data(
        img,
        config=_TSS_PAGE,
        output_type=pytesseract.Output.DICT,
    )
    words = []
    # Compose a global line key so words on the same printed line share it
    for i, text in enumerate(data["text"]):
        text = text.strip()
        conf = int(data["conf"][i])
        if not text or conf < 10:
            continue
        left   = data["left"][i]
        top    = data["top"][i]
        width  = data["width"][i]
        height = data["height"][i]
        words.append({
            "text":     text,
            "left":     left,
            "top":      top,
            "right":    left + width,
            "bottom":   top + height,
            "block":    data["block_num"][i],
            "par":      data["par_num"][i],
            "line":     data["line_num"][i],
            "conf":     conf,
        })
    return words


def _words_in_bbox(words: list[dict], bbox: list[float],
                   overlap: float = 0.5) -> list[dict]:
    """
    Return words whose centre falls inside bbox [x0, y0, x1, y1].
    overlap fraction of the word's width/height must be inside the box.
    """
    x0, y0, x1, y1 = bbox
    result = []
    for w in words:
        cx = (w["left"] + w["right"]) / 2
        cy = (w["top"]  + w["bottom"]) / 2
        if x0 <= cx <= x1 and y0 <= cy <= y1:
            result.append(w)
    return result


def _word_cy(w: dict) -> float:
    return (w["top"] + w["bottom"]) / 2


def _cluster_y_bands(words_per_field: dict[str, list[dict]],
                     row_gap: int = 10) -> list[tuple[float, float]]:
    """
    Collect every word Y-centre across all fields, cluster nearby values,
    and return a sorted list of (band_top, band_bottom) row bands.
    This gives row positions even when some columns are sparse.
    """
    all_cy: list[float] = []
    for words in words_per_field.values():
        for w in words:
            all_cy.append(_word_cy(w))

    if not all_cy:
        return []

    all_cy.sort()
    clusters: list[list[float]] = [[all_cy[0]]]
    for cy in all_cy[1:]:
        if cy - clusters[-1][-1] <= row_gap:
            clusters[-1].append(cy)
        else:
            clusters.append([cy])

    bands = []
    for cluster in clusters:
        mid = sum(cluster) / len(cluster)
        bands.append((mid - row_gap, mid + row_gap))
    return bands


def _words_in_band(words: list[dict], band_top: float, band_bottom: float) -> list[dict]:
    return [w for w in words if band_top <= _word_cy(w) <= band_bottom]


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

def _extract_fixed_regions(words: list[dict], fields: list[dict],
                            amount_fields: set, date_fields: set,
                            page_num: int) -> list[dict]:
    """
    Each bbox covers a full column (or a single header field).
    Words are filtered into each bbox, then rows are aligned by Y-band so that
    sparse columns (e.g. credit — only some rows have a value) get blank/null
    for rows where no word falls in that band, rather than repeating a value.
    Single-line fields (bbox height < 60 px) are treated as header fields.
    """
    # Bucket words into each field's bbox
    field_words: dict[str, list[dict]] = {}
    single_line_fields: set[str] = set()

    for field in fields:
        bbox = field["bbox"]
        fw = _words_in_bbox(words, bbox)
        field_words[field["name"]] = fw
        if (bbox[3] - bbox[1]) < 60:
            single_line_fields.add(field["name"])

    # Separate header (single-line / repeat-flagged) fields from column fields
    header_row = {"_page": page_num + 1, "_row_type": "header"}
    multi_field_words: dict[str, list[dict]] = {}

    for field in fields:
        fname = field["name"]
        fw = field_words[fname]
        is_repeat = field.get("repeat", False)
        if is_repeat or fname in single_line_fields or len(fw) == 0:
            text = " ".join(w["text"] for w in sorted(fw, key=lambda x: x["left"]))
            header_row[fname] = _coerce(text, fname, amount_fields, date_fields)
        else:
            multi_field_words[fname] = fw

    rows = []
    if any(v for k, v in header_row.items() if not k.startswith("_")):
        rows.append(header_row)

    if not multi_field_words:
        return rows

    # Discover row bands from all multi-column words' Y positions
    bands = _cluster_y_bands(multi_field_words)
    if not bands:
        return rows

    for band_top, band_bottom in bands:
        row = {"_page": page_num + 1, "_row_type": "transaction"}
        # Carry header values for context
        for k, v in header_row.items():
            if not k.startswith("_"):
                row[k] = v

        any_text = False
        for field in fields:
            fname = field["name"]
            if fname not in multi_field_words:
                continue  # header field already in row via header_row carry
            band_words = _words_in_band(multi_field_words[fname], band_top, band_bottom)
            text = _clean(" ".join(w["text"] for w in sorted(band_words, key=lambda x: x["left"])))
            if text:
                any_text = True
            # None when blank so the DB stores NULL, not empty string
            row[fname] = _coerce(text, fname, amount_fields, date_fields) if text else None

        if any_text:
            rows.append(row)

    return rows


def _extract_repeat_vertical(words: list[dict], fields: list[dict],
                              row_detection: dict,
                              amount_fields: set, date_fields: set,
                              page_num: int) -> list[dict]:
    """
    User mapped one row; step down the page at row_height intervals.
    Each step collects words falling in the shifted bbox.
    """
    row_h   = float(row_detection.get("row_height_pts", 12.0))
    start_y = float(row_detection.get("start_y_pts", 0.0))
    # Infer end_y from words if not set meaningfully
    end_y   = float(row_detection.get("end_y_pts", 0.0))
    if end_y <= start_y:
        end_y = max((w["bottom"] for w in words), default=start_y + row_h)

    rows = []
    y = start_y
    while y + row_h <= end_y + 0.5:
        offset = y - start_y
        row = {"_page": page_num + 1, "_row_type": "transaction"}
        any_text = False
        for field in fields:
            bbox = field["bbox"][:]
            shifted = [bbox[0], bbox[1] + offset, bbox[2], bbox[3] + offset]
            fw = _words_in_bbox(words, shifted)
            raw = _clean(" ".join(w["text"] for w in sorted(fw, key=lambda x: x["left"])))
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
    Tesseract runs once per page; results are sliced by field bounding boxes.
    Returns list of row dicts keyed by template field names.
    """
    fields   = template.get("fields", [])
    rd       = template.get("row_detection", {})
    strategy = rd.get("strategy", "fixed_regions")

    amount_fields = {f["name"] for f in fields
                     if any(k in f["name"].lower()
                            for k in ("amount", "balance", "withdrawal", "deposit", "total", "fee"))}
    date_fields   = {f["name"] for f in fields if "date" in f["name"].lower()}

    pages    = _load_pages(file_bytes, filename)
    all_rows = []

    for page_num, img in enumerate(pages):
        words = _ocr_page(img)   # single Tesseract call per page
        if strategy == "repeat_vertical":
            rows = _extract_repeat_vertical(words, fields, rd, amount_fields, date_fields, page_num)
        else:
            rows = _extract_fixed_regions(words, fields, amount_fields, date_fields, page_num)
        all_rows.extend(rows)

    return all_rows


def ocr_full_page(file_bytes: bytes, filename: str, page_index: int = 0) -> str:
    """Run Tesseract on the full page — useful for previewing raw OCR output."""
    pages = _load_pages(file_bytes, filename)
    if page_index >= len(pages):
        return ""
    return pytesseract.image_to_string(pages[page_index], config="--psm 6")


def tesseract_available() -> tuple[bool, str]:
    """Return (True, version_string) or (False, error_message)."""
    try:
        ver = str(pytesseract.get_tesseract_version())
        return True, ver
    except Exception as e:
        return False, str(e)
