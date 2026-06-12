"""
History page — query SQLite transactions, filter, export CSV, delete batches.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, pyqtSignal, QSortFilterProxyModel
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QTableView, QGroupBox, QLineEdit,
    QDateEdit, QAbstractItemView, QHeaderView,
    QFileDialog, QMessageBox, QSpinBox
)
from PyQt6.QtCore import QDate

from core.storage import query_transactions, query_import_log, delete_by_source, delete_by_batch, df_to_csv_bytes, init_db
from core.template import template_names

OUTPUT_DIR = Path(__file__).parent.parent / "output"


class PandasModel(QAbstractTableModel):
    def __init__(self, df: pd.DataFrame):
        super().__init__()
        self._df = df.copy()

    def rowCount(self, parent=QModelIndex()): return len(self._df)
    def columnCount(self, parent=QModelIndex()): return len(self._df.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid(): return None
        val = self._df.iloc[index.row(), index.column()]
        if role == Qt.ItemDataRole.DisplayRole:
            return "" if pd.isna(val) else str(val)
        if role == Qt.ItemDataRole.BackgroundRole and index.row() % 2:
            return QColor(26, 37, 64)
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole: return None
        if orientation == Qt.Orientation.Horizontal:
            return str(self._df.columns[section])
        return str(section + 1)

    def get_df(self): return self._df


class HistoryWidget(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        init_db()
        self._df: pd.DataFrame | None = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel("Transaction History")
        title.setObjectName("section_title")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        root.addWidget(title)

        # ── Filters ───────────────────────────────────────────────────────────
        filter_group = QGroupBox("Filters")
        filter_layout = QHBoxLayout(filter_group)

        filter_layout.addWidget(QLabel("From:"))
        self._date_from = QDateEdit()
        self._date_from.setCalendarPopup(True)
        self._date_from.setDate(QDate.currentDate().addYears(-5))
        self._date_from.setDisplayFormat("yyyy-MM-dd")
        filter_layout.addWidget(self._date_from)

        filter_layout.addWidget(QLabel("To:"))
        self._date_to = QDateEdit()
        self._date_to.setCalendarPopup(True)
        self._date_to.setDate(QDate.currentDate())
        self._date_to.setDisplayFormat("yyyy-MM-dd")
        filter_layout.addWidget(self._date_to)

        filter_layout.addWidget(QLabel("Template:"))
        self._tpl_filter = QComboBox()
        self._tpl_filter.setMinimumWidth(160)
        filter_layout.addWidget(self._tpl_filter)

        filter_layout.addWidget(QLabel("Search:"))
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Filter description…")
        self._search_edit.setMinimumWidth(160)
        self._search_edit.textChanged.connect(self._apply_search_filter)
        filter_layout.addWidget(self._search_edit)

        filter_layout.addWidget(QLabel("Max rows:"))
        self._limit_spin = QSpinBox()
        self._limit_spin.setRange(100, 100000)
        self._limit_spin.setValue(5000)
        self._limit_spin.setSingleStep(500)
        filter_layout.addWidget(self._limit_spin)

        btn_query = QPushButton("Query")
        btn_query.setObjectName("btn_primary")
        btn_query.clicked.connect(self._run_query)
        filter_layout.addWidget(btn_query)

        btn_all = QPushButton("Show All")
        btn_all.setToolTip("Load all rows regardless of date")
        btn_all.clicked.connect(self._run_query_all)
        filter_layout.addWidget(btn_all)

        root.addWidget(filter_group)

        # ── Table ─────────────────────────────────────────────────────────────
        table_group = QGroupBox("Results")
        table_layout = QVBoxLayout(table_group)

        self._table = QTableView()
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSortingEnabled(True)

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hdr.setStretchLastSection(False)
        hdr.setMinimumSectionSize(60)
        hdr.setDefaultSectionSize(130)

        self._table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        table_layout.addWidget(self._table)

        # Action row
        action_row = QHBoxLayout()
        self._lbl_count = QLabel("No data loaded")
        self._lbl_count.setStyleSheet("color: #a0c4ff;")
        action_row.addWidget(self._lbl_count)
        action_row.addStretch()

        btn_export = QPushButton("Export CSV")
        btn_export.clicked.connect(self._export_csv)
        action_row.addWidget(btn_export)

        action_row.addWidget(QLabel("Delete batch:"))
        self._delete_combo = QComboBox()
        self._delete_combo.setMinimumWidth(200)
        action_row.addWidget(self._delete_combo)

        btn_delete = QPushButton("Delete")
        btn_delete.setObjectName("btn_danger")
        btn_delete.clicked.connect(self._delete_batch)
        action_row.addWidget(btn_delete)

        table_layout.addLayout(action_row)
        root.addWidget(table_group)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_filters()
        self._run_query_all()

    def _refresh_filters(self):
        self._tpl_filter.clear()
        self._tpl_filter.addItem("All templates", None)
        for name in template_names():
            self._tpl_filter.addItem(name, name)

    def _run_query_all(self):
        """Load all rows with no date filter."""
        tpl = self._tpl_filter.currentData()
        self._df = query_transactions(
            template_name=tpl,
            limit=self._limit_spin.value(),
        )
        self._after_query()

    def _run_query(self):
        tpl = self._tpl_filter.currentData()
        self._df = query_transactions(
            date_from=self._date_from.date().toString("yyyy-MM-dd"),
            date_to=self._date_to.date().toString("yyyy-MM-dd"),
            template_name=tpl,
            limit=self._limit_spin.value(),
        )
        self._after_query()

    def _after_query(self):
        self._load_table(self._df)

        self._delete_combo.clear()
        if "batch_name" in self._df.columns:
            # Use batch_name; fall back to source_file for legacy rows with NULL batch_name
            labels = (
                self._df["batch_name"]
                .where(self._df["batch_name"].notna(), self._df.get("source_file"))
                .dropna()
                .unique()
            )
        elif "source_file" in self._df.columns:
            labels = self._df["source_file"].dropna().unique()
        else:
            labels = []
        for val in sorted(labels):
            self._delete_combo.addItem(val)

        self.status_message.emit(f"Loaded {len(self._df)} transactions")

    def _load_table(self, df: pd.DataFrame):
        model = PandasModel(df)
        proxy = QSortFilterProxyModel()
        proxy.setSourceModel(model)
        proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._table.setModel(proxy)
        self._lbl_count.setText(f"{len(df)} rows")

        # Size columns to content on first load, then leave them interactive
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._table.resizeColumnsToContents()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

    def _apply_search_filter(self, text: str):
        if self._df is None:
            return
        if text:
            mask = self._df.apply(
                lambda col: col.astype(str).str.contains(text, case=False, na=False)
            ).any(axis=1)
            self._load_table(self._df[mask])
        else:
            self._load_table(self._df)

    def _export_csv(self):
        if self._df is None or self._df.empty:
            QMessageBox.information(self, "Export", "No data to export.")
            return
        OUTPUT_DIR.mkdir(exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", str(OUTPUT_DIR / "history_export.csv"), "CSV (*.csv)"
        )
        if path:
            self._df.to_csv(path, index=False)
            self.status_message.emit(f"Exported: {Path(path).name}")
            QMessageBox.information(self, "Exported", f"Saved {len(self._df)} rows to:\n{path}")

    def _delete_batch(self):
        src = self._delete_combo.currentText()
        if not src:
            return
        reply = QMessageBox.question(
            self, "Delete Batch",
            f"Delete all rows from '{src}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            n = delete_by_batch(src)
            self._run_query_all()
            self.status_message.emit(f"Deleted {n} rows from '{src}'")
