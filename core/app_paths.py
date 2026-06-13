"""
Resolve app data directory for both development and frozen (PyInstaller) builds.

Dev:    APP_DIR = repo root  (Path(__file__).parent.parent)
Frozen: APP_DIR = folder containing OCRMaster.exe  (Path(sys.executable).parent)

User data (templates, database, input/output folders) always lives in APP_DIR
so it persists across app updates and is never inside the temp extraction dir.
"""
import sys
from pathlib import Path


def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


APP_DIR = get_app_dir()
