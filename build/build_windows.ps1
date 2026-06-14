# OCR Master - Windows build script
# Run from anywhere: right-click > "Run with PowerShell"
# Or from a terminal: powershell -ExecutionPolicy Bypass -File build\build_windows.ps1
#
# Prerequisites this script will install for you if missing:
#   - Python 3.11  (via winget)
#   - pip packages (via pip)
#   - Inno Setup 6 (via winget, for the installer step)

$RepoRoot = Split-Path $PSScriptRoot
Set-Location $RepoRoot

Write-Host ""
Write-Host " === OCR Master Windows Build ===" -ForegroundColor Cyan
Write-Host ""


# ── Helper: reload PATH from registry so installs take effect immediately ──────

function Refresh-Path {
    $machine = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $user    = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
}


# ── Helper: install a package via winget ──────────────────────────────────────

function Install-Via-Winget {
    param([string]$Id, [string]$DisplayName)

    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Host ""
        Write-Host "[ERROR] winget is not available on this machine." -ForegroundColor Red
        Write-Host "        Install $DisplayName manually, then re-run this script."
        Write-Host ""
        return $false
    }

    Write-Host ""
    Write-Host " $DisplayName is not installed." -ForegroundColor Yellow
    $choice = Read-Host " Install $DisplayName automatically via winget? [Y/N]"
    if ($choice -notmatch '^[Yy]') {
        Write-Host " Skipping $DisplayName install." -ForegroundColor Yellow
        return $false
    }

    Write-Host " Installing $DisplayName via winget..." -ForegroundColor Cyan
    winget install --id $Id --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "[ERROR] winget install of $DisplayName failed (exit $LASTEXITCODE)." -ForegroundColor Red
        Write-Host "        Try installing manually, then re-run this script."
        Write-Host ""
        return $false
    }

    Refresh-Path
    return $true
}


# ── Step 0: Clean previous build output ───────────────────────────────────────

Write-Host "[0/4] Cleaning previous build output..." -ForegroundColor Yellow
$CleanPaths = @("dist\OCRMaster", "build\OCRMaster", "build\Output")
foreach ($p in $CleanPaths) {
    if (Test-Path $p) {
        Remove-Item $p -Recurse -Force
        Write-Host "      Removed $p"
    }
}
Write-Host "      Clean done."
Write-Host ""


# ── Step 1: Ensure Python 3.11+ is available ──────────────────────────────────

Write-Host "[1/4] Checking Python..." -ForegroundColor Yellow

$pythonOk = $false
if (Get-Command python -ErrorAction SilentlyContinue) {
    $ver = python --version 2>&1
    Write-Host "      Found: $ver" -ForegroundColor Green
    $pythonOk = $true
} else {
    $installed = Install-Via-Winget -Id "Python.Python.3.11" -DisplayName "Python 3.11"
    if ($installed) {
        # After winget + PATH refresh, python may be under a versioned launcher name
        # Try both 'python' and 'py'
        if (Get-Command python -ErrorAction SilentlyContinue) {
            $ver = python --version 2>&1
            Write-Host "      Python ready: $ver" -ForegroundColor Green
            $pythonOk = $true
        } elseif (Get-Command py -ErrorAction SilentlyContinue) {
            Set-Alias python py -Scope Script
            $ver = python --version 2>&1
            Write-Host "      Python ready (via py launcher): $ver" -ForegroundColor Green
            $pythonOk = $true
        } else {
            # Last resort: find python.exe directly in common winget install paths
            $pyExe = Get-ChildItem "$env:LOCALAPPDATA\Programs\Python" -Filter "python.exe" -Recurse -ErrorAction SilentlyContinue |
                     Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
            if (-not $pyExe) {
                $pyExe = Get-ChildItem "C:\Python*" -Filter "python.exe" -ErrorAction SilentlyContinue |
                         Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
            }
            if ($pyExe) {
                Set-Alias python $pyExe -Scope Script
                $ver = python --version 2>&1
                Write-Host "      Python ready (found at $pyExe): $ver" -ForegroundColor Green
                $pythonOk = $true
            } else {
                Write-Host ""
                Write-Host "[NOTE] Python was installed but is not yet on PATH in this window." -ForegroundColor Yellow
                Write-Host "       Close this window, re-open it, and run build_windows.bat again."
                Write-Host ""
                Read-Host "Press Enter to exit"
                exit 1
            }
        }
    } else {
        Write-Host ""
        Write-Host "[ERROR] Python is required to build OCR Master." -ForegroundColor Red
        Write-Host "        Download Python 3.11 from https://www.python.org/downloads/"
        Write-Host "        Make sure to tick 'Add Python to PATH' during install."
        Write-Host ""
        Read-Host "Press Enter to exit"
        exit 1
    }
}
Write-Host ""


# ── Step 2: Install Python dependencies ───────────────────────────────────────

Write-Host "[2/4] Installing Python dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt --quiet
python -m pip install pyinstaller --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] pip install failed." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "      Dependencies ready." -ForegroundColor Green
Write-Host ""


# ── Step 3: Build with PyInstaller ────────────────────────────────────────────

Write-Host "[3/4] Building executable with PyInstaller..." -ForegroundColor Yellow
python -m PyInstaller build\OCRMaster.spec --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] PyInstaller build failed." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host ""
Write-Host "      Executable: dist\OCRMaster\OCRMaster.exe" -ForegroundColor Green
Write-Host "      Tip: test it before building the installer."
Write-Host ""


# ── Step 4: Compile installer with Inno Setup ─────────────────────────────────

Write-Host "[4/4] Looking for Inno Setup compiler (iscc)..." -ForegroundColor Yellow

$IsccCandidates = @(
    "iscc",
    "${env:LOCALAPPDATA}\Programs\Inno Setup 6\iscc.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\iscc.exe",
    "${env:ProgramFiles}\Inno Setup 6\iscc.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 5\iscc.exe"
)

$IsccPath = $null
foreach ($candidate in $IsccCandidates) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        $IsccPath = $candidate; break
    } elseif (Test-Path $candidate) {
        $IsccPath = $candidate; break
    }
}

if (-not $IsccPath) {
    $installed = Install-Via-Winget -Id "JRSoftware.InnoSetup" -DisplayName "Inno Setup 6"
    if ($installed) {
        Refresh-Path
        # Re-scan after install
        foreach ($candidate in $IsccCandidates) {
            if (Get-Command $candidate -ErrorAction SilentlyContinue) {
                $IsccPath = $candidate; break
            } elseif (Test-Path $candidate) {
                $IsccPath = $candidate; break
            }
        }
    }
}

if ($IsccPath) {
    Write-Host "[4/4] Compiling installer with Inno Setup..." -ForegroundColor Yellow
    & $IsccPath "build\installer.iss"
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host " Installer: build\Output\OCRMasterSetup.exe" -ForegroundColor Green
        Write-Host ""
        Write-Host " Build complete!" -ForegroundColor Green
        Write-Host " Distribute: build\Output\OCRMasterSetup.exe"
    } else {
        Write-Host "[ERROR] Inno Setup compilation failed." -ForegroundColor Red
    }
} else {
    Write-Host ""
    Write-Host "[4/4] Inno Setup not found - skipping installer build." -ForegroundColor Yellow
    Write-Host "      To build the installer later:"
    Write-Host "        winget install JRSoftware.InnoSetup"
    Write-Host "      Then re-run this script."
}

Write-Host ""
Read-Host "Press Enter to exit"
