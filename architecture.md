# OCR Master — Bank Statement Extractor

## Overview

A fully local, offline web application that lets users visually map fields on a PDF by drawing
bounding boxes, save those layouts as named templates, and use them to extract structured data
from batches of similar documents. No data leaves the machine.

---

## Stack

| Layer | Technology | Purpose |
|---|---|---|
| PDF Rendering | `pymupdf` (fitz) | Render PDF pages to images for display + coordinate mapping |
| PDF Extraction | `pdfplumber` | Crop regions by bbox and extract text from native PDFs |
| Template UI | `streamlit-drawable-canvas` | Draw/edit red bounding boxes on rendered PDF image |
| Data | `pandas` | DataFrame for in-memory table manipulation |
| Storage | `sqlite3` (stdlib) | Local persistent database — transactions + templates |
| UI | `Streamlit` | Localhost web app at `http://localhost:8501` |
| Export | `csv` (stdlib) | Flat-file CSV output |
| Templates | JSON files | Human-readable field→bbox mappings, one file per template |

No external API calls. No telemetry. No cloud.

---

## Directory Layout

```
OCR_Master/
├── app.py                  # Streamlit entry point — page routing
├── pages/
│   ├── 01_template_builder.py  # Visual field mapper (draw boxes)
│   ├── 02_extract.py           # Upload PDF, assign template, run extraction
│   ├── 03_history.py           # Browse SQLite history, re-export
│   └── 04_settings.py          # Manage templates, clear data
├── core/
│   ├── extractor.py        # Crop PDF regions by bbox, return text
│   ├── storage.py          # SQLite read/write + CSV export
│   ├── template.py         # Template load/save/list (JSON)
│   └── renderer.py         # PDF page → PIL image + coordinate scaling
├── templates/              # Saved template JSON files (e.g. template_a.json)
├── ocr_master.db           # SQLite database (auto-created)
├── architecture.md
└── requirements.txt
```

---

## Core Concept: Visual Template Builder

### How It Works

1. User uploads a sample PDF of a given bank's statement layout
2. PDF page is rendered as a high-res image and displayed in Streamlit
3. User draws red rectangles over each data field (date, description, amount, balance...)
4. Each rectangle is labeled with a field name from the table schema
5. User saves the mapping as a named template (e.g. "Chase Checking", "BofA Savings")
6. On future PDFs from the same bank: select template → extract → done

### Coordinate System

```
PDF (pymupdf)                     Canvas (pixels)
  origin: top-left                  origin: top-left
  units: points (1pt = 1/72 inch)   units: pixels
  page: width_pts × height_pts      canvas: CANVAS_W × CANVAS_H

scale_x = CANVAS_W / page.width_pts
scale_y = CANVAS_H / page.height_pts

# Canvas bbox → PDF bbox (for pdfplumber crop)
pdf_x0 = canvas_x0 / scale_x
pdf_y0 = canvas_y0 / scale_y
pdf_x1 = canvas_x1 / scale_x
pdf_y1 = canvas_y1 / scale_y
```

Templates store PDF-space coordinates (not pixel coordinates) so they are
resolution-independent and work regardless of screen size.

---

## Template JSON Format

```json
{
  "name": "Chase Checking",
  "version": 1,
  "created_at": "2026-06-12T00:00:00",
  "page_width_pts": 612.0,
  "page_height_pts": 792.0,
  "fields": [
    {
      "name": "transaction_date",
      "label": "Transaction Date",
      "page": 0,
      "bbox": [36.0, 180.5, 90.0, 192.0],
      "bbox_note": "[x0, y0, x1, y1] in PDF points from top-left"
    },
    {
      "name": "description",
      "label": "Description",
      "page": 0,
      "bbox": [92.0, 180.5, 380.0, 192.0]
    },
    {
      "name": "amount",
      "label": "Amount",
      "page": 0,
      "bbox": [385.0, 180.5, 450.0, 192.0]
    },
    {
      "name": "balance",
      "label": "Running Balance",
      "page": 0,
      "bbox": [455.0, 180.5, 540.0, 192.0]
    }
  ],
  "row_detection": {
    "strategy": "repeat_vertical",
    "anchor_field": "transaction_date",
    "row_height_pts": 12.0,
    "start_y_pts": 180.5,
    "end_y_pts": 720.0
  }
}
```

### Row Detection Strategies

| Strategy | Use Case |
|---|---|
| `repeat_vertical` | Fields repeat row-by-row at fixed Y intervals (most bank statements) |
| `fixed_regions` | Each bbox is a single one-off field (e.g. account number header) |
| `table_detect` | Let pdfplumber auto-detect table structure within the mapped region |

---

## Data Flow

```
TEMPLATE BUILDER (one-time per bank format)
  Upload sample PDF
        │
        ▼
  renderer.py: PDF page → PIL Image (scale to canvas size)
        │
        ▼
  streamlit-drawable-canvas: user draws red boxes, labels each
        │
        ▼
  template.py: convert canvas px → PDF pts, save to templates/xxx.json
        │
        ▼
  Template file ready for reuse


EXTRACTION (for each new statement)
  Upload PDF + select template
        │
        ▼
  renderer.py: verify page dimensions match template
        │
        ▼
  extractor.py:
    for each row in page:
      for each field in template.fields:
        crop = pdfplumber.page.crop(bbox offset by row)
        text = crop.extract_text()
      yield row dict
        │
        ▼
  pandas DataFrame → display in Streamlit
        │
        ├──── CSV download button
        └──── storage.py → INSERT into SQLite
```

---

## Transaction Schema (SQLite)

```sql
CREATE TABLE transactions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file      TEXT,
    template_name    TEXT,
    account_number   TEXT,
    statement_period TEXT,
    transaction_date TEXT,
    post_date        TEXT,
    description      TEXT,
    amount           REAL,
    balance          REAL,
    category         TEXT,
    imported_at      TEXT
);

CREATE TABLE import_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    filename      TEXT,
    template_name TEXT,
    pages         INTEGER,
    rows_found    INTEGER,
    imported_at   TEXT,
    status        TEXT
);
```

Templates are stored as JSON files in `templates/` — not in SQLite — so they are
portable, human-readable, and easy to back up or share.

---

## Streamlit UI — Pages

### Page 1: Template Builder
- Upload a sample PDF (stays in memory)
- Page selector (which page has the repeating rows)
- Rendered PDF page displayed at fixed canvas width (e.g. 900px)
- `streamlit-drawable-canvas` overlay: draw mode = rect, stroke color = red
- Right panel: list of drawn boxes → user types field name for each
- Row detection config: row height, start Y, end Y
- Save button → writes `templates/<slug>.json`
- Load existing template to edit

### Page 2: Extract
- Upload one or more PDFs
- Select template from dropdown
- Optional: page range override
- Run extraction → shows DataFrame preview
- Editable cells for corrections
- "Save to DB" button + CSV download

### Page 3: History
- Query SQLite by date range, template, file name
- Re-export filtered results as CSV
- Delete imported batch

### Page 4: Settings
- List / rename / delete templates
- View import log
- Vacuum / backup SQLite DB

---

## Security Model

- Streamlit configured to bind `127.0.0.1` only (`.streamlit/config.toml`)
- Uploaded PDFs processed in-memory only — never written to disk
- No `st.secrets` or external service connections
- No stdout logging of financial field values
- SQLite file is local; user is responsible for encrypting their drive

---

## Implementation Phases

| Phase | Deliverable |
|---|---|
| **Phase 1** | `renderer.py` — PDF → image, coordinate scaling utilities |
| **Phase 2** | `template.py` — JSON save/load/list, bbox coordinate conversion |
| **Phase 3** | Page 1: Template Builder UI with drawable canvas |
| **Phase 4** | `extractor.py` — crop+extract using template bboxes, row iteration |
| **Phase 5** | `storage.py` — SQLite schema, insert, query, CSV export |
| **Phase 6** | Page 2: Extract UI, Page 3: History, Page 4: Settings |
| **Phase 7** | Polish: duplicate detection, amount sign normalization, date parsing |

---

## Requirements

```
pdfplumber>=0.11
pymupdf>=1.24
streamlit>=1.35
streamlit-drawable-canvas>=0.9
pandas>=2.0
Pillow>=10.0
```
