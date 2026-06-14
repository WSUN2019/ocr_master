@echo off
:: Creates a clean source-code zip for sharing with another developer.
:: Uses "git archive" so only tracked files are included — no build output,
:: no user data (db, config, statements), no __pycache__.
::
:: The other dev just needs to:
::   1. Unzip anywhere
::   2. Double-click setup_windows.bat
::   3. Double-click run_in_windows.bat

cd /d "%~dp0"

:: Build a date string YYYYMMDD (works on any Windows locale)
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set DT=%%I
set DATESTR=%DT:~0,8%

set ZIPNAME=ocr_master_dev_%DATESTR%.zip

echo.
echo Creating %ZIPNAME% ...
git archive --format=zip --output="%ZIPNAME%" HEAD

if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: git archive failed. Make sure you are inside a git repository.
    pause
    exit /b 1
)

echo.
echo Done: %ZIPNAME%
echo.
echo Send this file to the other developer. They should:
echo   1. Unzip it anywhere
echo   2. Double-click setup_windows.bat
echo   3. Double-click run_in_windows.bat
echo.
pause
