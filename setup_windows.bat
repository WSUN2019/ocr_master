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
echo [1/2] Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed. Check your internet connection and try again.
    echo.
    pause
    exit /b 1
)

echo.
echo [2/2] Done! Setup complete.
echo.
echo  You can now run the app anytime by double-clicking run_in_windows.bat
echo.
pause
