"""
Resolve app data directory for both development and frozen (PyInstaller) builds.

Dev:    APP_DIR = repo root  (Path(__file__).parent.parent)
Frozen: APP_DIR = Documents\OCR Master  — all user data in one visible location.
        Falls back to home directory if Documents doesn't exist (rare).
"""
import sys
from pathlib import Path


def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        docs = Path.home() / "Documents"
        base = docs if docs.exists() else Path.home()
        data_dir = base / "OCR Master"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    return Path(__file__).parent.parent


APP_DIR = get_app_dir()
