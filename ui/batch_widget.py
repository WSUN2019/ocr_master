"""
Batch Processing page — point at a folder, process all files under one batch_name,
move each to a complete folder, save all rows to the database.
"""
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QLineEdit, QFileDialog, QGroupBox, QListWidget,
    QListWidgetItem, QProgressBar, QTextEdit, QAbstractItemView,
    QMessageBox, QSplitter, QFrame
)

from core.extractor import tesseract_available
from core.template import list_templates, load_template
from core.storage import init_db
from ui.batch_worker import BatchWorker

from core.config import get_config

_EXTS = {".jpg", ".jpeg", ".png", ".pdf"}


def _default_batch_name() -> str:
    return datetime.now().strftime("batch_%Y%m%d_%H%M%S")


class BatchWidget(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        init_db()
        self._worker: BatchWorker | None = None
        self._files: list[Path] = []
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # Title
        title = QLabel("Batch Processing")
        title.setObjectName("section_title")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        root.addWidget(title)

        sub = QLabel(
            "Process an entire folder of statements in one run. All files share one "
            "batch name; each file is moved to the complete folder after saving."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #64748b; font-size: 12px; padding-bottom: 4px;")
        root.addWidget(sub)

        # ── Config ────────────────────────────────────────────────────────────
        cfg = QGroupBox("Batch Setup")
        cfg_lay = QVBoxLayout(cfg)
        cfg_lay.setSpacing(8)

        # Row 1: batch name + template
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Batch name:"))
        self._batch_name_edit = QLineEdit(_default_batch_name())
        self._batch_name_edit.setMinimumWidth(240)
        self._batch_name_edit.setToolTip(
            "All files in this run share this name. Use it to find/delete the batch in History."
        )
        row1.addWidget(self._batch_name_edit)

        row1.addSpacing(20)
        row1.addWidget(QLabel("Template:"))
        self._tpl_combo = QComboBox()
        self._tpl_combo.setMinimumWidth(220)
        row1.addWidget(self._tpl_combo)
        row1.addStretch()
        cfg_lay.addLayout(row1)

        # Row 2: import folder
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Import folder:"))
        self._import_edit = QLineEdit(str(get_config().batch_import_dir))
        self._import_edit.setReadOnly(True)
        row2.addWidget(self._import_edit)
        btn_browse_import = QPushButton("Browse…")
        btn_browse_import.clicked.connect(self._browse_import)
        row2.addWidget(btn_browse_import)
        btn_scan = QPushButton("Scan")
        btn_scan.setObjectName("btn_primary")
        btn_scan.setToolTip("Find all eligible files in the import folder")
        btn_scan.clicked.connect(self._scan_folder)
        row2.addWidget(btn_scan)
        cfg_lay.addLayout(row2)

        # Row 3: complete folder
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Complete folder:"))
        self._complete_edit = QLineEdit(str(get_config().batch_complete_dir))
        self._complete_edit.setReadOnly(True)
        row3.addWidget(self._complete_edit)
        btn_browse_complete = QPushButton("Browse…")
        btn_browse_complete.clicked.connect(self._browse_complete)
        row3.addWidget(btn_browse_complete)
        cfg_lay.addLayout(row3)

        root.addWidget(cfg)

        # ── Run controls ──────────────────────────────────────────────────────
        run_row = QHBoxLayout()
        self._lbl_found = QLabel("No files scanned yet")
        self._lbl_found.setStyleSheet("color: #2563eb;")
        run_row.addWidget(self._lbl_found)
        run_row.addStretch()

        self._btn_start = QPushButton("Start Batch")
        self._btn_start.setObjectName("btn_primary")
        self._btn_start.setMinimumWidth(110)
        self._btn_start.setEnabled(False)
        self._btn_start.clicked.connect(self._start_batch)
        run_row.addWidget(self._btn_start)

        self._btn_cancel = QPushButton("Cancel")
        self._btn_cancel.setEnabled(False)
        self._btn_cancel.clicked.connect(self._cancel_batch)
        run_row.addWidget(self._btn_cancel)

        root.addLayout(run_row)

        # ── Progress ──────────────────────────────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setFormat("%v / %m files — %p%")
        root.addWidget(self._progress)

        # ── Splitter: file list | log ─────────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QGroupBox("Files to Process")
        left.setMaximumWidth(280)
        left_lay = QVBoxLayout(left)
        self._file_list = QListWidget()
        self._file_list.setAlternatingRowColors(True)
        self._file_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        left_lay.addWidget(self._file_list)
        splitter.addWidget(left)

        right = QGroupBox("Run Log")
        right_lay = QVBoxLayout(right)
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFont(QFont("Courier New", 10))
        self._log.setStyleSheet(
            "background: #f8fafc; color: #1e293b; border: 1px solid #e2e8f0;"
        )
        right_lay.addWidget(self._log)
        splitter.addWidget(right)

        splitter.setSizes([260, 820])
        root.addWidget(splitter)

        self._refresh_templates()

    # ── Template refresh ──────────────────────────────────────────────────────

    def _refresh_templates(self):
        self._tpl_combo.clear()
        for t in list_templates():
            self._tpl_combo.addItem(t["name"], t["slug"])
        if self._tpl_combo.count() == 0:
            self._tpl_combo.addItem("No templates — build one first", None)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_templates()

    # ── Folder browsing ───────────────────────────────────────────────────────

    def _browse_import(self):
        path = QFileDialog.getExistingDirectory(
            self, "Select Import Folder", self._import_edit.text()
        )
        if path:
            self._import_edit.setText(path)
            self._scan_folder()

    def _browse_complete(self):
        path = QFileDialog.getExistingDirectory(
            self, "Select Complete Folder", self._complete_edit.text()
        )
        if path:
            self._complete_edit.setText(path)

    # ── Scan ──────────────────────────────────────────────────────────────────

    def _scan_folder(self):
        folder = Path(self._import_edit.text())
        folder.mkdir(parents=True, exist_ok=True)

        self._files = sorted(
            f for f in folder.iterdir()
            if f.is_file() and f.suffix.lower() in _EXTS
        )

        self._file_list.clear()
        for f in self._files:
            item = QListWidgetItem(f"  {f.name}")
            item.setToolTip(str(f))
            self._file_list.addItem(item)

        n = len(self._files)
        self._lbl_found.setText(f"{n} file(s) found" if n else "No eligible files found")
        self._btn_start.setEnabled(n > 0)

        if n:
            self._log_write(
                f"Scanned {folder}\n"
                f"Found {n} file(s): " + ", ".join(f.name for f in self._files)
            )

    # ── Batch run ─────────────────────────────────────────────────────────────

    def _start_batch(self):
        ok, info = tesseract_available()
        if not ok:
            QMessageBox.critical(
                self, "Tesseract Not Found",
                f"Tesseract OCR engine is not installed or not on PATH.\n\n"
                f"Error: {info}\n\n"
                f"Linux:   sudo apt-get install -y tesseract-ocr\n"
                f"Windows: https://github.com/UB-Mannheim/tesseract/wiki"
            )
            return

        slug = self._tpl_combo.currentData()
        if not slug:
            QMessageBox.warning(self, "No Template",
                                "Create a template in Template Builder first.")
            return

        if not self._files:
            QMessageBox.warning(self, "No Files",
                                "Scan a folder first to find files to process.")
            return

        batch_name = self._batch_name_edit.text().strip()
        if not batch_name:
            batch_name = _default_batch_name()
            self._batch_name_edit.setText(batch_name)

        template     = load_template(slug)
        complete_dir = Path(self._complete_edit.text())

        self._log.clear()
        self._log_write(
            f"Starting batch: {batch_name}\n"
            f"Template: {template.get('name', slug)}\n"
            f"Files: {len(self._files)}\n"
            f"Complete folder: {complete_dir}\n"
            + "─" * 60
        )

        self._progress.setMaximum(len(self._files))
        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._btn_start.setEnabled(False)
        self._btn_cancel.setEnabled(True)

        self._worker = BatchWorker(self._files, template, batch_name, complete_dir, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.file_done.connect(self._on_file_done)
        self._worker.file_error.connect(self._on_file_error)
        self._worker.log_line.connect(self._log_write)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.start()

    def _cancel_batch(self):
        if self._worker:
            self._worker.cancel()
        self._btn_cancel.setEnabled(False)

    # ── Worker signals ────────────────────────────────────────────────────────

    def _on_progress(self, current: int, total: int, fname: str):
        self._progress.setValue(current)
        self.status_message.emit(f"Batch: {fname} ({current}/{total})")
        # Mark current file in list
        for i in range(self._file_list.count()):
            item = self._file_list.item(i)
            name = item.toolTip().split("/")[-1]
            if name == fname:
                item.setForeground(QColor("#60a5fa"))

    def _on_file_done(self, fname: str, rows: int):
        for i in range(self._file_list.count()):
            item = self._file_list.item(i)
            if item.toolTip().split("/")[-1] == fname:
                item.setText(f"  ✓ {fname}  ({rows} rows)")
                item.setForeground(QColor("#10b981"))

    def _on_file_error(self, fname: str, msg: str):
        for i in range(self._file_list.count()):
            item = self._file_list.item(i)
            if item.toolTip().split("/")[-1] == fname:
                item.setText(f"  ✗ {fname}")
                item.setForeground(QColor("#ef4444"))

    def _on_finished(self, files_done: int, total_rows: int):
        self._progress.setVisible(False)
        self._btn_start.setEnabled(bool(self._files))
        self._btn_cancel.setEnabled(False)

        self._log_write(
            "─" * 60 + "\n"
            f"Batch complete — {files_done} file(s) processed, "
            f"{total_rows} row(s) saved to database."
        )
        self.status_message.emit(
            f"Batch done — {files_done} files, {total_rows} rows"
        )

        # Reset batch name for next run so it's a fresh timestamp
        self._batch_name_edit.setText(_default_batch_name())
        # Re-scan so the list reflects moved files
        self._scan_folder()

    # ── Log helper ────────────────────────────────────────────────────────────

    def _log_write(self, text: str):
        self._log.append(text)
        self._log.verticalScrollBar().setValue(
            self._log.verticalScrollBar().maximum()
        )
