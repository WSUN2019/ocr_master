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
    QMessageBox, QSplitter, QListWidget, QListWidgetItem, QMenu
)
from PyQt6.QtGui import QAction

from core.storage import insert_transactions, df_to_csv_bytes, init_db
from core.template import list_templates, load_template
from core.extractor import tesseract_available
from ui.ocr_worker import OcrWorker
from ui.history_widget import _add_balance_check

APP_DIR    = Path(__file__).parent.parent
INPUT_DIR  = APP_DIR / "input_files"
OUTPUT_DIR = APP_DIR / "output"


# ── Pandas table model (editable) ────────────────────────────────────────────

_READONLY_EXTRACT  = frozenset({"balance_check"})   # computed cols — not editable
_BALANCE_TRIGGER   = ("balance", "debit", "credit", "amount")


class PandasModel(QAbstractTableModel):
    _NOTE_BG = QColor(59, 130, 246, 35)

    def __init__(self, df: pd.DataFrame):
        super().__init__()
        self._df = df.copy()
        # Ensure a note column exists for override tracking
        if "note" not in self._df.columns:
            self._df["note"] = None

    def rowCount(self, parent=QModelIndex()): return len(self._df)
    def columnCount(self, parent=QModelIndex()): return len(self._df.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        val = self._df.iloc[index.row(), index.column()]
        col = self._df.columns[index.column()]

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return "" if pd.isna(val) else str(val)

        if col == "balance_check":
            text = "" if pd.isna(val) else str(val)
            if role == Qt.ItemDataRole.ForegroundRole:
                if text.startswith("✓"): return QColor("#10b981")
                if text.startswith("✗"): return QColor("#ef4444")
            if role == Qt.ItemDataRole.BackgroundRole:
                if text.startswith("✓"): return QColor(16, 185, 129, 30)
                if text.startswith("✗"): return QColor(239, 68,  68,  30)
            return None

        if role == Qt.ItemDataRole.BackgroundRole:
            note = self._df["note"].iloc[index.row()]
            if pd.notna(note) and str(note).strip():
                return self._NOTE_BG
            if index.row() % 2:
                return QColor(248, 250, 252)  # slate-50 alternate row

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return str(self._df.columns[section])
        return str(section + 1)

    def flags(self, index):
        base = super().flags(index)
        col = self._df.columns[index.column()]
        if col in _READONLY_EXTRACT or col.startswith("_"):
            return base
        return base | Qt.ItemFlag.ItemIsEditable

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role != Qt.ItemDataRole.EditRole:
            return False
        col = self._df.columns[index.column()]
        if col in _READONLY_EXTRACT or col.startswith("_"):
            return False
        new_val = str(value).strip()
        row = index.row()
        df_idx = self._df.index[row]

        old_raw = self._df.at[df_idx, col]
        old_val = "" if pd.isna(old_raw) else str(old_raw).strip()
        if old_val == new_val:
            return False

        if self._df[col].dtype != object:
            self._df[col] = self._df[col].astype(object)
        self._df.at[df_idx, col] = new_val
        self.dataChanged.emit(index, index, [role])

        if col != "note":
            note = f"Manual override: [{col}] {old_val!r} → {new_val!r}"
            self._df.at[df_idx, "note"] = note
            if "note" in self._df.columns:
                note_col = list(self._df.columns).index("note")
                note_idx = self.index(row, note_col)
                self.dataChanged.emit(note_idx, note_idx, [Qt.ItemDataRole.DisplayRole])

        if any(k in col.lower() for k in _BALANCE_TRIGGER):
            self._recompute_balance_check()

        return True

    def _recompute_balance_check(self):
        base = self._df.drop(columns=["balance_check"], errors="ignore")
        new_df = _add_balance_check(base)
        if "balance_check" not in new_df.columns:
            return
        self._df["balance_check"] = new_df["balance_check"].values
        if "balance_check" in self._df.columns:
            c = list(self._df.columns).index("balance_check")
            self.dataChanged.emit(
                self.index(0, c),
                self.index(len(self._df) - 1, c),
                [Qt.ItemDataRole.DisplayRole,
                 Qt.ItemDataRole.ForegroundRole,
                 Qt.ItemDataRole.BackgroundRole],
            )

    def get_df(self): return self._df


# ── Extract widget ────────────────────────────────────────────────────────────

class ExtractWidget(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        init_db()
        self._worker: OcrWorker | None = None
        self._model: PandasModel | None = None
        self._all_rows: list[dict] = []
        self._df: pd.DataFrame | None = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # Title row
        title_row = QHBoxLayout()
        title = QLabel("Extract Transactions")
        title.setObjectName("section_title")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_row.addWidget(title)
        title_row.addStretch()
        btn_new = QPushButton("New Extract")
        btn_new.setToolTip("Clear files and results to start a fresh extraction")
        btn_new.clicked.connect(self._new_extract)
        title_row.addWidget(btn_new)
        root.addLayout(title_row)

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
        self._status_lbl.setStyleSheet("color: #2563eb;")
        root.addWidget(self._status_lbl)

        # ── Splitter: file list | table ───────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # File list
        left = QGroupBox("Files to process")
        left.setMaximumWidth(260)
        left_layout = QVBoxLayout(left)
        self._file_list = QListWidget()
        self._file_list.setAlternatingRowColors(True)
        self._file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._file_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._file_list.customContextMenuRequested.connect(self._file_list_context_menu)
        self._file_list.keyPressEvent = self._file_list_key_press
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
        self._lbl_count.setStyleSheet("color: #2563eb;")
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

    def _remove_selected_files(self):
        for item in self._file_list.selectedItems():
            self._file_list.takeItem(self._file_list.row(item))

    def _file_list_context_menu(self, pos):
        if not self._file_list.selectedItems():
            return
        menu = QMenu(self)
        act = QAction(f"Remove {len(self._file_list.selectedItems())} file(s)", self)
        act.triggered.connect(self._remove_selected_files)
        menu.addAction(act)
        menu.exec(self._file_list.mapToGlobal(pos))

    def _file_list_key_press(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self._remove_selected_files()
        else:
            QListWidget.keyPressEvent(self._file_list, event)

    def _new_extract(self):
        """Reset everything for a fresh extraction session."""
        if self._worker is not None:
            self._worker.cancel()
            self._worker = None
        self._file_list.clear()
        self._table.setModel(None)
        self._model = None
        self._df = None
        self._lbl_count.setText("No data")
        self._status_lbl.setText("")
        self._progress.setVisible(False)
        self._btn_run.setEnabled(True)
        self._btn_cancel.setEnabled(False)
        self.status_message.emit("Ready for new extraction")

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

        # Add balance validation column if balance/debit/credit present
        display_df = _add_balance_check(self._df)

        self._model = PandasModel(display_df)
        self._table.setModel(self._model)
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
        if self._model is None:
            QMessageBox.information(self, "Save", "No data to save yet.")
            return
        # Use the model's df so any inline edits are captured
        df = self._model.get_df()
        # Drop computed columns that aren't real fields
        df = df.drop(columns=[c for c in ("balance_check",) if c in df.columns])
        if df.empty:
            QMessageBox.information(self, "Save", "No data to save yet.")
            return
        from datetime import datetime
        tpl_name = self._tpl_combo.currentText()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        total = 0
        if "_source_file" in df.columns:
            for src in df["_source_file"].dropna().unique():
                batch_name = f"{Path(src).stem}__{timestamp}{Path(src).suffix}"
                mask = df["_source_file"] == src
                rows = df[mask].to_dict("records")
                total += insert_transactions(
                    rows, source_file=src, batch_name=batch_name, template_name=tpl_name
                )
        else:
            batch_name = f"batch__{timestamp}"
            rows = df.to_dict("records")
            total += insert_transactions(
                rows, source_file="unknown", batch_name=batch_name, template_name=tpl_name
            )
        self.status_message.emit(f"Saved {total} rows to database")
        QMessageBox.information(self, "Saved", f"Saved {total} rows to database.")
