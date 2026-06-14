"""
Database tab — browse and manage the SQLite database tables.
Shows row counts, lets you browse any table, delete import_log entries
(which clears the duplicate-detection gate so files can be re-extracted),
and perform housekeeping (vacuum, wipe).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QTableView, QGroupBox, QSpinBox,
    QAbstractItemView, QHeaderView, QFileDialog, QMessageBox,
    QSizePolicy
)

from core.storage import (
    list_tables, query_table, delete_import_log_rows,
    db_size_mb, init_db
)
from core.config import get_config


class _ReadOnlyModel(QAbstractTableModel):
    def __init__(self, df: pd.DataFrame):
        super().__init__()
        self._df = df.reset_index(drop=True)

    def rowCount(self, parent=QModelIndex()): return len(self._df)
    def columnCount(self, parent=QModelIndex()): return len(self._df.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            val = self._df.iloc[index.row(), index.column()]
            return "" if pd.isna(val) else str(val)
        if role == Qt.ItemDataRole.BackgroundRole and index.row() % 2:
            return QColor(248, 250, 252)
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return str(self._df.columns[section])
        return str(section + 1)

    def get_df(self): return self._df


class DatabaseWidget(QWidget):
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

        # ── Title ─────────────────────────────────────────────────────────────
        title_row = QHBoxLayout()
        title = QLabel("Database")
        title.setObjectName("section_title")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_row.addWidget(title)
        title_row.addStretch()
        root.addLayout(title_row)

        # ── DB info strip ─────────────────────────────────────────────────────
        info_group = QGroupBox("Database Info")
        info_layout = QHBoxLayout(info_group)

        self._lbl_path = QLabel()
        self._lbl_path.setStyleSheet("color: #475569; font-size: 11px;")
        self._lbl_path.setWordWrap(False)
        self._lbl_path.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        info_layout.addWidget(self._lbl_path)

        self._lbl_size = QLabel()
        self._lbl_size.setStyleSheet("color: #2563eb; font-size: 11px;")
        info_layout.addWidget(self._lbl_size)

        info_layout.addSpacing(16)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh)
        info_layout.addWidget(btn_refresh)

        root.addWidget(info_group)

        # ── Table summary strip ───────────────────────────────────────────────
        summary_group = QGroupBox("Tables")
        summary_layout = QHBoxLayout(summary_group)
        self._summary_labels: dict[str, QLabel] = {}
        for tbl in ("transactions", "import_log"):
            lbl = QLabel(f"{tbl}: —")
            lbl.setStyleSheet("font-size: 12px; padding: 4px 12px;")
            summary_layout.addWidget(lbl)
            self._summary_labels[tbl] = lbl
        summary_layout.addStretch()
        root.addWidget(summary_group)

        # ── Browser controls ──────────────────────────────────────────────────
        ctrl_group = QGroupBox("Browse")
        ctrl_layout = QHBoxLayout(ctrl_group)

        ctrl_layout.addWidget(QLabel("Table:"))
        self._tbl_combo = QComboBox()
        self._tbl_combo.setMinimumWidth(180)
        self._tbl_combo.currentIndexChanged.connect(self._load_selected_table)
        ctrl_layout.addWidget(self._tbl_combo)

        ctrl_layout.addWidget(QLabel("Limit:"))
        self._limit_spin = QSpinBox()
        self._limit_spin.setRange(50, 50000)
        self._limit_spin.setValue(500)
        self._limit_spin.setSingleStep(500)
        self._limit_spin.setFixedWidth(80)
        ctrl_layout.addWidget(self._limit_spin)

        btn_browse = QPushButton("Load")
        btn_browse.setObjectName("btn_primary")
        btn_browse.clicked.connect(self._load_selected_table)
        ctrl_layout.addWidget(btn_browse)

        ctrl_layout.addStretch()

        self._lbl_note = QLabel(
            "Tip: select import_log rows and click 'Delete Selected' to allow re-extraction of those files"
        )
        self._lbl_note.setStyleSheet("color: #64748b; font-size: 11px;")
        ctrl_layout.addWidget(self._lbl_note)

        root.addWidget(ctrl_group)

        # ── Table view ────────────────────────────────────────────────────────
        self._table = QTableView()
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        hdr.setStretchLastSection(True)
        self._table.setSortingEnabled(False)
        root.addWidget(self._table)

        # ── Action row ────────────────────────────────────────────────────────
        action_row = QHBoxLayout()
        self._lbl_count = QLabel("No data")
        self._lbl_count.setStyleSheet("color: #2563eb;")
        action_row.addWidget(self._lbl_count)
        action_row.addStretch()

        self._btn_delete_rows = QPushButton("Delete Selected")
        self._btn_delete_rows.setObjectName("btn_danger")
        self._btn_delete_rows.setToolTip(
            "Delete the selected import_log rows — allows those files to be re-extracted"
        )
        self._btn_delete_rows.setEnabled(False)
        self._btn_delete_rows.clicked.connect(self._delete_selected_import_log_rows)
        action_row.addWidget(self._btn_delete_rows)

        btn_export = QPushButton("Export CSV")
        btn_export.clicked.connect(self._export_csv)
        action_row.addWidget(btn_export)

        root.addLayout(action_row)

        # Enable Delete Selected only when import_log is shown
        self._tbl_combo.currentTextChanged.connect(self._on_table_changed)

    # ── Populate ──────────────────────────────────────────────────────────────

    def _refresh_db_info(self):
        cfg = get_config()
        path = cfg.db_path
        self._lbl_path.setText(f"Path: {path}")
        mb = db_size_mb()
        self._lbl_size.setText(f"{mb:.2f} MB")

    def _refresh_summary(self):
        tables = dict(list_tables())
        for name, lbl in self._summary_labels.items():
            count = tables.get(name, 0)
            lbl.setText(f"{name}: {count:,} rows")

    def _refresh_table_combo(self):
        current = self._tbl_combo.currentText()
        self._tbl_combo.blockSignals(True)
        self._tbl_combo.clear()
        for name, count in list_tables():
            self._tbl_combo.addItem(f"{name}  ({count:,} rows)", name)
        # Restore previous selection or default to import_log
        idx = self._tbl_combo.findData("import_log")
        if current:
            found = self._tbl_combo.findData(current)
            if found >= 0:
                idx = found
        if idx >= 0:
            self._tbl_combo.setCurrentIndex(idx)
        self._tbl_combo.blockSignals(False)

    def refresh(self):
        self._refresh_db_info()
        self._refresh_summary()
        self._refresh_table_combo()
        self._load_selected_table()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    # ── Table browsing ────────────────────────────────────────────────────────

    def _load_selected_table(self):
        table_name = self._tbl_combo.currentData()
        if not table_name:
            return
        self._df = query_table(table_name, limit=self._limit_spin.value())
        model = _ReadOnlyModel(self._df)
        self._table.setModel(model)
        self._lbl_count.setText(f"{len(self._df)} rows")
        self.status_message.emit(f"Loaded {len(self._df)} rows from {table_name}")

    def _on_table_changed(self, text: str):
        tbl = self._tbl_combo.currentData()
        is_log = tbl == "import_log"
        self._btn_delete_rows.setEnabled(is_log)
        self._lbl_note.setVisible(is_log)

    # ── Delete import_log rows ────────────────────────────────────────────────

    def _delete_selected_import_log_rows(self):
        tbl = self._tbl_combo.currentData()
        if tbl != "import_log":
            return
        model = self._table.model()
        if not model or self._df is None:
            return
        selected = {idx.row() for idx in self._table.selectedIndexes()}
        if not selected:
            QMessageBox.information(self, "No Selection", "Select one or more rows to delete.")
            return

        # Get the id values for selected rows
        df = model.get_df()
        if "id" not in df.columns:
            return
        ids = [int(df["id"].iloc[r]) for r in sorted(selected) if pd.notna(df["id"].iloc[r])]
        filenames = []
        if "filename" in df.columns:
            filenames = [str(df["filename"].iloc[r]) for r in sorted(selected)]

        msg = f"Delete {len(ids)} import_log entr{'y' if len(ids)==1 else 'ies'}?\n\n"
        if filenames:
            msg += "\n".join(filenames[:10])
            if len(filenames) > 10:
                msg += f"\n…and {len(filenames)-10} more"
        msg += "\n\nThis clears the duplicate-detection gate so these files can be re-extracted.\nTransaction history for these files is NOT deleted."
        reply = QMessageBox.question(self, "Delete Import Log Entries", msg,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        n = delete_import_log_rows(ids)
        self.refresh()
        self.status_message.emit(f"Deleted {n} import_log entr{'y' if n==1 else 'ies'}")

    # ── Export ────────────────────────────────────────────────────────────────

    def _export_csv(self):
        if self._df is None or self._df.empty:
            QMessageBox.information(self, "Export", "No data to export.")
            return
        from core.config import get_config
        out_dir = get_config().output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        tbl = self._tbl_combo.currentData() or "table"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", str(out_dir / f"{tbl}_export.csv"), "CSV (*.csv)"
        )
        if path:
            self._df.to_csv(path, index=False)
            self.status_message.emit(f"Exported: {Path(path).name}")
