"""
Background QThread worker for OCR extraction — keeps the UI responsive.
"""
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from core.extractor import extract_with_template, ocr_full_page


class OcrWorker(QThread):
    """
    Runs OCR on a list of files in a background thread.
    Emits progress updates and the final combined result.
    """
    progress    = pyqtSignal(int, int, str)   # current, total, filename
    file_done   = pyqtSignal(str, list)        # filename, rows
    finished_ok = pyqtSignal(list)             # all_rows combined
    error       = pyqtSignal(str, str)         # filename, error message

    def __init__(self, file_paths: list[str], template: dict, parent=None):
        super().__init__(parent)
        self._file_paths = file_paths
        self._template   = template
        self._cancelled  = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        all_rows = []
        total = len(self._file_paths)

        for i, path in enumerate(self._file_paths):
            if self._cancelled:
                break

            fname = Path(path).name
            self.progress.emit(i + 1, total, fname)

            try:
                file_bytes = Path(path).read_bytes()
                rows = extract_with_template(file_bytes, fname, self._template)
                for r in rows:
                    r["_source_file"] = fname
                all_rows.extend(rows)
                self.file_done.emit(fname, rows)
            except Exception as exc:
                self.error.emit(fname, str(exc))

        if not self._cancelled:
            self.finished_ok.emit(all_rows)


class FullPageOcrWorker(QThread):
    """Run full-page OCR on a single file and return raw text."""
    result = pyqtSignal(str, str)   # filename, raw_text
    error  = pyqtSignal(str, str)

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self._path = file_path

    def run(self):
        fname = Path(self._path).name
        try:
            data = Path(self._path).read_bytes()
            text = ocr_full_page(data, fname)
            self.result.emit(fname, text)
        except Exception as exc:
            self.error.emit(fname, str(exc))
