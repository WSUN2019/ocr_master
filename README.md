# OCR Master — Bank Statement Extractor

A fully local, offline desktop application for extracting transaction data from bank statement images. No cloud, no AI APIs, no data ever leaves your machine.

## Features

- **Visual template builder** — open a sample statement image, draw red boxes over each field, label them, save as a named template
- **Multi-bank support** — create templates A, B, C, D for different banks; assign the right template when extracting
- **OCR extraction** — Tesseract OCR reads text from each mapped region
- **Table review** — extracted data shown in an editable table before saving
- **SQLite storage** — all transactions stored locally in `ocr_master.db`
- **CSV export** — export any filtered view to a flat file
- **History & search** — query by date range, template, or keyword

## Requirements

**Python packages** (install with pip):
```
pip install -r requirements.txt
```

**Tesseract OCR engine** (system install):
```bash
# Linux
sudo apt-get install -y tesseract-ocr

# macOS
brew install tesseract

# Windows
# Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
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

1. **Template Builder** — open a sample image from a bank, draw boxes over each field (date, description, amount, balance), save as a named template
2. **Extract** — add statement files (JPG, PNG, PDF), pick the matching template, click Run OCR
3. **Review** — check the extracted table, make any corrections
4. **Save / Export** — save to the local database and/or download as CSV
5. **History** — filter and re-export any previously imported data

## Security

- Runs entirely on `localhost` — no network connections
- No data sent to any external service
- PDFs and images processed in memory only
- SQLite database stays on your machine

## Supported File Types

- JPEG / PNG — scanned statement images
- PDF — scanned or digital statements (multi-page supported)
