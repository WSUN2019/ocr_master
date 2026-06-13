# OCR Master — Bank Statement Extractor

A fully local, offline desktop application for extracting structured transaction data from bank statement images and PDFs. No cloud, no AI APIs, no data ever leaves your machine.

## How It Works

![How to Use — workflow diagram](docs/how_to_use.png)

## Features

- **Visual template builder** — load a sample statement image, draw bounding boxes over each field (date, description, debit, credit, balance), label and save as a named template
- **Multi-bank support** — create one template per bank layout; assign the right template at extract time
- **Repeat & Sub-group fields** — mark header fields as *Repeat* (value copied to every row) or *Sub-group* (fill-down for banks like RBS where date/balance appear once per row group)
- **Tesseract OCR extraction** — runs once per page for performance; bounding-box crops map text to fields
- **Single-file Extract** — add files manually, review and edit the table inline before saving to the database
- **Batch Processing** — point at a folder of statement files; all process under one shared batch name; each file moves to a `batch_complete/` folder after saving; run log shows per-file outcome
- **Balance validation** — auto-computed `balance_check` column (✓ green / ✗ red) verifies running balance using debit/credit math; sign convention auto-detected per batch; reruns instantly when any amount cell is edited
- **Inline editing** — double-click any cell to correct OCR errors; original value pre-filled; note column auto-stamped with `Manual override: [field] 'before' → 'after'`
- **SQLite storage** — all transactions stored locally in `ocr_master.db`
- **CSV export** — export any filtered view to a flat file
- **History & search** — query by date range, template, or keyword; continue editing saved transactions; delete batches

## Requirements

**Python packages:**
```bash
pip install -r requirements.txt
```

**Tesseract OCR engine** (system install):
```bash
# Linux
sudo apt-get install -y tesseract-ocr

# macOS
brew install tesseract

# Windows — download installer from:
# https://github.com/UB-Mannheim/tesseract/wiki
```

## Run

```bash
./run.sh
```

Or directly:
```bash
python3 app.py
```

## Workflow

1. **Template Builder** — open a sample statement image, draw boxes over each field column, name them, set Repeat/Sub-group flags as needed, and save the template
2. **Extract** (single run) — add files manually, choose the template, click *Run OCR*; right-click or press Delete to remove files from the list; review and edit the extracted table inline; save to database or export CSV
3. **Batch** (folder run) — drop all statement files into `batch_import/`, select the template, optionally edit the batch name, click *Start Batch*; each file is processed and moved to `batch_complete/` automatically; all rows share one batch name
4. **History** — filter by date, template, or keyword; continue editing rows; delete batches when no longer needed

## Security

- Runs entirely on your local machine — no network connections made
- No data sent to any external service, cloud, or AI
- PDFs and images processed in memory only
- SQLite database file stays on your machine at `ocr_master.db`

## Supported File Types

- JPEG / PNG — scanned or photographed statement images
- PDF — scanned or digital statements (multi-page supported, rendered at 300 DPI)
