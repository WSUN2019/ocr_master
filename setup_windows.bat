@echo off
cd /d "%~dp0"

echo.
echo  === OCR Master Setup ===
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.11+ from python.org
    echo         Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

:: Install dependencies
echo [1/3] Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed. Check your internet connection and try again.
    echo.
    pause
    exit /b 1
)

:: Install Tesseract OCR
echo.
echo [2/3] Checking Tesseract OCR...
set TESS_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
if exist "%TESS_PATH%" (
    echo       Tesseract already installed, skipping.
) else (
    echo       Installing Tesseract via winget...
    winget install --id UB-Mannheim.TesseractOCR --silent --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo [ERROR] Tesseract install failed.
        echo         Install manually from: https://github.com/UB-Mannheim/tesseract/wiki
        echo.
        pause
        exit /b 1
    )
    echo       Tesseract installed.
)

:: Write tesseract path to app config
echo       Configuring app settings...
echo {"tesseract_path": "%TESS_PATH:\=\\%"} > config.json
echo       Tesseract path saved to config.json

echo.
echo [3/3] Done! Setup complete.
echo.
echo  You can now run the app anytime by double-clicking run_in_windows.bat
echo.
pause
