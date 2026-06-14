# OCR Master — Dev environment setup
# Installs Python 3.11, pip dependencies, and Tesseract OCR so you can
# run the app from source with:  python app.py   (or double-click run_in_windows.bat)
#
# Run via:  setup_windows.bat   (double-click)

$RepoRoot = Split-Path $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

Write-Host ""
Write-Host " === OCR Master Setup ===" -ForegroundColor Cyan
Write-Host ""


# ── Helper: reload PATH from registry ─────────────────────────────────────────

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
        Write-Host " [ERROR] winget is not available." -ForegroundColor Red
        Write-Host "         Install $DisplayName manually, then re-run setup."
        Write-Host ""
        return $false
    }

    Write-Host ""
    $choice = Read-Host " $DisplayName not found. Install it automatically via winget? [Y/N]"
    if ($choice -notmatch '^[Yy]') {
        return $false
    }

    Write-Host " Installing $DisplayName..." -ForegroundColor Cyan
    winget install --id $Id --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host " [ERROR] winget install failed (exit $LASTEXITCODE)." -ForegroundColor Red
        return $false
    }

    Refresh-Path
    return $true
}


# ── Helper: test whether a command is a real Python (not the Windows Store stub) ──

function Test-RealPython {
    param([string]$Cmd)
    try {
        $out = & $Cmd --version 2>&1
        # The Windows App Execution Alias stub outputs "Python was not found; run without
        # arguments to install from the Microsoft Store..." instead of "Python 3.x.y"
        return ($out -match "^Python \d")
    } catch { return $false }
}


# ── Helper: find a real python.exe in common install locations ────────────────

function Find-Python {
    # Search %LOCALAPPDATA%\Programs\Python (winget / user install default)
    $found = Get-ChildItem "$env:LOCALAPPDATA\Programs\Python" -Filter "python.exe" -Recurse `
             -ErrorAction SilentlyContinue |
             Sort-Object FullName -Descending |
             Select-Object -First 1 -ExpandProperty FullName
    if ($found -and (Test-RealPython $found)) { return $found }

    # Search C:\Python3xx (system install)
    $found = Get-ChildItem "C:\" -Filter "python.exe" -Depth 2 `
             -ErrorAction SilentlyContinue |
             Where-Object { $_.FullName -match "Python3" } |
             Sort-Object FullName -Descending |
             Select-Object -First 1 -ExpandProperty FullName
    if ($found -and (Test-RealPython $found)) { return $found }
    return $null
}


# ── Step 1: Python ────────────────────────────────────────────────────────────

Write-Host "[1/3] Checking Python..." -ForegroundColor Yellow

$PythonCmd = $null

# Check PATH candidates — skip the Windows Store stub if present
foreach ($candidate in @("python", "py")) {
    if ((Get-Command $candidate -ErrorAction SilentlyContinue) -and (Test-RealPython $candidate)) {
        $PythonCmd = $candidate
        break
    }
}

if ($PythonCmd) {
    $ver = & $PythonCmd --version 2>&1
    Write-Host "      Found: $ver" -ForegroundColor Green
} else {
    $installed = Install-Via-Winget -Id "Python.Python.3.11" -DisplayName "Python 3.11"

    if ($installed) {
        Refresh-Path
        foreach ($candidate in @("python", "py")) {
            if ((Get-Command $candidate -ErrorAction SilentlyContinue) -and (Test-RealPython $candidate)) {
                $PythonCmd = $candidate
                break
            }
        }
        if (-not $PythonCmd) {
            # PATH not updated yet in this session — find the exe directly
            $exePath = Find-Python
            if ($exePath) {
                $PythonCmd = $exePath
                Write-Host "      Found at: $exePath" -ForegroundColor Green
            }
        }
    }

    if (-not $PythonCmd) {
        Write-Host ""
        Write-Host " [ERROR] Python could not be found after install." -ForegroundColor Red
        Write-Host "         Try closing this window, reopening it, and running setup_windows.bat again."
        Write-Host "         Or install Python 3.11 manually from https://www.python.org/downloads/"
        Write-Host "         Make sure to check 'Add Python to PATH' during install."
        Write-Host ""
        Read-Host "Press Enter to exit"
        exit 1
    }

    $ver = & $PythonCmd --version 2>&1
    Write-Host "      Python ready: $ver" -ForegroundColor Green
}
Write-Host ""


# ── Step 2: pip dependencies ──────────────────────────────────────────────────

Write-Host "[2/3] Installing Python dependencies..." -ForegroundColor Yellow
& $PythonCmd -m pip install --upgrade pip --quiet
& $PythonCmd -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host " [ERROR] pip install failed. Check your internet connection and try again." -ForegroundColor Red
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "      Dependencies installed." -ForegroundColor Green
Write-Host ""


# ── Step 3: Tesseract OCR ─────────────────────────────────────────────────────

Write-Host "[3/3] Checking Tesseract OCR..." -ForegroundColor Yellow

$TessExe = "C:\Program Files\Tesseract-OCR\tesseract.exe"

if (Test-Path $TessExe) {
    Write-Host "      Tesseract already installed." -ForegroundColor Green
} else {
    $installed = Install-Via-Winget -Id "UB-Mannheim.TesseractOCR" -DisplayName "Tesseract OCR"
    if (-not $installed -or -not (Test-Path $TessExe)) {
        Write-Host ""
        Write-Host " [WARNING] Tesseract not installed. OCR will not work until it is." -ForegroundColor Yellow
        Write-Host "           Install manually from: https://github.com/UB-Mannheim/tesseract/wiki"
        Write-Host "           Then re-run this script to update config, or set the path in Settings."
        Write-Host ""
    } else {
        Write-Host "      Tesseract installed." -ForegroundColor Green
    }
}

# Write tesseract path to config.json (only tesseract_path; all other paths use dev defaults)
$EscTess = $TessExe -replace '\\', '\\'
$ConfigPath = Join-Path $RepoRoot "config.json"
Set-Content -Path $ConfigPath -Value "{`"tesseract_path`": `"$EscTess`"}" -Encoding UTF8
Write-Host "      Config written: config.json" -ForegroundColor Green
Write-Host ""


# ── Done ──────────────────────────────────────────────────────────────────────

Write-Host " Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host " To run the app:"
Write-Host "   Double-click  run_in_windows.bat"
Write-Host "   Or from a terminal:  python app.py"
Write-Host ""
