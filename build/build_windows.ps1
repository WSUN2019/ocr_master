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
Write-Host "[1/4] Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] pip install failed." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Step 3: Run PyInstaller
Write-Host "[2/4] Building executable with PyInstaller..." -ForegroundColor Yellow
pyinstaller build\OCRMaster.spec --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] PyInstaller build failed." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host " Executable: dist\OCRMaster\OCRMaster.exe" -ForegroundColor Green
Write-Host " Tip: Test it before building the installer."
Write-Host ""

# Step 4: Compile installer with Inno Setup (if available)
Write-Host "[3/4] Looking for Inno Setup compiler (iscc)..." -ForegroundColor Yellow

# Common install locations for Inno Setup
$IsccCandidates = @(
    "iscc",   # in PATH
    "${env:LOCALAPPDATA}\Programs\Inno Setup 6\iscc.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\iscc.exe",
    "${env:ProgramFiles}\Inno Setup 6\iscc.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 5\iscc.exe"
)

$IsccPath = $null
foreach ($candidate in $IsccCandidates) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        $IsccPath = $candidate
        break
    } elseif (Test-Path $candidate) {
        $IsccPath = $candidate
        break
    }
}

if ($IsccPath) {
    Write-Host "[3/4] Compiling installer with Inno Setup..." -ForegroundColor Yellow
    & $IsccPath "build\installer.iss"
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host " Installer: build\Output\OCRMasterSetup.exe" -ForegroundColor Green
        Write-Host ""
        Write-Host "[4/4] Build complete!" -ForegroundColor Green
        Write-Host ""
        Write-Host " Distribute:  build\Output\OCRMasterSetup.exe"
    } else {
        Write-Host "[ERROR] Inno Setup compilation failed." -ForegroundColor Red
    }
} else {
    Write-Host "[3/4] Inno Setup not found — skipping installer build." -ForegroundColor Yellow
    Write-Host ""
    Write-Host " To build the installer:"
    Write-Host "   1. Download Inno Setup free from https://jrsoftware.org/isinfo.php"
    Write-Host "   2. Open build\installer.iss in Inno Setup Compiler and press F9"
    Write-Host "      Output: build\Output\OCRMasterSetup.exe"
    Write-Host ""
    Write-Host "[4/4] Done (installer step skipped)." -ForegroundColor Yellow
}

Write-Host ""
Read-Host "Press Enter to exit"
