# OCR Master — Bank Statement Extractor

> **Experiment:** This project was built entirely using **VS Code + Claude Code** (Anthropic's AI coding assistant) — from blank repo to a fully functional PyQt6 desktop application, Windows `.exe` installer, and a documented path to Microsoft Store publishing.
>
> **Finding:** AI-assisted coding delivers remarkable speed in the first 80% — architecture, core logic, UI layout, and build pipeline all came together rapidly. The remaining 20% — true polish, edge-case handling, and production-grade fit-and-finish — proved to take as much effort as the first 80%. A classic Tortoise and Hare dynamic: fast out of the gate, but the finish line moves.

---

A fully local, offline desktop application for extracting structured transaction data from bank statement images and PDFs. No cloud, no AI APIs, no data ever leaves your machine.

## Screenshot

![OCR Master — Template Builder with SaiminBank template](docs/screenshot.png)

---

## Features

- **Visual template builder** — load a sample statement image, draw bounding boxes over each field (date, description, debit, credit, balance), label and save as a named template
- **Multi-bank support** — create one template per bank layout; a `SaiminBank` example template is included
- **Repeat & Sub-group fields** — mark header fields as *Repeat* (copied to every row) or *Sub-group* (fill-down for banks like RBS where date/balance appear once per row group)
- **Tesseract OCR** — runs once per page; bounding-box crops map extracted text to fields
- **Single-file Extract** — add files manually, review and edit the table inline before saving
- **Batch Processing** — point at a folder; all files process under one batch name; each file moves to `batch_complete/` on success
- **Balance validation** — auto-computed `balance_check` column (✓ green / ✗ red); sign convention auto-detected; reruns on every cell edit
- **Inline editing** — double-click any cell to correct OCR errors; note column auto-stamped with before/after
- **Configurable paths** — all 7 data paths (Tesseract, database, templates, input, output, batch folders) are user-configurable in Settings
- **SQLite storage** — all transactions stored locally
- **CSV export** — export any filtered view
- **History & search** — query by date range, template, or keyword; delete batches

---

## Windows — Install (end users)

**Run `OCRMasterSetup.exe`** — one file installs everything.

The installer:
- Installs the app to `C:\Program Files\OCR Master\`
- Offers to install Tesseract OCR automatically (via winget) or open the download page
- Lets you choose where user files (imports, exports, batch folders) are stored — default: `Documents\OCR Master\`
- Stores app data (templates, database, config) in `%APPDATA%\OCR Master\` — no admin rights needed for day-to-day use
- Creates Start Menu + optional Desktop shortcuts
- Full uninstaller via Windows Settings → Apps; on uninstall asks whether to keep or delete your data

> Tesseract auto-install via winget requires Windows 10 (1809+) or Windows 11.

---

## Windows — Build from source

Double-click `build\build_windows.bat`, or from a terminal:

```powershell
powershell -ExecutionPolicy Bypass -File build\build_windows.ps1
```

The script cleans previous output, installs dependencies, runs PyInstaller, and compiles the Inno Setup installer automatically.

**Output:** `build\Output\OCRMasterSetup.exe` — this is the file you distribute.

See [docs/Windows_Install_Instructions.md](docs/Windows_Install_Instructions.md) for full prerequisites and step-by-step detail.

---

## Linux / macOS — Run from source

```bash
sudo apt-get install -y tesseract-ocr   # Debian/Ubuntu
brew install tesseract                   # macOS

pip install -r requirements.txt
python3 app.py
```

---

## Workflow

1. **Template Builder** — open a sample statement image, draw boxes over each column, name and configure fields, save the template
2. **Extract** — add files, pick the template, run OCR, review and edit inline, save to database or export CSV
3. **Batch** — drop files into the import folder, pick the template, click *Start Batch*; files are processed and moved automatically
4. **History** — filter, search, edit, and export saved transactions

---

## User data locations (default, all configurable in Settings)

| Data | Default location |
|------|-----------------|
| Database + templates + config | `%APPDATA%\OCR Master\` |
| Input files, output, batch folders | `Documents\OCR Master\` |
| Development (running from source) | Repo root |

All paths can be changed under **Settings → Paths & Locations** without restarting the app.

---

## Security & Privacy

- Runs entirely on your local machine — no network connections
- No data sent to any external service, cloud, or AI
- PDFs and images processed in memory; never uploaded
- SQLite database stays on your machine

---

## Supported File Types

| Format | Notes |
|--------|-------|
| JPEG / PNG | Scanned or photographed statement images |
| PDF | Scanned or digital; multi-page supported, rendered at 300 DPI |

---

## Microsoft Store

The app is structured for MSIX packaging and Store submission. The binary output from PyInstaller can be wrapped with the MSIX Packaging Tool and submitted via Microsoft Partner Center. This step is documented but not yet completed — it remains part of the original experiment scope.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| UI | PyQt6 (Qt 6) |
| OCR | Tesseract + pytesseract |
| PDF rendering | PyMuPDF (fitz) at 300 DPI |
| Data | pandas + SQLite |
| Packaging | PyInstaller + Inno Setup 6 |
| Language | Python 3.11+ |
