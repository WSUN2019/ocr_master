"""
Background worker for folder-based batch OCR processing.
Each file is extracted, inserted into the DB, then moved to the complete folder.
All files in one run share the same batch_name.
"""
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from core.extractor import extract_with_template
from core.storage import insert_transactions, is_already_imported


class BatchWorker(QThread):
    progress   = pyqtSignal(int, int, str)   # current, total, filename
    file_done  = pyqtSignal(str, int)         # filename, rows_inserted
    file_error = pyqtSignal(str, str)         # filename, error_message
    log_line   = pyqtSignal(str)              # one log entry
    finished_ok = pyqtSignal(int, int)        # files_processed, total_rows

    def __init__(self, files: list[Path], template: dict,
                 batch_name: str, complete_dir: Path, parent=None):
        super().__init__(parent)
        self._files       = list(files)
        self._template    = template
        self._batch_name  = batch_name
        self._complete_dir = complete_dir
        self._cancelled   = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        total      = len(self._files)
        total_rows = 0
        done_files = 0

        self._complete_dir.mkdir(parents=True, exist_ok=True)

        for i, fpath in enumerate(self._files, 1):
            if self._cancelled:
                self.log_line.emit("⚠  Batch cancelled.")
                break

            self.progress.emit(i, total, fpath.name)

            if is_already_imported(fpath.name):
                self.log_line.emit(f"⤭  {fpath.name} — already imported, skipping")
                done_files += 1
                continue

            self.log_line.emit(f"Processing  {fpath.name} …")

            try:
                file_bytes = fpath.read_bytes()
                rows = extract_with_template(file_bytes, fpath.name, self._template)

                n = insert_transactions(
                    rows,
                    source_file=fpath.name,
                    batch_name=self._batch_name,
                    template_name=self._template.get("name", ""),
                )
                total_rows += n
                done_files += 1

                # Move to complete folder; avoid clobbering existing files.
                # Handled separately so a rename failure doesn't mask a successful insert.
                dest = self._complete_dir / fpath.name
                if dest.exists():
                    dest = self._complete_dir / f"{fpath.stem}_{i}{fpath.suffix}"
                try:
                    fpath.rename(dest)
                    self.log_line.emit(f"✓  {fpath.name} — {n} row(s) saved → moved to complete")
                except Exception as move_exc:
                    self.log_line.emit(
                        f"⚠  {fpath.name} — {n} row(s) saved, but file move failed: {move_exc}"
                    )

                self.file_done.emit(fpath.name, n)

            except Exception as exc:
                self.file_error.emit(fpath.name, str(exc))
                self.log_line.emit(f"✗  {fpath.name} — ERROR: {exc}")

        self.finished_ok.emit(done_files, total_rows)
