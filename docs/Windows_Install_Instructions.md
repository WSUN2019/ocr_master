# Windows Install Instructions — OCR Master

## Overview

These steps produce `OCRMasterSetup.exe` — a double-click installer that handles everything: installs the app and a bundled copy of Tesseract OCR, and lets the user choose where their data files live.

Tesseract is **bundled inside the installer** — end users do not need to install it separately.

---

## Prerequisites (build machine only, one-time)

| Tool | Where | Notes |
|------|-------|-------|
| **Python 3.11+** | https://www.python.org/downloads/ | Check "Add Python to PATH" during install |
| **Tesseract OCR** | `winget install UB-Mannheim.TesseractOCR` | Required on the **build machine** so the build script can bundle it |
| **Inno Setup 6** | https://jrsoftware.org/isinfo.php | Free; creates the installer EXE |

---

## Build Steps

### 1 — Clone the repo

```bat
git clone https://github.com/WSUN2019/ocr_master.git
cd ocr_master
```

### 2 — Run the build script

**Easiest:** double-click `build\build_windows.bat`

Or from a terminal:

```powershell
powershell -ExecutionPolicy Bypass -File build\build_windows.ps1
```

The script automatically:
1. Cleans `dist\OCRMaster\`, `build\OCRMaster\`, and `build\Output\` for a fresh build
2. Installs Python dependencies (`requirements.txt` + `pyinstaller`)
3. Runs PyInstaller → `dist\OCRMaster\OCRMaster.exe`
4. Copies Tesseract from `C:\Program Files\Tesseract-OCR\` into `dist\OCRMaster\tesseract\`
5. Compiles the Inno Setup installer → `build\Output\OCRMasterSetup.exe`

If Inno Setup is not found, the script prints instructions for the manual compile step.

### 3 — Test before distributing (recommended)

```bat
dist\OCRMaster\OCRMaster.exe
```

Verify the app opens and OCR works on a sample file before packaging.

### 4 — Distribute

Send `build\Output\OCRMasterSetup.exe` to end users. That single file is the complete installer.

---

## What the Installer Does

### Install flow

1. Selects install directory: `C:\Program Files\OCR Master\`
2. **Data folder picker** — user chooses where all data files are stored (default: `Documents\OCR Master\`)
3. Copies app binaries **and bundled Tesseract** to `C:\Program Files\OCR Master\`
4. Writes `config.json` with all 7 paths to the user-selected data folder (`Documents\OCR Master\` by default)
5. Creates all data subdirectories under the selected data folder
6. Checks for Visual C++ Redistributable; offers download if missing
7. Creates Start Menu shortcut + optional Desktop shortcut
8. Offers to launch the app immediately

No internet connection is required during installation.

### User data locations (defaults)

All user data lives under a single folder the user chooses during install. Default is `Documents\OCR Master\`.

| Data | Location |
|------|---------|
| Database (`ocr_master.db`) | `Documents\OCR Master\` |
| Templates | `Documents\OCR Master\templates\` |
| Config (`config.json`) | `Documents\OCR Master\` |
| Input files | `Documents\OCR Master\input_files\` |
| CSV output | `Documents\OCR Master\output\` |
| Batch import | `Documents\OCR Master\batch_import\` |
| Batch complete | `Documents\OCR Master\batch_complete\` |

All paths can be changed after install in **Settings → Paths & Locations**.

### Uninstall

Via Windows **Settings → Apps** or **Control Panel → Programs**.

On uninstall, the installer asks:
- **YES** — delete `Documents\OCR Master\` (removes database, templates, and settings permanently)
- **NO** — keep data (safe for reinstalling or upgrading later)

---

## Notes

- **64-bit Windows only** — matches Tesseract's `w64` build and Python 3.11+
- **Tesseract must be installed on the build machine** — the build script copies it from `C:\Program Files\Tesseract-OCR\`; end users do not need it separately
- The build script window stays open after completion (or on error) so you can read the output

---

## File Reference

| File | Purpose |
|------|---------|
| `build\build_windows.bat` | Double-click launcher |
| `build\build_windows.ps1` | Full build script: clean, deps, PyInstaller, Inno Setup |
| `build\OCRMaster.spec` | PyInstaller configuration |
| `build\installer.iss` | Inno Setup script |
| `core\app_paths.py` | Resolves APP_DIR: repo root in dev, `Documents\OCR Master\` when installed |
| `core\config.py` | Singleton config manager for all 7 configurable paths |
| `create_dev_zip.bat` | Creates a clean dated zip of source files for sharing with another developer |
