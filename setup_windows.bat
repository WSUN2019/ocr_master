@echo off
:: OCR Master — Dev environment setup
:: Double-click this file to install everything needed to run from source.
:: Requires Windows 10/11 with winget available (pre-installed on Win 11,
:: available via Microsoft Store on Win 10).

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_windows.ps1"
pause
