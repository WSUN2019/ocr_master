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

:: Create app data folders (excluded from git)
echo [2/2] Creating app data folders...
if not exist "templates\"     mkdir templates
if not exist "input_files\"   mkdir input_files
if not exist "output\"        mkdir output
if not exist "batch_import\"  mkdir batch_import
if not exist "batch_complete\" mkdir batch_complete

echo.
echo [3/3] Done! Setup complete.
echo.
echo  Folders created: templates, input_files, output, batch_import, batch_complete
echo  You can now run the app anytime by double-clicking run_in_windows.bat
echo.
pause
