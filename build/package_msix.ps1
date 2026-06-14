# OCR Master - MSIX Packager
# Assembles dist\OCRMaster\ into an MSIX package for Microsoft Store submission.
#
# Prerequisites:
#   1. Run build_windows.ps1 first to produce dist\OCRMaster\
#   2. Install Windows SDK (includes makeappx.exe):
#      winget install Microsoft.WindowsSDK.10.0.22621
#
# Output: build\Output\OCRMaster.msix
#
# IMPORTANT: Update Publisher CN in build\msix\AppxManifest.xml before submitting.
# Get your Publisher value from: Partner Center -> App identity -> Publisher

$RepoRoot = Split-Path $PSScriptRoot
Set-Location $RepoRoot

Write-Host ""
Write-Host " === OCR Master MSIX Packager ===" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Check PyInstaller output exists ───────────────────────────────────
if (-not (Test-Path "dist\OCRMaster\OCRMaster.exe")) {
    Write-Host "[ERROR] dist\OCRMaster\OCRMaster.exe not found." -ForegroundColor Red
    Write-Host "        Run build_windows.ps1 first to produce the executable."
    Read-Host "Press Enter to exit"
    exit 1
}

# ── Step 2: Find makeappx.exe ─────────────────────────────────────────────────
Write-Host "[1/5] Looking for makeappx.exe (Windows SDK)..." -ForegroundColor Yellow

$makeappx = $null
$sdkBin = "C:\Program Files (x86)\Windows Kits\10\bin"
if (Test-Path $sdkBin) {
    $makeappx = Get-ChildItem $sdkBin -Recurse -Filter "makeappx.exe" -ErrorAction SilentlyContinue |
                Where-Object { $_.FullName -like "*x64*" } |
                Sort-Object FullName -Descending |
                Select-Object -First 1 -ExpandProperty FullName
}

if (-not $makeappx) {
    Write-Host "[ERROR] makeappx.exe not found." -ForegroundColor Red
    Write-Host ""
    Write-Host " Install the Windows SDK with:"
    Write-Host "   winget install Microsoft.WindowsSDK.10.0.22621"
    Write-Host ""
    Write-Host " Then re-run this script."
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "        Found: $makeappx" -ForegroundColor Green

# ── Step 3: Generate placeholder assets if missing ───────────────────────────
Write-Host "[2/5] Checking assets..." -ForegroundColor Yellow

$assetsDir = "build\msix\Assets"
Add-Type -AssemblyName System.Drawing

function New-PlaceholderPng {
    param([string]$Path, [int]$W, [int]$H, [string]$Label)
    if (Test-Path $Path) { return }
    $bmp  = New-Object System.Drawing.Bitmap($W, $H)
    $gfx  = [System.Drawing.Graphics]::FromImage($bmp)
    $gfx.Clear([System.Drawing.Color]::FromArgb(30, 58, 95))   # #1e3a5f
    $font = New-Object System.Drawing.Font("Segoe UI", [Math]::Max(7, $W / 10), [System.Drawing.FontStyle]::Bold)
    $brush = [System.Drawing.Brushes]::White
    $sf   = New-Object System.Drawing.StringFormat
    $sf.Alignment = [System.Drawing.StringAlignment]::Center
    $sf.LineAlignment = [System.Drawing.StringAlignment]::Center
    $gfx.DrawString($Label, $font, $brush, [System.Drawing.RectangleF]::new(0, 0, $W, $H), $sf)
    $bmp.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    $gfx.Dispose(); $bmp.Dispose()
    Write-Host "        Generated placeholder: $(Split-Path $Path -Leaf)"
}

New-PlaceholderPng "$assetsDir\StoreLogo.png"          50  50  "OCR"
New-PlaceholderPng "$assetsDir\Square44x44Logo.png"    44  44  "OCR"
New-PlaceholderPng "$assetsDir\Square150x150Logo.png" 150 150  "OCR Master"
New-PlaceholderPng "$assetsDir\Wide310x150Logo.png"   310 150  "OCR Master"
New-PlaceholderPng "$assetsDir\SplashScreen.png"      620 300  "OCR Master"

Write-Host "        Assets ready. Replace placeholders in build\msix\Assets\ with real branding before Store submission." -ForegroundColor Yellow

# ── Step 4: Assemble package root ─────────────────────────────────────────────
Write-Host "[3/5] Assembling package root..." -ForegroundColor Yellow

$pkgRoot = "build\MSIXPackage"
if (Test-Path $pkgRoot) { Remove-Item $pkgRoot -Recurse -Force }
New-Item -ItemType Directory -Force -Path "$pkgRoot\OCRMaster" | Out-Null
New-Item -ItemType Directory -Force -Path "$pkgRoot\Assets"    | Out-Null

# Copy app files
Copy-Item "dist\OCRMaster\*" "$pkgRoot\OCRMaster\" -Recurse -Force
Write-Host "        Copied dist\OCRMaster -> $pkgRoot\OCRMaster\"

# Copy manifest and assets
Copy-Item "build\msix\AppxManifest.xml" "$pkgRoot\AppxManifest.xml" -Force
Copy-Item "build\msix\Assets\*"         "$pkgRoot\Assets\"          -Force
Write-Host "        Copied manifest and assets"

# ── Step 5: Run makeappx ──────────────────────────────────────────────────────
Write-Host "[4/5] Running makeappx..." -ForegroundColor Yellow

New-Item -ItemType Directory -Force -Path "build\Output" | Out-Null
$msixOut = "build\Output\OCRMaster.msix"
if (Test-Path $msixOut) { Remove-Item $msixOut -Force }

& $makeappx pack /d $pkgRoot /p $msixOut /nv
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] makeappx failed." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# ── Done ──────────────────────────────────────────────────────────────────────
$sizeMB = [Math]::Round((Get-Item $msixOut).Length / 1MB, 1)
Write-Host ""
Write-Host "[5/5] Done!" -ForegroundColor Green
Write-Host ""
Write-Host " MSIX: $msixOut  ($sizeMB MB)" -ForegroundColor Green
Write-Host ""
Write-Host " Next steps:"
Write-Host "   1. Update Publisher CN in build\msix\AppxManifest.xml"
Write-Host "      (get it from Partner Center -> App identity -> Publisher)"
Write-Host "   2. Replace placeholder images in build\msix\Assets\"
Write-Host "   3. Re-run this script to regenerate the MSIX"
Write-Host "   4. Upload build\Output\OCRMaster.msix to Partner Center"
Write-Host ""

Read-Host "Press Enter to exit"
