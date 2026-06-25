"""
Extract structured rows from bank statement images (JPG/PNG) or scanned PDFs
using Tesseract OCR on bounding-box crops defined by a saved template.

Currency normalisation: fields flagged "currency" assume exactly 2 decimal
places in the source document.  When OCR drops the period (and/or thousands
comma), the raw digits are reconstructed correctly:
  "100000"  <- "1,000.00"  (both comma and period dropped)
  "10050"   <- "100.50"    (period dropped)
  "1000.00" <- "1,000.00"  (comma dropped, period kept) — already correct

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
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import fitz
import pytesseract
from PIL import Image

if sys.platform == "win32":
    def _resolve_tesseract() -> str:
        # 1. User-configured path in config.json (must exist on disk)
        try:
            from core.config import get_config as _get_config
            cfg = _get_config().tesseract_path
            if cfg and Path(cfg).exists():
                return cfg
        except Exception:
            pass
        # 2. Bundled alongside OCRMaster.exe (PyInstaller / MSIX build)
        if getattr(sys, "frozen", False):
            bundled = Path(sys.executable).parent / "tesseract" / "tesseract.exe"
            if bundled.exists():
                return str(bundled)
        # 3. Standard system install
        return r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    pytesseract.pytesseract.tesseract_cmd = _resolve_tesseract()

# Single-call OCR config: treat page as sparse text with a mix of blocks
_TSS_PAGE = "--psm 11"

# Template builder renders PDFs via open_source_image at Matrix(2.0, 2.0).
# OCR renders via _load_pages at Matrix(300/72, 300/72).
# Bboxes must be scaled from canvas pixel space to OCR pixel space for PDFs.
_PDF_CANVAS_SCALE = 2.0
_PDF_OCR_SCALE    = 300 / 72


# ── PDF coordinate scaling ────────────────────────────────────────────────────

def _scale_template_for_pdf(fields: list[dict], row_detection: dict
                             ) -> tuple[list[dict], dict]:
    """Scale template coords from canvas (2x) pixel space to OCR (300/72) pixel space."""
    ratio = _PDF_OCR_SCALE / _PDF_CANVAS_SCALE
    scaled_fields = []
    for f in fields:
        sf = dict(f)
        b = f["bbox"]
        sf["bbox"] = [b[0] * ratio, b[1] * ratio, b[2] * ratio, b[3] * ratio]
        scaled_fields.append(sf)
    scaled_rd = dict(row_detection)
    for key in ("start_y_pts", "end_y_pts", "row_height_pts"):
        if key in scaled_rd:
            scaled_rd[key] = float(scaled_rd[key]) * ratio
    return scaled_fields, scaled_rd


# ── Text helpers ──────────────────────────────────────────────────────────────

def _clean(text: Optional[str]) -> str:
    if not text:
        return ""
    return " ".join(text.split())


_MONTH_ABBREVS: dict[str, int] = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}


def _closest_month(s: str) -> Optional[int]:
    """Match an OCR'd 3-ish-letter string to a month number.
    Requires at least 2 of 3 leading characters to agree."""
    s3 = s.upper().strip()[:3]
    if s3 in _MONTH_ABBREVS:
        return _MONTH_ABBREVS[s3]
    best_num, best_score = None, -1
    for abbr, num in _MONTH_ABBREVS.items():
        score = sum(1 for a, b in zip(s3, abbr) if a == b)
        if score > best_score:
            best_score, best_num = score, num
    return best_num if best_score >= 2 else None


def _parse_date_with_format(raw: str, fmt: str) -> Optional[str]:
    """Parse an OCR'd date string using a user-specified format.

    Format tokens: DD (day 01-31), MM (month 01-12), MMM (Jan abbreviation),
                   YY (2-digit year), YYYY (4-digit year).
    Separators in the format (space, -, /, .) become flexible in the regex so
    OCR-dropped or substituted separators are tolerated.
    Falls back to _parse_date() if the format regex does not match.
    """
    if not raw or not fmt:
        return _parse_date(raw) if raw else None

    # Tokenise format string into alternating (tok, value) / (sep, chars) pairs.
    # Order matters: longer tokens must come before shorter prefixes (MMM > MM > M).
    tok_re = re.compile(r'(YYYY|YY|MMM|MM|M|DD)')
    tokens: list[tuple[str, str]] = []
    last = 0
    for m in tok_re.finditer(fmt):
        if m.start() > last:
            tokens.append(('sep', fmt[last:m.start()]))
        tokens.append(('tok', m.group()))
        last = m.end()
    if last < len(fmt):
        tokens.append(('sep', fmt[last:]))

    if not any(k == 'tok' for k, _ in tokens):
        return _parse_date(raw)

    # M  = month without zero-pad (1-12, 1-2 digits)
    # MM = month zero-padded (01-12, always 2 digits from the source)
    #      Both accept 1-2 digit OCR output; validation enforces 1-12.
    cap = {
        'DD':   r'(\d{1,2})',
        'MM':   r'(\d{1,2})',
        'M':    r'(\d{1,2})',
        'MMM':  r'([A-Za-z]{2,5})',
        'YY':   r'(\d{2,4})',
        'YYYY': r'(\d{4})',
    }
    regex_parts: list[str] = []
    component_names: list[str] = []
    for kind, val in tokens:
        if kind == 'tok':
            regex_parts.append(cap[val])
            component_names.append(val)
        else:
            regex_parts.append(r'[\s\-\/\.\,]*')

    pattern = r'^\s*' + ''.join(regex_parts) + r'\s*$'
    m = re.match(pattern, raw.strip(), re.IGNORECASE)
    if not m:
        return _parse_date(raw)

    comps = dict(zip(component_names, m.groups()))
    try:
        day = int(comps['DD']) if 'DD' in comps else 1
        if 'MMM' in comps:
            month = _closest_month(comps['MMM'])
            if month is None:
                return _parse_date(raw)
        elif 'MM' in comps:
            month = int(comps['MM'])
        elif 'M' in comps:
            month = int(comps['M'])
        else:
            month = 1

        if 'YYYY' in comps:
            year = int(comps['YYYY'])
        elif 'YY' in comps:
            y = int(comps['YY'])
            year = y + 2000 if y < 100 else y
        else:
            year = datetime.now().year

        if not (1 <= day <= 31 and 1 <= month <= 12):
            return _parse_date(raw)
        return f"{year:04d}-{month:02d}-{day:02d}"
    except (ValueError, KeyError):
        return _parse_date(raw)


def _parse_amount(raw: str) -> Optional[float]:
    raw = raw.replace("$", "").replace(",", "").replace(" ", "").strip()
    try:
        return float(raw)
    except ValueError:
        return None


def _normalize_currency(raw: str) -> Optional[float]:
    """Parse a 2-decimal-place currency string where OCR may have dropped
    the period and/or thousands commas."""
    if not raw:
        return None
    s = raw.strip()
    if not s:
        return None

    negative = s.startswith('-') or (s.startswith('(') and s.endswith(')'))
    core = s.lstrip('-').strip().lstrip('(').rstrip(')').strip()
    core = core.replace('$', '').replace(' ', '')

    # Already in correct X.XX or X,XXX.XX format
    if re.fullmatch(r'[\d,]+\.\d{2}', core):
        val = float(core.replace(',', ''))
        return -val if negative else val

    # One decimal digit — trailing zero dropped by OCR (e.g. "100.5" → 100.50)
    if re.fullmatch(r'[\d,]+\.\d', core):
        val = float(core.replace(',', '') + '0')
        return -val if negative else val

    # No valid decimal — strip all non-digits and reinsert before last 2
    digits = re.sub(r'\D', '', core)
    if not digits:
        return None
    if len(digits) <= 2:
        # Too short to reliably infer decimal; return as whole number
        return -float(digits) if negative else float(digits)
    val = float(digits[:-2] + '.' + digits[-2:])
    return -val if negative else val


def _parse_date(raw: str) -> Optional[str]:
    raw = raw.strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%Y-%m-%d",
                "%B %d, %Y", "%b %d, %Y", "%d %b %Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return raw if raw else None


def _coerce(raw: str, fname: str, currency_fields: set, amount_fields: set,
            date_fields: set, date_formats: dict):
    if fname in currency_fields:
        return _normalize_currency(raw) if raw else None
    if fname in date_formats:
        return _parse_date_with_format(raw, date_formats[fname]) if raw else None
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
                            currency_fields: set, amount_fields: set,
                            date_fields: set, date_formats: dict,
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
            header_row[fname] = _coerce(text, fname, currency_fields, amount_fields, date_fields, date_formats)
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
            row[fname] = _coerce(text, fname, currency_fields, amount_fields, date_fields, date_formats) if text else None

        if any_text:
            rows.append(row)

    return rows


def _extract_repeat_vertical(words: list[dict], fields: list[dict],
                              row_detection: dict,
                              currency_fields: set, amount_fields: set,
                              date_fields: set, date_formats: dict,
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
            row[field["name"]] = _coerce(raw, field["name"], currency_fields, amount_fields, date_fields, date_formats)
        if any_text:
            rows.append(row)
        y += row_h

    return rows


# ── Row grouping (multi-line transactions) ────────────────────────────────────

def _apply_row_grouping(rows: list[dict], fields: list[dict]) -> list[dict]:
    """
    Collapse multi-line transaction rows into one row per transaction.

    anchor_fields  — field(s) marked group_anchor (e.g. date): when a row has a
                     value here it starts a new transaction group.
    concat_fields  — field(s) marked concat_in_group (e.g. description): values
                     from every row in the group are joined with a space.
    Other fields   — last non-None value in the group wins (covers debit/credit
                     which appear only in the final row of a group).
    """
    anchor_fields = {f["name"] for f in fields if f.get("group_anchor", False)}
    concat_fields = {f["name"] for f in fields if f.get("concat_in_group", False)}

    if not anchor_fields:
        return rows

    groups: list[list[dict]] = []
    current: list[dict] = []

    for row in rows:
        if row.get("_row_type") == "header":
            if current:
                groups.append(current)
                current = []
            groups.append([row])
            continue

        is_anchor = any(row.get(f) for f in anchor_fields)
        if is_anchor and current:
            groups.append(current)
            current = []
        current.append(row)

    if current:
        groups.append(current)

    result = []
    for group in groups:
        if not group:
            continue
        # Single row or header — pass through unchanged
        if len(group) == 1 or group[0].get("_row_type") == "header":
            result.append(group[0])
            continue

        # Collect all field keys across the group
        all_keys: set[str] = set()
        for row in group:
            all_keys.update(row.keys())
        all_keys -= {"_page", "_row_type"}

        collapsed: dict = {"_page": group[0]["_page"], "_row_type": "transaction"}
        for fname in all_keys:
            if fname in concat_fields:
                parts = [str(row[fname]) for row in group if row.get(fname) is not None]
                collapsed[fname] = " ".join(parts) if parts else None
            else:
                # Last non-None value wins (e.g. amount in the last row)
                val = None
                for row in group:
                    if row.get(fname) is not None:
                        val = row[fname]
                collapsed[fname] = val
        result.append(collapsed)

    return result


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

    currency_fields = {f["name"] for f in fields if f.get("currency", False)}
    amount_fields   = {f["name"] for f in fields
                       if f["name"] not in currency_fields and
                       any(k in f["name"].lower()
                           for k in ("amount", "balance", "withdrawal", "deposit", "total", "fee"))}
    # Fields with an explicit date_format take priority; remaining "date" fields use auto-detect
    date_formats    = {f["name"]: f["date_format"] for f in fields
                       if f.get("date_format", "").strip()}
    date_fields     = {f["name"] for f in fields
                       if "date" in f["name"].lower() and f["name"] not in date_formats}

    # Template bboxes are in the 2x (144 DPI) canvas pixel space for PDFs;
    # OCR runs at 300/72 DPI. Scale to match before filtering words.
    if Path(filename).suffix.lower() == ".pdf":
        fields, rd = _scale_template_for_pdf(fields, rd)

    pages      = _load_pages(file_bytes, filename)
    all_rows   = []
    skip_pages = set(template.get("skip_pages", []))   # 1-based page numbers
    page_range = template.get("page_range", [])         # [start, end] 1-based inclusive

    for page_num, img in enumerate(pages):
        page_1based = page_num + 1
        if page_1based in skip_pages:
            continue
        if len(page_range) == 2 and not (page_range[0] <= page_1based <= page_range[1]):
            continue

        words = _ocr_page(img)   # single Tesseract call per page
        if strategy == "repeat_vertical":
            rows = _extract_repeat_vertical(words, fields, rd, currency_fields, amount_fields, date_fields, date_formats, page_num)
        else:
            rows = _extract_fixed_regions(words, fields, currency_fields, amount_fields, date_fields, date_formats, page_num)
        all_rows.extend(rows)

    # Collapse multi-line transactions (group_anchor + concat_in_group fields)
    if any(f.get("group_anchor") or f.get("concat_in_group") for f in fields):
        all_rows = _apply_row_grouping(all_rows, fields)

    # Fill-forward for sub_group fields: value appears once per group of rows;
    # blank rows in the group inherit the last seen non-None value (date, balance, etc.)
    sub_group_fields = [f["name"] for f in fields if f.get("sub_group", False)]
    if sub_group_fields and all_rows:
        last_seen: dict[str, object] = {}
        for row in all_rows:
            for fname in sub_group_fields:
                val = row.get(fname)
                if val is not None:
                    last_seen[fname] = val
                elif fname in last_seen:
                    row[fname] = last_seen[fname]

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
