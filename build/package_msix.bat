@echo off
:: Launcher for package_msix.ps1
:: Double-click to assemble dist\OCRMaster\ into build\Output\OCRMaster.msix

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0package_msix.ps1"
pause
