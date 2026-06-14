"""
Resolve app data directory for both development and frozen (PyInstaller) builds.

Dev:    APP_DIR = repo root  (Path(__file__).parent.parent)
Frozen: APP_DIR = %APPDATA%\OCR Master  — writing to Program Files requires
        elevation; user data belongs in AppData so it survives upgrades and
        is accessible without admin rights.
"""
import os
import sys
from pathlib import Path


def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        appdata = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA", "")
        if appdata:
            data_dir = Path(appdata) / "OCR Master"
            data_dir.mkdir(parents=True, exist_ok=True)
            return data_dir
        # Fallback if APPDATA is somehow unset
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


APP_DIR = get_app_dir()
