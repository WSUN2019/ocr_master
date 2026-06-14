@echo off
:: Launcher for build_windows.ps1
:: Double-click this file to build OCR Master on Windows.
:: It calls the PowerShell script with ExecutionPolicy Bypass so no manual
:: right-click "Run with PowerShell" or policy changes are needed.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows.ps1"
pause
