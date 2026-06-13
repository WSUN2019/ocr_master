@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM  OCR Master — Windows build script
REM  Run from the repo root:  build\build_windows.bat
REM ─────────────────────────────────────────────────────────────────────────────

echo.
echo  === OCR Master Windows Build ===
echo.

REM Step 1: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.11+ from python.org
    pause & exit /b 1
)

REM Step 2: Install / upgrade dependencies
echo [1/3] Installing Python dependencies...
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet
if errorlevel 1 (
    echo [ERROR] pip install failed.
    pause & exit /b 1
)

REM Step 3: Run PyInstaller
echo [2/3] Building executable with PyInstaller...
pyinstaller build\OCRMaster.spec --noconfirm
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    pause & exit /b 1
)

echo.
echo [3/3] Done!
echo.
echo  Output: dist\OCRMaster\OCRMaster.exe
echo.
echo  Next steps:
echo    - Test:    double-click dist\OCRMaster\OCRMaster.exe
echo    - Install: open build\installer.iss in Inno Setup Compiler and press F9
echo               Output will be: build\Output\OCRMasterSetup.exe
echo.
pause
