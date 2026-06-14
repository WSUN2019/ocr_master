"""
History page — query SQLite transactions, filter, export CSV, delete batches.
"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QBrush
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QTableView, QGroupBox, QLineEdit, QLayout,
    QDateEdit, QAbstractItemView, QHeaderView,
    QFileDialog, QMessageBox, QSpinBox, QCheckBox
)
from PyQt6.QtCore import QDate

from core.storage import query_transactions, query_import_log, delete_by_source, delete_by_batch, df_to_csv_bytes, init_db, update_transaction_field
from core.template import template_names

from core.app_paths import APP_DIR
OUTPUT_DIR  = APP_DIR / "output"
CONFIG_PATH = APP_DIR / "config.json"


def _to_num(v) -> float | None:
    """Parse a value like '$1,234.56' or 78.22 into a float, or None if blank."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).replace("$", "").replace(",", "").strip()
    if not s or s.lower() == "none":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _add_balance_check(df: pd.DataFrame) -> pd.DataFrame:
    """
    Insert a 'balance_check' column next to the balance column.
    For each consecutive pair of rows within the same batch/file,
    verifies the running balance is consistent.
    Sign convention (credit-adds vs debit-adds) is auto-detected per batch
    using the first row pair that has enough data to distinguish.
    """
    cols = {c.lower(): c for c in df.columns}
    bal_col  = cols.get("balance")
    deb_col  = next((cols[k] for k in cols if "debit"  in k), None)
    cred_col = next((cols[k] for k in cols if "credit" in k), None)

    if not bal_col or (not deb_col and not cred_col):
        return df

    df = df.copy()
    check = pd.Series("", index=df.index)

    grp_cols = [c for c in ("batch_name", "source_file") if c in df.columns]
    groups = df.groupby(grp_cols, sort=False) if grp_cols else [("all", df)]

    for _, grp in groups:
        bal_rows = [i for i in grp.index if _to_num(df.at[i, bal_col]) is not None]

        # Detect sign convention: credit-adds (standard) vs debit-adds (bank-ledger)
        # Test on the first row pair where a non-zero debit or credit is present
        credit_adds = True  # default: credit increases balance
        for i in range(1, len(bal_rows)):
            idx      = bal_rows[i]
            prev_idx = bal_rows[i - 1]
            prev_bal = _to_num(df.at[prev_idx, bal_col])
            curr_bal = _to_num(df.at[idx,      bal_col])
            debit    = _to_num(df.at[idx, deb_col])  if deb_col  else None
            credit   = _to_num(df.at[idx, cred_col]) if cred_col else None
            if prev_bal is None or curr_bal is None:
                continue
            amt = (debit or 0.0) + (credit or 0.0)
            if amt == 0:
                continue  # can't distinguish with a zero-amount row
            exp_standard = prev_bal + (credit or 0.0) - (debit or 0.0)
            exp_inverted = prev_bal + (debit or 0.0) - (credit or 0.0)
            if abs(exp_standard - curr_bal) < abs(exp_inverted - curr_bal):
                credit_adds = True
            else:
                credit_adds = False
            break  # convention set from first usable pair

        # Detect if balance is sparse (sub-grouped): many rows have no balance.
        # In that case, group rows by the balance-anchor rows and sum across the group.
        total_rows = len(grp)
        sparse_balance = total_rows > 1 and len(bal_rows) < total_rows * 0.6

        all_grp_idx = list(grp.index)

        for i, idx in enumerate(bal_rows):
            if i == 0:
                continue
            prev_idx = bal_rows[i - 1]
            prev_bal = _to_num(df.at[prev_idx, bal_col])
            curr_bal = _to_num(df.at[idx,      bal_col])

            if prev_bal is None or curr_bal is None:
                continue

            if sparse_balance:
                # Sum all debits/credits between prev_bal_row (exclusive) and curr (inclusive)
                start = all_grp_idx.index(prev_idx) + 1
                end   = all_grp_idx.index(idx) + 1
                group_slice = all_grp_idx[start:end]
                total_debit  = sum(_to_num(df.at[r, deb_col])  or 0.0 for r in group_slice) if deb_col  else 0.0
                total_credit = sum(_to_num(df.at[r, cred_col]) or 0.0 for r in group_slice) if cred_col else 0.0
            else:
                total_debit  = _to_num(df.at[idx, deb_col])  or 0.0 if deb_col  else 0.0
                total_credit = _to_num(df.at[idx, cred_col]) or 0.0 if cred_col else 0.0

            if credit_adds:
                expected = prev_bal + total_credit - total_debit
            else:
                expected = prev_bal + total_debit - total_credit

            if abs(expected - curr_bal) < 0.02:
                check.at[idx] = "✓ Match"
            else:
                check.at[idx] = f"✗  {expected:,.2f}"

    bal_pos = df.columns.get_loc(bal_col) + 1
    df.insert(bal_pos, "balance_check", check)
    return df


_HIDDEN_COLS   = frozenset({"id"})
_READONLY_COLS = frozenset({
    "batch_name", "source_file", "file_row",
    "template_name", "imported_at", "balance_check",
})
_BALANCE_TRIGGER = ("balance", "debit", "credit", "amount")


class PandasModel(QAbstractTableModel):
    _GREEN = QColor("#10b981")
    _RED   = QColor("#ef4444")
    _NOTE_BG = QColor(59, 130, 246, 35)   # faint blue tint for overridden rows

    edit_requested = pyqtSignal(int, str, str, str)  # row_id, col_name, new_value, note

    def __init__(self, df: pd.DataFrame):
        super().__init__()
        self._df   = df.copy()
        self._cols = [c for c in df.columns if c not in _HIDDEN_COLS]
        self._check_col = (
            self._cols.index("balance_check")
            if "balance_check" in self._cols else -1
        )

    def rowCount(self, parent=QModelIndex()): return len(self._df)
    def columnCount(self, parent=QModelIndex()): return len(self._cols)

    def _col(self, vis: int) -> str:
        return self._cols[vis]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        col = self._col(index.column())
        val = self._df[col].iloc[index.row()]

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return "" if pd.isna(val) else str(val)

        # balance_check colours
        if index.column() == self._check_col and self._check_col >= 0:
            text = "" if pd.isna(val) else str(val)
            if role == Qt.ItemDataRole.ForegroundRole:
                if text.startswith("✓"): return self._GREEN
                if text.startswith("✗"): return self._RED
            if role == Qt.ItemDataRole.BackgroundRole:
                if text.startswith("✓"): return QColor(16, 185, 129, 30)
                if text.startswith("✗"): return QColor(239, 68,  68,  30)
            return None

        if role == Qt.ItemDataRole.BackgroundRole:
            # Blue tint on rows that have a note (manual override)
            if "note" in self._df.columns:
                note = self._df["note"].iloc[index.row()]
                if pd.notna(note) and str(note).strip():
                    return self._NOTE_BG
            if index.row() % 2:
                return QColor(248, 250, 252)  # slate-50 alternate row

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole: return None
        if orientation == Qt.Orientation.Horizontal:
            return self._col(section)
        return str(section + 1)

    def flags(self, index):
        base = super().flags(index)
        if self._col(index.column()) in _READONLY_COLS:
            return base
        return base | Qt.ItemFlag.ItemIsEditable

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role != Qt.ItemDataRole.EditRole:
            return False
        col = self._col(index.column())
        if col in _READONLY_COLS:
            return False
        new_val = str(value).strip()
        row = index.row()
        df_idx = self._df.index[row]

        old_raw = self._df.at[df_idx, col]
        old_val = "" if pd.isna(old_raw) else str(old_raw).strip()
        if old_val == new_val:
            return False

        # Cast to object dtype first to silence pandas mixed-type warning
        if self._df[col].dtype != object:
            self._df[col] = self._df[col].astype(object)
        self._df.at[df_idx, col] = new_val
        self.dataChanged.emit(index, index, [role])

        # Auto-stamp note for non-note edits
        if col != "note" and "note" in self._df.columns:
            note = f"Manual override: [{col}] {old_val!r} → {new_val!r}"
            self._df.at[df_idx, "note"] = note
            if "note" in self._cols:
                note_vis = self._cols.index("note")
                self.dataChanged.emit(
                    self.index(row, note_vis), self.index(row, note_vis),
                    [Qt.ItemDataRole.DisplayRole]
                )

        if "id" in self._df.columns:
            row_id = self._df["id"].iloc[row]
            if pd.notna(row_id):
                note = self._df["note"].iloc[row] if "note" in self._df.columns else ""
                self.edit_requested.emit(int(row_id), col, new_val, note)

        if any(k in col.lower() for k in _BALANCE_TRIGGER):
            self._recompute_balance_check()

        return True

    def _recompute_balance_check(self):
        base = self._df.drop(columns=["balance_check"], errors="ignore")
        new_df = _add_balance_check(base)
        if "balance_check" not in new_df.columns:
            return
        self._df["balance_check"] = new_df["balance_check"].values
        if "balance_check" in self._cols:
            c = self._cols.index("balance_check")
            self.dataChanged.emit(
                self.index(0, c),
                self.index(len(self._df) - 1, c),
                [Qt.ItemDataRole.DisplayRole,
                 Qt.ItemDataRole.ForegroundRole,
                 Qt.ItemDataRole.BackgroundRole],
            )

    def get_df(self):
        return self._df

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder):
        if column < 0 or column >= len(self._cols):
            return
        self.layoutAboutToBeChanged.emit()
        col = self._cols[column]
        ascending = order == Qt.SortOrder.AscendingOrder
        try:
            self._df = self._df.sort_values(col, ascending=ascending, na_position="last")
            self._df = self._df.reset_index(drop=True)
        except Exception:
            pass
        self.layoutChanged.emit()


class HistoryWidget(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        init_db()
        self._df: pd.DataFrame | None = None
        self._setup_ui()
        self._table.horizontalHeader().sectionMoved.connect(self._on_column_moved)

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
        filter_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)

        self._date_check = QCheckBox("Date range:")
        self._date_check.setChecked(False)
        self._date_check.stateChanged.connect(self._on_date_filter_toggled)
        filter_layout.addWidget(self._date_check)

        self._date_from = QDateEdit()
        self._date_from.setCalendarPopup(True)
        self._date_from.setDate(QDate.currentDate().addYears(-5))
        self._date_from.setDisplayFormat("yyyy-MM-dd")
        self._date_from.setEnabled(False)
        self._date_from.setFixedWidth(120)
        filter_layout.addWidget(self._date_from)

        filter_layout.addWidget(QLabel("→"))

        self._date_to = QDateEdit()
        self._date_to.setCalendarPopup(True)
        self._date_to.setDate(QDate.currentDate())
        self._date_to.setDisplayFormat("yyyy-MM-dd")
        self._date_to.setEnabled(False)
        self._date_to.setFixedWidth(120)
        filter_layout.addWidget(self._date_to)

        filter_layout.addWidget(QLabel("Template:"))
        self._tpl_filter = QComboBox()
        self._tpl_filter.setFixedWidth(160)
        filter_layout.addWidget(self._tpl_filter)

        filter_layout.addWidget(QLabel("Search:"))
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Filter description…")
        self._search_edit.setFixedWidth(180)
        self._search_edit.textChanged.connect(self._apply_search_filter)
        filter_layout.addWidget(self._search_edit)

        filter_layout.addWidget(QLabel("Max rows:"))
        self._limit_spin = QSpinBox()
        self._limit_spin.setRange(100, 100000)
        self._limit_spin.setValue(5000)
        self._limit_spin.setSingleStep(500)
        self._limit_spin.setFixedWidth(80)
        filter_layout.addWidget(self._limit_spin)

        btn_query = QPushButton("Query")
        btn_query.setObjectName("btn_primary")
        btn_query.clicked.connect(self._run_query)
        filter_layout.addWidget(btn_query)

        btn_all = QPushButton("Show All")
        btn_all.setToolTip("Load all rows regardless of date")
        btn_all.clicked.connect(self._run_query_all)
        filter_layout.addWidget(btn_all)

        filter_layout.addStretch()

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
        hdr.setSectionsMovable(True)

        self._table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        table_layout.addWidget(self._table)

        # Action row
        action_row = QHBoxLayout()
        self._lbl_count = QLabel("No data loaded")
        self._lbl_count.setStyleSheet("color: #2563eb;")
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

    # ── Config persistence ────────────────────────────────────────────────────

    def _load_config(self) -> dict:
        try:
            return json.loads(CONFIG_PATH.read_text())
        except Exception:
            return {}

    def _save_config(self, data: dict):
        try:
            existing = self._load_config()
            existing.update(data)
            CONFIG_PATH.write_text(json.dumps(existing, indent=2))
        except Exception:
            pass

    def _on_column_moved(self, logical: int, old_visual: int, new_visual: int):
        """Save column order whenever the user drags a header."""
        self._save_column_order()

    def _save_column_order(self):
        hdr = self._table.horizontalHeader()
        proxy = self._table.model()
        if not proxy:
            return
        source = proxy.sourceModel() if hasattr(proxy, "sourceModel") else proxy
        order = []
        for vis in range(hdr.count()):
            logical = hdr.logicalIndex(vis)
            name = source.headerData(logical, Qt.Orientation.Horizontal,
                                     Qt.ItemDataRole.DisplayRole)
            if name:
                order.append(name)
        self._save_config({"history_column_order": order})

    def _restore_column_order(self):
        saved = self._load_config().get("history_column_order", [])
        if not saved:
            return
        hdr = self._table.horizontalHeader()
        proxy = self._table.model()
        if not proxy:
            return
        source = proxy.sourceModel() if hasattr(proxy, "sourceModel") else proxy

        # Map column name → current logical index
        col_map = {}
        for i in range(source.columnCount()):
            name = source.headerData(i, Qt.Orientation.Horizontal,
                                     Qt.ItemDataRole.DisplayRole)
            if name:
                col_map[name] = i

        # Move each saved column to its saved visual position
        hdr.blockSignals(True)
        for target_vis, col_name in enumerate(saved):
            if col_name not in col_map:
                continue
            logical = col_map[col_name]
            current_vis = hdr.visualIndex(logical)
            if current_vis != target_vis:
                hdr.moveSection(current_vis, target_vis)
        hdr.blockSignals(False)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def refresh(self):
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
        self._df = _add_balance_check(query_transactions(
            template_name=tpl,
            limit=self._limit_spin.value(),
        ))
        self._after_query()

    def _on_date_filter_toggled(self, state: int):
        enabled = bool(state)
        self._date_from.setEnabled(enabled)
        self._date_to.setEnabled(enabled)

    def _run_query(self):
        tpl = self._tpl_filter.currentData()
        use_dates = self._date_check.isChecked()
        self._df = _add_balance_check(query_transactions(
            date_from=self._date_from.date().toString("yyyy-MM-dd") if use_dates else None,
            date_to=self._date_to.date().toString("yyyy-MM-dd") if use_dates else None,
            template_name=tpl,
            limit=self._limit_spin.value(),
        ))
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
        sort_by = [c for c in ("template_name", "source_file", "batch_name", "file_row")
                   if c in df.columns]
        if sort_by:
            df = df.sort_values(sort_by, na_position="last").reset_index(drop=True)
        model = PandasModel(df)
        model.edit_requested.connect(self._on_cell_edited)
        self._table.setModel(model)
        self._lbl_count.setText(f"{len(df)} rows")

        # Size columns to content, then restore user's saved column order
        hdr = self._table.horizontalHeader()
        hdr.blockSignals(True)
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._table.resizeColumnsToContents()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hdr.blockSignals(False)
        self._restore_column_order()

    def _on_cell_edited(self, row_id: int, col_name: str, new_value: str, note: str):
        update_transaction_field(row_id, col_name, new_value, note=note)
        self.status_message.emit(f"Row {row_id} — {note or col_name + ' updated'}")

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
