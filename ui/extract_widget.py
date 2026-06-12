"""
Extract page — pick files, choose template, run OCR, review table, save/export.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QTableView, QProgressBar, QFileDialog,
    QGroupBox, QAbstractItemView, QHeaderView, QTextEdit,
    QMessageBox, QSplitter, QListWidget, QListWidgetItem
)

from core.storage import insert_transactions, df_to_csv_bytes, init_db
from core.template import list_templates, load_template
from core.extractor import tesseract_available
from ui.ocr_worker import OcrWorker

APP_DIR    = Path(__file__).parent.parent
INPUT_DIR  = APP_DIR / "input_files"
OUTPUT_DIR = APP_DIR / "output"


# ── Pandas table model ────────────────────────────────────────────────────────

class PandasModel(QAbstractTableModel):
    def __init__(self, df: pd.DataFrame):
        super().__init__()
        self._df = df.copy()

    def rowCount(self, parent=QModelIndex()): return len(self._df)
    def columnCount(self, parent=QModelIndex()): return len(self._df.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        val = self._df.iloc[index.row(), index.column()]
        if role == Qt.ItemDataRole.DisplayRole:
            return "" if pd.isna(val) else str(val)
        if role == Qt.ItemDataRole.BackgroundRole and index.row() % 2:
            return QColor(26, 37, 64)
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return str(self._df.columns[section])
        return str(section + 1)

    def get_df(self): return self._df


# ── Extract widget ────────────────────────────────────────────────────────────

class ExtractWidget(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        init_db()
        self._worker: OcrWorker | None = None
        self._all_rows: list[dict] = []
        self._df: pd.DataFrame | None = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # Title
        title = QLabel("Extract Transactions")
        title.setObjectName("section_title")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        root.addWidget(title)

        # ── Top controls ──────────────────────────────────────────────────────
        ctrl_group = QGroupBox("Setup")
        ctrl_layout = QHBoxLayout(ctrl_group)

        # Template picker
        ctrl_layout.addWidget(QLabel("Template:"))
        self._tpl_combo = QComboBox()
        self._tpl_combo.setMinimumWidth(220)
        ctrl_layout.addWidget(self._tpl_combo)

        ctrl_layout.addSpacing(20)

        # File list controls
        btn_add = QPushButton("Add Files")
        btn_add.clicked.connect(self._add_files)
        ctrl_layout.addWidget(btn_add)

        btn_clear_files = QPushButton("Clear Files")
        btn_clear_files.clicked.connect(self._clear_files)
        ctrl_layout.addWidget(btn_clear_files)

        ctrl_layout.addStretch()

        self._btn_run = QPushButton("Run OCR")
        self._btn_run.setObjectName("btn_primary")
        self._btn_run.setMinimumWidth(100)
        self._btn_run.clicked.connect(self._run_ocr)
        ctrl_layout.addWidget(self._btn_run)

        self._btn_cancel = QPushButton("Cancel")
        self._btn_cancel.setEnabled(False)
        self._btn_cancel.clicked.connect(self._cancel_ocr)
        ctrl_layout.addWidget(self._btn_cancel)

        root.addWidget(ctrl_group)

        # ── Progress ──────────────────────────────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setFormat("%v / %m files — %p%")
        root.addWidget(self._progress)

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color: #a0c4ff;")
        root.addWidget(self._status_lbl)

        # ── Splitter: file list | table ───────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # File list
        left = QGroupBox("Files to process")
        left.setMaximumWidth(260)
        left_layout = QVBoxLayout(left)
        self._file_list = QListWidget()
        self._file_list.setAlternatingRowColors(True)
        left_layout.addWidget(self._file_list)
        splitter.addWidget(left)

        # Table
        right = QGroupBox("Extracted Data")
        right_layout = QVBoxLayout(right)

        self._table = QTableView()
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSortingEnabled(True)
        right_layout.addWidget(self._table)

        # Action buttons under table
        btn_row = QHBoxLayout()
        self._lbl_count = QLabel("No data")
        self._lbl_count.setStyleSheet("color: #a0c4ff;")
        btn_row.addWidget(self._lbl_count)
        btn_row.addStretch()

        btn_export = QPushButton("Export CSV")
        btn_export.clicked.connect(self._export_csv)
        btn_row.addWidget(btn_export)

        btn_save_db = QPushButton("Save to Database")
        btn_save_db.setObjectName("btn_primary")
        btn_save_db.clicked.connect(self._save_to_db)
        btn_row.addWidget(btn_save_db)

        right_layout.addLayout(btn_row)
        splitter.addWidget(right)
        splitter.setSizes([240, 800])

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

    # ── File management ───────────────────────────────────────────────────────

    def _add_files(self):
        INPUT_DIR.mkdir(exist_ok=True)
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Statement Files",
            str(INPUT_DIR),
            "Images & PDFs (*.jpg *.jpeg *.png *.pdf)"
        )
        for p in paths:
            existing = [self._file_list.item(i).data(Qt.ItemDataRole.UserRole)
                        for i in range(self._file_list.count())]
            if p not in existing:
                item = QListWidgetItem(Path(p).name)
                item.setData(Qt.ItemDataRole.UserRole, p)
                self._file_list.addItem(item)

    def _clear_files(self):
        self._file_list.clear()

    def _file_paths(self) -> list[str]:
        return [self._file_list.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(self._file_list.count())]

    # ── OCR ───────────────────────────────────────────────────────────────────

    def _run_ocr(self):
        # Check Tesseract first
        ok, info = tesseract_available()
        if not ok:
            QMessageBox.critical(self, "Tesseract Not Found",
                f"Tesseract OCR engine is not installed or not on PATH.\n\n"
                f"Error: {info}\n\n"
                f"Linux:   sudo apt-get install -y tesseract-ocr\n"
                f"Windows: https://github.com/UB-Mannheim/tesseract/wiki\n\n"
                f"After installing, restart the app.")
            return

        slug = self._tpl_combo.currentData()
        if not slug:
            QMessageBox.warning(self, "No Template", "Create a template in Template Builder first.")
            return
        paths = self._file_paths()
        if not paths:
            QMessageBox.warning(self, "No Files", "Add files to process first.")
            return

        template = load_template(slug)
        self._all_rows = []
        self._progress.setMaximum(len(paths))
        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._btn_run.setEnabled(False)
        self._btn_cancel.setEnabled(True)

        self._worker = OcrWorker(paths, template, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.file_done.connect(self._on_file_done)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _cancel_ocr(self):
        if self._worker:
            self._worker.cancel()
        self._btn_cancel.setEnabled(False)
        self._status_lbl.setText("Cancelling…")

    def _on_progress(self, current: int, total: int, fname: str):
        self._progress.setValue(current)
        self._status_lbl.setText(f"Processing ({current}/{total}): {fname}")
        self.status_message.emit(f"OCR: {fname}")

    def _on_file_done(self, fname: str, rows: list):
        self._all_rows.extend(rows)

    def _on_error(self, fname: str, msg: str):
        self._status_lbl.setText(f"Error on {fname}: {msg}")
        QMessageBox.critical(self, f"OCR Error — {fname}", msg)

    def _on_finished(self, all_rows: list):
        self._progress.setVisible(False)
        self._btn_run.setEnabled(True)
        self._btn_cancel.setEnabled(False)

        if not all_rows:
            self._status_lbl.setText("No rows extracted. Check template alignment.")
            return

        self._df = pd.DataFrame(all_rows)
        # Put internal cols at end
        front = [c for c in self._df.columns if not c.startswith("_")]
        back  = [c for c in self._df.columns if c.startswith("_")]
        self._df = self._df[front + back]

        model = PandasModel(self._df)
        self._table.setModel(model)
        self._lbl_count.setText(f"{len(self._df)} rows extracted")
        self._status_lbl.setText(f"Done — {len(self._df)} rows from {len(set(r.get('_source_file','') for r in all_rows))} file(s)")
        self.status_message.emit(f"Extracted {len(self._df)} rows")

    # ── Export / save ─────────────────────────────────────────────────────────

    def _export_csv(self):
        if self._df is None or self._df.empty:
            QMessageBox.information(self, "Export", "No data to export yet.")
            return
        OUTPUT_DIR.mkdir(exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", str(OUTPUT_DIR / "transactions.csv"), "CSV (*.csv)"
        )
        if path:
            self._df.to_csv(path, index=False)
            self.status_message.emit(f"Exported CSV: {Path(path).name}")
            QMessageBox.information(self, "Exported", f"Saved {len(self._df)} rows to:\n{path}")

    def _save_to_db(self):
        if self._df is None or self._df.empty:
            QMessageBox.information(self, "Save", "No data to save yet.")
            return
        from datetime import datetime
        tpl_name = self._tpl_combo.currentText()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        total = 0
        if "_source_file" in self._df.columns:
            for src in self._df["_source_file"].dropna().unique():
                batch_name = f"{Path(src).stem}__{timestamp}{Path(src).suffix}"
                mask = self._df["_source_file"] == src
                rows = self._df[mask].to_dict("records")
                total += insert_transactions(
                    rows, source_file=src, batch_name=batch_name, template_name=tpl_name
                )
        else:
            batch_name = f"batch__{timestamp}"
            rows = self._df.to_dict("records")
            total += insert_transactions(
                rows, source_file="unknown", batch_name=batch_name, template_name=tpl_name
            )
        self.status_message.emit(f"Saved {total} rows to database")
        QMessageBox.information(self, "Saved", f"Saved {total} rows to database.")
