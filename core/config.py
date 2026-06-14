"""
Central configuration manager. All user-configurable paths live here.
config.json is stored in APP_DIR (Documents\\OCR Master when installed, repo root in dev).

All consumers must call get_config().<property> at runtime — never cache the value
at import time, because the user can change paths in Settings without restarting.
"""
import json
from pathlib import Path

from core.app_paths import APP_DIR


class AppConfig:
    def __init__(self):
        self._path = APP_DIR / "config.json"
        self._data: dict = {}
        self.reload()

    # ── Defaults ──────────────────────────────────────────────────────────────

    def _defaults(self) -> dict:
        # APP_DIR = Documents\OCR Master (installed) or repo root (dev)
        # Everything lives under the same root in both modes.
        return {
            "tesseract_path":     r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            "db_path":            str(APP_DIR / "ocr_master.db"),
            "templates_dir":      str(APP_DIR / "templates"),
            "input_dir":          str(APP_DIR / "input_files"),
            "output_dir":         str(APP_DIR / "output"),
            "batch_import_dir":   str(APP_DIR / "batch_import"),
            "batch_complete_dir": str(APP_DIR / "batch_complete"),
        }

    # ── Load / save ───────────────────────────────────────────────────────────

    def reload(self):
        raw = {}
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            pass
        self._data = {**self._defaults(), **raw}

    def save(self):
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def set(self, key: str, value: str):
        self._data[key] = value
        self.save()

    def update_many(self, updates: dict):
        self._data.update(updates)
        self.save()

    def reset_to_defaults(self):
        self._data = self._defaults()
        self.save()

    def as_dict(self) -> dict:
        return dict(self._data)

    # ── Path properties ───────────────────────────────────────────────────────

    @property
    def tesseract_path(self) -> str:
        return self._data.get("tesseract_path", "")

    @property
    def db_path(self) -> Path:
        return Path(self._data["db_path"])

    @property
    def templates_dir(self) -> Path:
        return Path(self._data["templates_dir"])

    @property
    def input_dir(self) -> Path:
        return Path(self._data["input_dir"])

    @property
    def output_dir(self) -> Path:
        return Path(self._data["output_dir"])

    @property
    def batch_import_dir(self) -> Path:
        return Path(self._data["batch_import_dir"])

    @property
    def batch_complete_dir(self) -> Path:
        return Path(self._data["batch_complete_dir"])


# ── Singleton ─────────────────────────────────────────────────────────────────

_cfg: AppConfig | None = None


def get_config() -> AppConfig:
    global _cfg
    if _cfg is None:
        _cfg = AppConfig()
    return _cfg
