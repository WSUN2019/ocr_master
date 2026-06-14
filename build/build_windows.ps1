# OCR Master — Windows build script
# Run from anywhere: right-click → "Run with PowerShell"
# Or from a terminal: powershell -ExecutionPolicy Bypass -File build\build_windows.ps1

# Always work from the repo root (one level above this script)
$RepoRoot = Split-Path $PSScriptRoot
Set-Location $RepoRoot

Write-Host ""
Write-Host " === OCR Master Windows Build ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python not found. Install Python 3.11+ from python.org" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
python --version

# Step 2: Install dependencies
Write-Host "[1/3] Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] pip install failed." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Step 3: Run PyInstaller
Write-Host "[2/3] Building executable with PyInstaller..." -ForegroundColor Yellow
pyinstaller build\OCRMaster.spec --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] PyInstaller build failed." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "[3/3] Done!" -ForegroundColor Green
Write-Host ""
Write-Host " Output: dist\OCRMaster\OCRMaster.exe"
Write-Host ""
Write-Host " Next steps:"
Write-Host "   - Test:    double-click dist\OCRMaster\OCRMaster.exe"
Write-Host "   - Install: open build\installer.iss in Inno Setup Compiler and press F9"
Write-Host "              Output will be: build\Output\OCRMasterSetup.exe"
Write-Host ""
Read-Host "Press Enter to exit"
