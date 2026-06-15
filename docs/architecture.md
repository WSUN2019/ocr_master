# OCR Master — Architecture

## Overview

**Disclaimer:** OCR Master is a working proof of concept and technology demonstrator of AI-assisted software development. It is provided as-is with no expressed or implied warranty. Use at your own risk.

A PyQt6 desktop application designed to process bank statement files locally. No web server, external API calls, or cloud services are intentionally used, though no guarantee is made as to the complete absence of network activity.

---

## Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| UI | `PyQt6` | Native desktop window, sidebar navigation, widgets |
| PDF rendering | `pymupdf` (fitz) | Render PDF pages to images at 300 DPI for OCR; 2x for canvas display |
| OCR | `pytesseract` + Tesseract | Extract text with word-level bounding boxes (`image_to_data`) |
| PDF text | `pdfplumber` | Supplemental PDF text extraction |
| Data | `pandas` | In-memory DataFrame for table display and manipulation |
| Storage | `sqlite3` (stdlib) | Local persistent database — transactions + import log |
| Export | `csv` / `pandas` | Flat-file CSV output |
| Templates | JSON files | Human-readable field-to-bbox mappings, one file per bank layout |
| Image processing | `Pillow` | PIL Image conversion between formats |
| Config | `json` (stdlib) | User-configurable paths written to `config.json` |

---

## Directory Layout

```
ocr_master/
├── app.py                    # Entry point — QApplication + MainWindow
│
├── core/                     # Backend logic (no UI dependencies)
│   ├── app_paths.py          # Data directory resolver (dev vs frozen/installed)
│   ├── config.py             # Singleton config manager — all 7 user-configurable paths
│   ├── extractor.py          # Tesseract OCR + field mapping from templates
│   ├── renderer.py           # PDF page → PIL Image + coordinate scaling
│   ├── storage.py            # SQLite read/write, CSV export
│   └── template.py           # Template load/save/list (JSON files)
│
├── ui/                       # PyQt6 widgets
│   ├── main_window.py        # Main window + sidebar navigation
│   ├── template_builder.py   # Draw bounding boxes on PDF, define fields
│   ├── canvas_widget.py      # Drawing canvas + undo/redo stack
│   ├── extract_widget.py     # Single-file extraction UI
│   ├── ocr_worker.py         # Threaded OCR worker (QThread)
│   ├── batch_widget.py       # Batch folder processing UI
│   ├── batch_worker.py       # Threaded batch worker (QThread)
│   ├── history_widget.py     # Transaction Report — query, filter, edit, export
│   ├── database_widget.py    # Database browser — raw table viewer, import_log management
│   ├── settings_widget.py    # Template management + configurable paths
│   ├── help_widget.py        # Workflow guide
│   ├── about_widget.py       # App info + experiment notes
│   └── styles.py             # PyQt6 stylesheet (light theme)
│
├── build/                    # Windows packaging
│   ├── build_windows.bat     # Double-click launcher for the build script
│   ├── build_windows.ps1     # Full build: clean → deps → PyInstaller → Inno Setup
│   ├── OCRMaster.spec        # PyInstaller configuration
│   └── installer.iss         # Inno Setup script → OCRMasterSetup.exe
│
├── create_dev_zip.bat        # Zip source files for sharing with another developer
├── templates/                # User-created bank templates (JSON, gitignored)
├── input_files/Examples/     # Sample statement images for testing
├── docs/                     # Documentation and assets
└── requirements.txt
```

---

## Data Directory & Configurable Paths

### Path Resolution

`core/app_paths.py` resolves the app data root (`APP_DIR`):

| Mode | `APP_DIR` |
|------|----------|
| Development (`python app.py`) | Repo root |
| Installed / frozen (`OCRMaster.exe`) | `Documents\OCR Master\` |

In frozen mode the path falls back to the home directory if `Documents` doesn't exist (rare on non-Windows systems).

### Configurable Paths (core/config.py)

All 7 paths are user-configurable and stored in `config.json` (in `APP_DIR`). Defaults when installed:

| Path key | Default location | Purpose |
|----------|-----------------|---------|
| `tesseract_path` | `C:\Program Files\Tesseract-OCR\tesseract.exe` | OCR engine binary |
| `db_path` | `Documents\OCR Master\ocr_master.db` | Transaction database |
| `templates_dir` | `Documents\OCR Master\templates\` | Bank layout templates |
| `input_dir` | `Documents\OCR Master\input_files\` | Statement imports |
| `output_dir` | `Documents\OCR Master\output\` | CSV exports |
| `batch_import_dir` | `Documents\OCR Master\batch_import\` | Batch input folder |
| `batch_complete_dir` | `Documents\OCR Master\batch_complete\` | Processed files |

All consumers call `get_config().<property>` at runtime — never cached at import time — so path changes in Settings take effect immediately without a restart.

---

## Core Concept: Visual Template Builder

### How It Works

1. User loads a sample bank statement image or PDF
2. PDF page is rendered at 2x scale and displayed on a canvas widget
3. User draws rectangles over each data field (date, description, debit, credit, balance)
4. Each rectangle is labeled with a field name and optional flags (Repeat, Sub-group, Group Anchor, Currency, Date format)
5. Template saved as `templates/<slug>.json`
6. On future statements from the same bank: select template → run OCR → done

### Undo / Redo

`canvas_widget.py` maintains a snapshot-based undo stack:

- `push_undo()` serialises the current canvas state via `get_field_defs()` and appends it to `_undo_stack` (clears `_redo_stack`)
- `undo()` / `redo()` pop a snapshot and call `_restore_snapshot()`, which rebuilds all `BoxItem`s from the saved list
- A `_restoring` flag prevents re-entrant pushes during restoration
- `BoxItem.itemChange(ItemPositionChange)` fires on the first pixel of a drag and pushes undo once; `mouseReleaseEvent` resets the per-drag flag so the next drag can push again
- `_ResizeHandle.mousePressEvent` pushes undo before resize begins
- Key bindings: **Ctrl+Z** → undo, **Ctrl+Shift+Z** / **Ctrl+Y** → redo (template builder skips undo when a text input has focus)

### Coordinate System

```
PDF canvas display (2x scale)       OCR rendering (300/72 DPI scale)
  origin: top-left                    origin: top-left
  units: pixels at 2x DPI            units: pixels at 300 DPI

Template stores: canvas pixel coords (2x space)
OCR scaling:     ratio = (300/72) / 2.0  ~2.083x

extractor.py applies this ratio to all bbox coords before
filtering Tesseract word positions.
```

---

## Template JSON Format

```json
{
  "name": "HSBC",
  "version": 1,
  "created_at": "2026-06-01T00:00:00",
  "fields": [
    {
      "name": "transaction_date",
      "bbox": [42.0, 310.0, 180.0, 2900.0],
      "repeat": false,
      "sub_group": false,
      "group_anchor": true,
      "concat_in_group": false,
      "currency": false,
      "date_format": "DD MMM YY"
    },
    {
      "name": "description",
      "bbox": [185.0, 310.0, 800.0, 2900.0],
      "concat_in_group": true,
      "currency": false,
      "date_format": ""
    },
    {
      "name": "debit",
      "bbox": [805.0, 310.0, 960.0, 2900.0],
      "currency": true,
      "date_format": ""
    },
    {
      "name": "balance",
      "bbox": [1100.0, 310.0, 1280.0, 2900.0],
      "currency": true,
      "date_format": ""
    }
  ],
  "row_detection": {
    "strategy": "fixed_regions"
  },
  "skip_pages": [1],
  "page_range": [2, 99]
}
```

### Field Flags

| Flag | Effect |
|------|--------|
| `repeat` | Value appears once (header); copied to every transaction row |
| `sub_group` | Fill-down: value appears once per group, blank rows inherit it |
| `group_anchor` | A new non-null value here starts a new transaction group |
| `concat_in_group` | Multi-line field; values from all rows in a group are joined |
| `currency` | Reconstruct 2-decimal amounts when OCR drops the decimal point or thousands comma (e.g. `100000` → `1000.00`, `10050` → `100.50`) |
| `date_format` | Source date format string (`DD MMM YY`, `DD/MM/YYYY`, `M/D/YY`, etc.); validates day ≤ 31 and month ≤ 12; fuzzy-matches month abbreviations; unparseable dates stored as raw OCR string and shown in red |

### Row Detection Strategies

| Strategy | Use case |
|----------|---------|
| `fixed_regions` | Tall column bboxes; words filtered by Y-band into rows. Best for most statements. |
| `repeat_vertical` | One row drawn; extractor steps down at fixed `row_height_pts` intervals. |

---

## OCR Data Flow

```
TEMPLATE BUILDER (one-time per bank format)
  Load sample image/PDF
        |
        v
  renderer.py: PDF page -> PIL Image (2x scale for canvas display)
        |
        v
  canvas_widget.py: user draws rectangles, labels each field
        |
        v
  template.py: save field bboxes (canvas pixel coords) to templates/<slug>.json


EXTRACTION (for each new statement)
  Load file + select template
        |
        v
  extractor.py: _load_pages() -- PDF rendered at 300 DPI via pymupdf
        |
        v
  extractor.py: _scale_template_for_pdf() -- scale canvas coords to 300 DPI space
        |
        v
  extractor.py: _ocr_page() -- single Tesseract call via image_to_data()
                returns word list with {text, left, top, right, bottom}
        |
        v
  extractor.py: _extract_fixed_regions() or _extract_repeat_vertical()
                filters words into field bboxes, clusters by Y-band into rows
        |
        v
  Optional: _apply_row_grouping() -- collapse multi-line transactions
  Optional: fill-forward for sub_group fields
        |
        v
  List of row dicts -> pandas DataFrame -> UI table display
        |
        +-- inline edit -> save to SQLite (storage.py)
        +-- CSV export
```

---

## SQLite Schema

```sql
CREATE TABLE transactions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_name       TEXT,
    source_file      TEXT,
    file_row         INTEGER,
    template_name    TEXT,
    account_number   TEXT,
    statement_period TEXT,
    transaction_date TEXT,
    post_date        TEXT,
    description      TEXT,
    amount           REAL,
    balance          REAL,
    category         TEXT,
    imported_at      TEXT,
    raw_data         TEXT,   -- JSON blob of all OCR'd field values
    note             TEXT    -- auto-stamped when a cell is edited inline
);

CREATE TABLE import_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    filename      TEXT,      -- source file path (used for duplicate detection)
    template_name TEXT,
    pages         INTEGER,
    rows_found    INTEGER,
    imported_at   TEXT,
    status        TEXT
);
```

**`balance_check`** is computed in-memory at display time (running balance from OCR'd data vs. extracted `balance` column) and is never stored in the database.

**Duplicate detection** (`is_already_imported`) queries `import_log.filename`. Deleting a batch via the Report page removes matching rows from both `transactions` and `import_log`, so the same file can be re-extracted cleanly.

**Database tab** (`database_widget.py`) lets the user browse either table with live row counts, delete individual `import_log` entries without touching transaction history, and export any table to CSV. Internal SQLite tables (e.g. `sqlite_sequence`) are excluded from the table list.

Templates are stored as JSON files in `templates/` — not in SQLite — so they are portable, human-readable, and easy to back up or share between machines.

---

## Windows Build Pipeline

```
build_windows.ps1
  |
  +- Clean: dist\OCRMaster\, build\OCRMaster\, build\Output\
  |
  +- pip install -r requirements.txt
  +- pip install pyinstaller
  +- pyinstaller build\OCRMaster.spec
  |    +- Output: dist\OCRMaster\OCRMaster.exe  (self-contained folder)
  |
  +- iscc build\installer.iss
       +- Output: build\Output\OCRMasterSetup.exe  (distribute this)
```

### PyInstaller Notes (`OCRMaster.spec`)

- **Folder mode** (not one-file): faster startup, easier to inspect
- **Excluded**: `tkinter`, `matplotlib`, `scipy`, `pyarrow` — not used, saves ~80 MB
- **Hidden imports**: `pdfplumber`, `pdfminer`, `fitz` — dynamically imported at runtime
- **Bundled DLLs**: `python3*.dll`, `vcruntime*.dll` — prevents startup failures on machines without VC++ Redist

### Installer Notes (`installer.iss`)

- App binaries → `C:\Program Files\OCR Master\`
- Wizard page: Tesseract (auto via winget or manual)
- Wizard page: data folder picker (default `Documents\OCR Master\`)
- Writes complete 7-path `config.json` to the user-selected data folder at install completion
- Creates all data subdirectories
- Uninstall asks whether to delete user data or keep it

### Developer Sharing

`create_dev_zip.bat` runs `git archive HEAD` to produce a clean dated zip of all tracked source files. It excludes build output, user data (database, config, statements), and `__pycache__` automatically because git only archives tracked files. The recipient unzips and runs `setup_windows.bat` to get started.
