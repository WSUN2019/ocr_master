# Windows Install Instructions — OCR Master

## Overview

These steps produce a double-click installer (`OCRMasterSetup.exe`) that your customer runs once. The app then appears in Start Menu / Desktop with no terminal required.

---

## Prerequisites (one-time setup on a Windows machine)

| Tool | Where to get it | Notes |
|------|----------------|-------|
| **Python 3.11+** | https://www.python.org/downloads/ | Check "Add Python to PATH" during install |
| **Tesseract OCR** | https://github.com/UB-Mannheim/tesseract/wiki | Download `tesseract-ocr-w64-setup-*.exe`; check "Add to PATH" |
| **Inno Setup** | https://jrsoftware.org/isinfo.php | Free; used to create the installer EXE |

---

## Build Steps

### 1 — Clone the repo

```bat
git clone https://github.com/WSUN2019/ocr_master.git
cd ocr_master
```

### 2 — Run the build script

Right-click `build\build_windows.ps1` in Windows Explorer → **Run with PowerShell**

Or from a terminal:
```powershell
powershell -ExecutionPolicy Bypass -File build\build_windows.ps1
```

This script:
- Changes to the repo root automatically (works regardless of where it is launched from)
- Installs all Python dependencies (`requirements.txt` + `pyinstaller`)
- Runs PyInstaller using `build\OCRMaster.spec`
- Outputs a self-contained folder at `dist\OCRMaster\`

### 3 — Test the raw executable (optional)

```bat
dist\OCRMaster\OCRMaster.exe
```

The app should open with no console window. Verify OCR works on a sample file before packaging.

### 4 — Build the installer

1. Open **Inno Setup Compiler** (installed in step above)
2. File → Open → browse to `build\installer.iss`
3. Press **F9** (or Build → Compile)
4. Output: `build\Output\OCRMasterSetup.exe`

### 5 — Distribute

Send `OCRMasterSetup.exe` to the customer. That single file is the full installer.

---

## What the Installer Does

- Installs to `C:\Program Files\OCRMaster\`
- Creates a Start Menu shortcut
- Optionally creates a Desktop shortcut (user choice during install)
- Detects if Tesseract is missing → offers to open the download page automatically
- Includes an uninstaller (visible in Windows "Add or Remove Programs")

---

## Important Notes

- **User data** (`templates/`, `ocr_master.db`, `batch_import/`, `batch_complete/`) is stored
  **next to** `OCRMaster.exe` inside `Program Files\OCRMaster\` — it is **not** removed on
  uninstall, so customer data is safe across upgrades.

- **App icon:** To add a custom icon, place `icon.ico` in the `build/` folder, then uncomment
  the `icon=` line in `build\OCRMaster.spec` before running the build script.

- **64-bit only:** The installer targets 64-bit Windows. This matches Tesseract's `w64` build.

- **PyInstaller must run on Windows** — you cannot cross-compile from macOS/Linux.

---

## File Reference

| File | Purpose |
|------|---------|
| `build\build_windows.ps1` | One-command build: installs deps + runs PyInstaller |
| `build\OCRMaster.spec` | PyInstaller spec (entry point, hidden imports, excludes) |
| `build\installer.iss` | Inno Setup script — produces `OCRMasterSetup.exe` |
| `core\app_paths.py` | Path resolver — ensures data dirs work both frozen and in dev |
