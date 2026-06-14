# Windows Install Instructions — OCR Master

## Overview

These steps produce a double-click installer (`OCRMasterSetup.exe`) that handles everything:
installs the app, offers to install Tesseract automatically, and creates Start Menu / Desktop shortcuts.

---

## Prerequisites (one-time, on the build machine)

| Tool | Where to get it | Notes |
|------|----------------|-------|
| **Python 3.11+** | https://www.python.org/downloads/ | Check "Add Python to PATH" during install |
| **Inno Setup 6** | https://jrsoftware.org/isinfo.php | Free; creates the installer EXE |

> Tesseract does **not** need to be on the build machine — the installer handles it for end users.

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

The script:
- Installs Python dependencies (`requirements.txt` + `pyinstaller`)
- Runs PyInstaller → produces `dist\OCRMaster\OCRMaster.exe`
- **Automatically compiles the Inno Setup installer** if `iscc` is found in PATH
  or at the default Inno Setup install location
- Output: `build\Output\OCRMasterSetup.exe`

If Inno Setup is not found, the script prints instructions for the manual compile step.

### 3 — Test the raw executable (recommended)

```bat
dist\OCRMaster\OCRMaster.exe
```

Verify the app opens and OCR works on a sample file before distributing.

### 4 — Distribute

Send `build\Output\OCRMasterSetup.exe` to end users. That single file is the complete installer.

---

## What the Installer Does

### Install flow

1. Chooses install directory: `C:\Program Files\OCR Master\`
2. If Tesseract is **not** installed, shows a choice page:
   - **Install automatically** — runs `winget install UB-Mannheim.TesseractOCR` silently
   - **Install manually** — opens the Tesseract download page in a browser
3. Copies the app to `C:\Program Files\OCR Master\`
4. Creates user data folder at `%APPDATA%\OCR Master\` (templates, DB, config)
5. Creates Start Menu shortcut + optional Desktop shortcut
6. Checks for Visual C++ Redistributable; offers download if missing
7. Offers to launch the app immediately

### User data location

All user-generated data lives in `%APPDATA%\OCR Master\` (not Program Files):

| Folder / File | Contents |
|--------------|----------|
| `templates\` | Saved bank statement templates (JSON) |
| `ocr_master.db` | Transaction history (SQLite) |
| `config.json` | Tesseract path override |
| `input_files\` | Import folder |
| `output\` | CSV exports |

This means user data is **not removed on uninstall** unless the user explicitly chooses to delete it.

### Uninstall

Uninstall via Windows **Settings → Apps** or **Control Panel → Programs**.

On uninstall, the installer asks:
- **YES** — delete `%APPDATA%\OCR Master\` (removes templates, history, settings)
- **NO** — keep data (safe for reinstalling later or upgrading)

---

## Important Notes

- **64-bit Windows only** — matches Tesseract's `w64` build and Python 3.11+
- **Tesseract auto-install requires winget** — available on Windows 10 1809+ and all Windows 11. Older systems should use the manual option.
- **App icon:** Place `icon.ico` in the `build/` folder, then uncomment the `icon=` line in `build\OCRMaster.spec`

---

## File Reference

| File | Purpose |
|------|---------|
| `build\build_windows.bat` | Double-click launcher — calls the PS1 script |
| `build\build_windows.ps1` | Full build: deps → PyInstaller → Inno Setup |
| `build\OCRMaster.spec` | PyInstaller configuration |
| `build\installer.iss` | Inno Setup script → produces `OCRMasterSetup.exe` |
| `core\app_paths.py` | Path resolver — dev uses repo root, frozen uses `%APPDATA%\OCR Master` |
