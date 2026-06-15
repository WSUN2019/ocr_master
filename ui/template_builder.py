"""
Template Builder — open an image, draw red boxes, label fields, save template.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QLineEdit, QComboBox,
    QGroupBox, QListWidget, QListWidgetItem,
    QFileDialog, QInputDialog, QMessageBox,
    QDoubleSpinBox, QFormLayout, QScrollArea, QCheckBox
)
from PIL import Image

from core.renderer import render_image, open_source_image
from core.template import (
    list_templates, load_template, save_template,
    delete_template, build_template
)
from ui.canvas_widget import CanvasWidget

PRESET_FIELDS = sorted([
    "account_number", "amount", "balance", "bank_name",
    "credit", "debit", "description", "post_date",
    "statement_period", "transaction_date",
])


class TemplateBuilderWidget(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._source_img: Image.Image | None = None
        self._source_filename: str = ""
        self._source_path: str = ""
        self._pending_rect: QRectF | None = None
        self._current_tpl: dict | None = None
        self._setup_ui()
        self._refresh_template_list()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(6)

        # ── Single header row: title | template controls | open/fit ──────────
        header = QHBoxLayout()
        header.setSpacing(8)

        lbl = QLabel("Template Builder")
        lbl.setObjectName("section_title")
        lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header.addWidget(lbl)

        header.addSpacing(12)
        header.addWidget(QLabel("Template:"))

        self._tpl_combo = QComboBox()
        self._tpl_combo.setEditable(True)
        self._tpl_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._tpl_combo.lineEdit().setPlaceholderText("Select or type a template name…")
        self._tpl_combo.setMinimumWidth(220)
        self._tpl_combo.currentIndexChanged.connect(self._load_selected_template)
        header.addWidget(self._tpl_combo)

        btn_save = QPushButton("Save")
        btn_save.setObjectName("btn_primary")
        btn_save.clicked.connect(self._save_template)
        header.addWidget(btn_save)

        btn_new = QPushButton("New")
        btn_new.clicked.connect(self._new_template)
        header.addWidget(btn_new)

        btn_del = QPushButton("Delete")
        btn_del.setObjectName("btn_danger")
        btn_del.clicked.connect(self._delete_template)
        header.addWidget(btn_del)

        header.addStretch()

        self._save_info_lbl = QLabel("")
        self._save_info_lbl.setStyleSheet("color: #2563eb; font-size: 11px;")
        header.addWidget(self._save_info_lbl)

        header.addSpacing(12)

        btn_open = QPushButton("Open Image / PDF")
        btn_open.setObjectName("btn_primary")
        btn_open.clicked.connect(self._open_file)
        header.addWidget(btn_open)

        btn_fit = QPushButton("Fit Image")
        btn_fit.clicked.connect(lambda: self._canvas.fit_image())
        btn_fit.setToolTip("Reset zoom so the full image fits in the canvas")
        header.addWidget(btn_fit)

        root.addLayout(header)

        # ── Main splitter: canvas | right panel ───────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(4)

        # Canvas
        self._canvas = CanvasWidget()
        self._canvas.box_drawn.connect(self._on_box_drawn)
        self._canvas.box_removed.connect(self._on_box_removed)
        self._canvas.box_selected.connect(self._on_canvas_box_selected)
        self._canvas.boxes_changed.connect(self._refresh_field_list)
        splitter.addWidget(self._canvas)

        # Right panel — fixed width, scrollable when app is resized small
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(10)

        # Field list
        fg = QGroupBox("Fields (draw a box, then label it)")
        fg_layout = QVBoxLayout(fg)

        self._field_list = QListWidget()
        self._field_list.setAlternatingRowColors(True)
        self._field_list.setMinimumHeight(168)  # ~6 rows at 28px each
        self._field_list.currentRowChanged.connect(self._on_field_row_changed)
        fg_layout.addWidget(self._field_list)

        self._repeat_check = QCheckBox("Repeat on every row")
        self._repeat_check.setToolTip(
            "Fields like Bank Name or Account Number appear once on the statement\n"
            "but should be copied into every transaction row."
        )
        self._repeat_check.setEnabled(False)
        self._repeat_check.stateChanged.connect(self._on_repeat_toggled)
        fg_layout.addWidget(self._repeat_check)

        self._subgroup_check = QCheckBox("Sub-group field")
        self._subgroup_check.setToolTip(
            "Fields like Date or Balance that appear once per group of rows\n"
            "(e.g. Royal Bank of Scotland: one date covers 4 sub-rows).\n"
            "Value is carried forward to rows where it is blank.\n"
            "Balance check will sum debits/credits across the whole group."
        )
        self._subgroup_check.setEnabled(False)
        self._subgroup_check.stateChanged.connect(self._on_subgroup_toggled)
        fg_layout.addWidget(self._subgroup_check)

        self._group_anchor_check = QCheckBox("Group anchor (⊕)")
        self._group_anchor_check.setToolTip(
            "Marks the field (e.g. date) that signals the start of a new transaction.\n"
            "When this field has a value, all previous rows are collapsed into one row.\n"
            "Use with 'Concat in group' on description to merge multi-line transactions."
        )
        self._group_anchor_check.setEnabled(False)
        self._group_anchor_check.stateChanged.connect(self._on_group_anchor_toggled)
        fg_layout.addWidget(self._group_anchor_check)

        self._concat_check = QCheckBox("Concat in group (∑)")
        self._concat_check.setToolTip(
            "Concatenates this field's values across all rows in a group.\n"
            "Use on description fields where one transaction spans several lines."
        )
        self._concat_check.setEnabled(False)
        self._concat_check.stateChanged.connect(self._on_concat_toggled)
        fg_layout.addWidget(self._concat_check)

        self._currency_check = QCheckBox("Currency (2 decimal places  $)")
        self._currency_check.setToolTip(
            "OCR sometimes drops the decimal point and/or thousands comma.\n"
            "Enabling this reconstructs the correct value from raw digits:\n"
            "  '100000'  →  1000.00  (from '1,000.00')\n"
            "  '10050'   →   100.50  (from '100.50')\n"
            "Can be combined with any of the grouping flags above."
        )
        self._currency_check.setEnabled(False)
        self._currency_check.stateChanged.connect(self._on_currency_toggled)
        fg_layout.addWidget(self._currency_check)

        date_fmt_row = QHBoxLayout()
        date_fmt_row.setSpacing(6)
        date_fmt_row.addWidget(QLabel("Date format:"))
        self._date_format_combo = QComboBox()
        self._date_format_combo.setEditable(True)
        self._date_format_combo.lineEdit().setPlaceholderText("e.g. DD MMM YY  (blank = auto-detect)")
        self._date_format_combo.addItems([
            "", "DD MMM YY", "DD MMM YYYY", "DD-MMM-YYYY",
            "DD/MM/YY", "DD/MM/YYYY", "D/M/YY", "D/M/YYYY",
            "MM/DD/YY", "MM/DD/YYYY", "M/D/YY", "M/D/YYYY",
            "YYYY-MM-DD",
        ])
        self._date_format_combo.setCurrentIndex(0)
        self._date_format_combo.setEnabled(False)
        self._date_format_combo.setToolTip(
            "Tokens: DD (day 01-31), D (day 1-31), MM (month 01-12), M (month 1-12),\n"
            "        MMM (Jan/Feb/… abbreviation), YY (2-digit year), YYYY (4-digit year)\n"
            "Separators: - / space (OCR mismatches tolerated)\n"
            "Leave blank to use auto-detection from common date formats."
        )
        self._date_format_combo.lineEdit().editingFinished.connect(self._on_date_format_changed)
        self._date_format_combo.activated.connect(lambda _: self._on_date_format_changed())
        date_fmt_row.addWidget(self._date_format_combo)
        fg_layout.addLayout(date_fmt_row)

        btn_row = QHBoxLayout()
        btn_rm = QPushButton("Remove Selected Box")
        btn_rm.setObjectName("btn_danger")
        btn_rm.setFixedWidth(btn_rm.fontMetrics().horizontalAdvance("Remove Selected Box") + 48)
        btn_rm.clicked.connect(self._remove_selected)
        btn_row.addWidget(btn_rm)
        btn_row.addStretch()
        fg_layout.addLayout(btn_row)
        right_layout.addWidget(fg)

        # Row detection
        rd_group = QGroupBox("Row Detection")
        rd_form = QFormLayout(rd_group)
        rd_form.setSpacing(8)

        self._strategy_combo = QComboBox()
        self._strategy_combo.addItem("Fixed Regions", "fixed_regions")
        self._strategy_combo.addItem("Repeat Vertical - 1 row repeats", "repeat_vertical")
        self._strategy_combo.setMinimumWidth(200)
        rd_form.addRow("Strategy:", self._strategy_combo)

        self._row_height = QDoubleSpinBox()
        self._row_height.setRange(2.0, 500.0)
        self._row_height.setValue(12.0)
        self._row_height.setSuffix(" px")
        self._row_height.setFixedWidth(150)
        rd_form.addRow("Row height:", self._row_height)

        self._start_y = QDoubleSpinBox()
        self._start_y.setRange(0.0, 99999.0)
        self._start_y.setValue(0.0)
        self._start_y.setSuffix(" px")
        self._start_y.setFixedWidth(150)
        rd_form.addRow("Start Y:", self._start_y)

        self._end_y = QDoubleSpinBox()
        self._end_y.setRange(0.0, 99999.0)
        self._end_y.setValue(800.0)
        self._end_y.setSuffix(" px")
        self._end_y.setFixedWidth(150)
        rd_form.addRow("End Y:", self._end_y)

        right_layout.addWidget(rd_group)

        # Page filtering
        pf_group = QGroupBox("Page Filtering (multi-page PDFs)")
        pf_form = QFormLayout(pf_group)
        pf_form.setSpacing(6)

        self._skip_pages_edit = QLineEdit()
        self._skip_pages_edit.setPlaceholderText("e.g. 1  or  1, 15")
        self._skip_pages_edit.setToolTip(
            "Comma-separated 1-based page numbers to skip entirely.\n"
            "Example: '1' skips the cover page."
        )
        pf_form.addRow("Skip pages:", self._skip_pages_edit)

        from PyQt6.QtWidgets import QSpinBox
        range_row = QHBoxLayout()
        range_row.setSpacing(6)
        self._page_from = QSpinBox()
        self._page_from.setRange(0, 9999)
        self._page_from.setSpecialValueText("first")
        self._page_from.setToolTip("First page to process (1-based). 0 = from the beginning.")
        self._page_to = QSpinBox()
        self._page_to.setRange(0, 9999)
        self._page_to.setSpecialValueText("last")
        self._page_to.setToolTip("Last page to process (1-based). 0 = to the end.")
        range_row.addWidget(QLabel("From"))
        range_row.addWidget(self._page_from)
        range_row.addWidget(QLabel("to"))
        range_row.addWidget(self._page_to)
        range_row.addStretch()
        pf_form.addRow("Page range:", range_row)

        right_layout.addWidget(pf_group)

        right_layout.addStretch()

        right.setMaximumWidth(420)

        right_scroll = QScrollArea()
        right_scroll.setWidget(right)
        right_scroll.setWidgetResizable(True)
        right_scroll.setMinimumWidth(400)
        right_scroll.setMaximumWidth(420)
        right_scroll.setFrameShape(right_scroll.Shape.NoFrame)

        splitter.addWidget(right_scroll)
        splitter.setSizes([900, 400])
        splitter.setCollapsible(1, False)
        root.addWidget(splitter)

    # ── Keyboard shortcuts (Ctrl+Z/Y for undo/redo) ───────────────────────────

    def keyPressEvent(self, event):
        from PyQt6.QtWidgets import QApplication, QLineEdit, QSpinBox, QDoubleSpinBox
        focused = QApplication.focusWidget()
        is_text = isinstance(focused, (QLineEdit, QSpinBox, QDoubleSpinBox))
        ctrl  = event.modifiers() & Qt.KeyboardModifier.ControlModifier
        shift = event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        if ctrl and not is_text:
            if event.key() == Qt.Key.Key_Z:
                if shift:
                    self._canvas.redo()
                    self.status_message.emit("Redo")
                else:
                    self._canvas.undo()
                    self.status_message.emit("Undo")
                event.accept()
                return
            if event.key() == Qt.Key.Key_Y:
                self._canvas.redo()
                self.status_message.emit("Redo")
                event.accept()
                return
        super().keyPressEvent(event)

    # ── File open ─────────────────────────────────────────────────────────────

    def _open_file(self, path: str = ""):
        if not path:
            from core.app_paths import APP_DIR
            start_dir = APP_DIR / "input_files"
            start_dir.mkdir(exist_ok=True)
            path, _ = QFileDialog.getOpenFileName(
                self, "Open Statement Image",
                str(start_dir),
                "Images & PDFs (*.jpg *.jpeg *.png *.pdf)"
            )
        if not path:
            return
        self._source_path = path
        self._source_filename = Path(path).name
        try:
            file_bytes = Path(path).read_bytes()
            self._source_img = open_source_image(file_bytes, self._source_filename)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Failed to open file", str(e))
            return

        self._canvas.set_image(self._source_img)
        h = self._source_img.height
        self._end_y.setValue(float(h))
        self.status_message.emit(f"Loaded: {self._source_filename}  ({self._source_img.width}×{h} px)")

        # If a template is already selected, draw its boxes onto the newly opened image
        self._apply_template_to_canvas()

    # ── Box drawing ───────────────────────────────────────────────────────────

    def _on_box_drawn(self, rect: QRectF):
        """User finished drawing — ask for a field name and flags."""
        existing_names = {f["name"] for f in self._canvas.get_field_defs()}
        dlg = _FieldNameDialog(PRESET_FIELDS, self)
        if dlg.exec():
            name = dlg.chosen_name()
            if not name:
                return
            if name in existing_names:
                QMessageBox.warning(self, "Duplicate Field",
                    f"A field named '{name}' already exists.\n"
                    "Each field name must be unique.")
                return
            self._canvas.push_undo()
            self._canvas.add_named_box(
                rect, name,
                repeat=dlg.repeat(),
                sub_group=dlg.sub_group(),
                group_anchor=dlg.group_anchor(),
                concat_in_group=dlg.concat_in_group(),
                currency=dlg.currency(),
                date_format=dlg.date_format(),
            )
            self._refresh_field_list()
        # If cancelled, box is discarded (not added to canvas)

    def _on_box_removed(self, index: int):
        self._refresh_field_list()

    def _remove_selected(self):
        self._canvas.push_undo()
        self._canvas.remove_selected_box()
        self._refresh_field_list()

    def _on_canvas_box_selected(self, index: int):
        """Canvas box was clicked — sync highlight in the field list."""
        self._field_list.blockSignals(True)
        self._field_list.setCurrentRow(index)
        self._field_list.blockSignals(False)
        self._sync_field_checkboxes(index)

    def _on_field_row_changed(self, row: int):
        """Field list row clicked — select the matching box on the canvas."""
        self._canvas.select_box_by_index(row)
        self._sync_field_checkboxes(row)

    def _sync_field_checkboxes(self, index: int):
        """Update all field-flag checkboxes from the selected box state."""
        defs = self._canvas.get_field_defs()
        has = 0 <= index < len(defs)
        for cb, key in (
            (self._repeat_check,       "repeat"),
            (self._subgroup_check,     "sub_group"),
            (self._group_anchor_check, "group_anchor"),
            (self._concat_check,       "concat_in_group"),
            (self._currency_check,     "currency"),
        ):
            cb.blockSignals(True)
            cb.setChecked(defs[index].get(key, False) if has else False)
            cb.setEnabled(has)
            cb.blockSignals(False)

        self._date_format_combo.blockSignals(True)
        self._date_format_combo.setCurrentText(defs[index].get("date_format", "") if has else "")
        self._date_format_combo.setEnabled(has)
        self._date_format_combo.blockSignals(False)

    # keep old name as alias so nothing else breaks
    def _sync_repeat_checkbox(self, index: int):
        self._sync_field_checkboxes(index)

    def _on_repeat_toggled(self, state: int):
        index = self._field_list.currentRow()
        if index < 0:
            return
        self._canvas.push_undo()
        self._canvas.set_box_repeat(index, bool(state))
        if state:
            for cb in (self._subgroup_check, self._group_anchor_check, self._concat_check):
                cb.blockSignals(True)
                cb.setChecked(False)
                cb.blockSignals(False)
        self._refresh_field_list()

    def _on_subgroup_toggled(self, state: int):
        index = self._field_list.currentRow()
        if index < 0:
            return
        self._canvas.push_undo()
        self._canvas.set_box_sub_group(index, bool(state))
        if state:
            for cb in (self._repeat_check, self._group_anchor_check, self._concat_check):
                cb.blockSignals(True)
                cb.setChecked(False)
                cb.blockSignals(False)
        self._refresh_field_list()

    def _on_group_anchor_toggled(self, state: int):
        index = self._field_list.currentRow()
        if index < 0:
            return
        self._canvas.push_undo()
        self._canvas.set_box_group_anchor(index, bool(state))
        if state:
            for cb in (self._repeat_check, self._subgroup_check, self._concat_check):
                cb.blockSignals(True)
                cb.setChecked(False)
                cb.blockSignals(False)
        self._refresh_field_list()

    def _on_concat_toggled(self, state: int):
        index = self._field_list.currentRow()
        if index < 0:
            return
        self._canvas.push_undo()
        self._canvas.set_box_concat_in_group(index, bool(state))
        if state:
            for cb in (self._repeat_check, self._subgroup_check, self._group_anchor_check):
                cb.blockSignals(True)
                cb.setChecked(False)
                cb.blockSignals(False)
        self._refresh_field_list()

    def _on_currency_toggled(self, state: int):
        index = self._field_list.currentRow()
        if index < 0:
            return
        self._canvas.push_undo()
        self._canvas.set_box_currency(index, bool(state))
        self._refresh_field_list()

    def _on_date_format_changed(self):
        index = self._field_list.currentRow()
        if index < 0:
            return
        fmt = self._date_format_combo.currentText().strip()
        self._canvas.push_undo()
        self._canvas.set_box_date_format(index, fmt)
        self._refresh_field_list()

    def _refresh_field_list(self):
        row = self._field_list.currentRow()
        self._field_list.blockSignals(True)
        self._field_list.clear()
        for f in self._canvas.get_field_defs():
            bbox = f["bbox"]
            if f.get("group_anchor"):
                prefix = "⊕ "
            elif f.get("concat_in_group"):
                prefix = "∑ "
            elif f.get("sub_group"):
                prefix = "⊞ "
            elif f.get("repeat"):
                prefix = "↺ "
            else:
                prefix = "   "
            suffix = "  $" if f.get("currency") else ""
            date_note = f"  [{f['date_format']}]" if f.get("date_format") else ""
            text = f"{prefix}{f['name']}{suffix}{date_note}  [{bbox[0]:.0f},{bbox[1]:.0f}  →  {bbox[2]:.0f},{bbox[3]:.0f}]"
            self._field_list.addItem(QListWidgetItem(text))
        self._field_list.blockSignals(False)
        if row >= 0:
            self._field_list.setCurrentRow(row)

    # ── Template CRUD ─────────────────────────────────────────────────────────

    def _refresh_template_list(self):
        current_slug = self._tpl_combo.itemData(self._tpl_combo.currentIndex())
        typed_text   = self._tpl_combo.currentText()

        self._tpl_combo.blockSignals(True)
        self._tpl_combo.clear()
        for t in list_templates():
            self._tpl_combo.addItem(t["name"], t["slug"])

        # Restore previous selection if slug still exists; else restore typed text
        if current_slug:
            idx = self._tpl_combo.findData(current_slug)
            if idx >= 0:
                self._tpl_combo.setCurrentIndex(idx)
            else:
                self._tpl_combo.setCurrentIndex(-1)
                self._tpl_combo.setEditText(typed_text)
        else:
            self._tpl_combo.setCurrentIndex(-1)
            self._tpl_combo.setEditText(typed_text)
        self._tpl_combo.blockSignals(False)

    def _load_selected_template(self):
        slug = self._tpl_combo.currentData()
        if not slug:
            self._current_tpl = None
            self._canvas.clear_image()
            self._source_img = None
            self._source_path = ""
            self._source_filename = ""
            self._refresh_field_list()
            return
        tpl = load_template(slug)
        if not tpl:
            return
        self._current_tpl = tpl
        # combo already shows the template name — no separate name field to update
        rd = tpl.get("row_detection", {})
        strategy = rd.get("strategy", "fixed_regions")
        idx = self._strategy_combo.findData(strategy)
        if idx >= 0:
            self._strategy_combo.setCurrentIndex(idx)
        self._row_height.setValue(float(rd.get("row_height_pts", 12.0)))
        self._start_y.setValue(float(rd.get("start_y_pts", 0.0)))
        self._end_y.setValue(float(rd.get("end_y_pts", 800.0)))

        # Page filtering
        skip = tpl.get("skip_pages", [])
        self._skip_pages_edit.setText(", ".join(str(p) for p in skip))
        pr = tpl.get("page_range", [])
        self._page_from.setValue(pr[0] if len(pr) == 2 else 0)
        self._page_to.setValue(pr[1] if len(pr) == 2 else 0)

        # Always show field list from template data
        self._refresh_field_list_from_template(tpl)

        # Auto-load the sample image stored in the template (if still accessible).
        # sample_image_path is stored as a filename only; look it up in input_files/.
        saved_name = tpl.get("sample_image_path", "")
        if saved_name:
            from core.app_paths import APP_DIR
            fname = Path(saved_name).name
            search_dirs = [
                APP_DIR / "input_files",
                APP_DIR / "input_files" / "Examples",
            ]
            candidate = next((d / fname for d in search_dirs if (d / fname).exists()), None)
            if candidate and str(candidate) != self._source_path:
                self._open_file(str(candidate))
            else:
                self._apply_template_to_canvas()
        else:
            self._apply_template_to_canvas()

        if not self._source_img:
            self.status_message.emit(
                f"Template '{tpl.get('name','')}' loaded — open a sample image to see the field boxes"
            )

    def _apply_template_to_canvas(self):
        """Draw the currently selected template's boxes onto the canvas (if image is open)."""
        tpl = getattr(self, "_current_tpl", None)
        if not tpl or not self._source_img:
            return
        self._canvas.load_boxes(
            tpl.get("fields", []),
            float(tpl.get("page_width_pts", self._source_img.width)),
            float(tpl.get("page_height_pts", self._source_img.height)),
        )
        self._refresh_field_list()

    def _refresh_field_list_from_template(self, tpl: dict):
        """Show field list from template JSON (no image needed)."""
        self._field_list.clear()
        for f in tpl.get("fields", []):
            bbox = f["bbox"]
            text = f"{f['name']}  [{bbox[0]:.0f},{bbox[1]:.0f}  →  {bbox[2]:.0f},{bbox[3]:.0f}]"
            self._field_list.addItem(QListWidgetItem(text))

    def _new_template(self):
        self._tpl_combo.blockSignals(True)
        self._tpl_combo.setCurrentIndex(-1)
        self._tpl_combo.clearEditText()
        self._tpl_combo.blockSignals(False)
        self._current_tpl = None
        self._source_img = None
        self._source_path = ""
        self._source_filename = ""
        self._canvas.clear_image()
        self._refresh_field_list()
        for cb in (self._repeat_check, self._subgroup_check,
                   self._group_anchor_check, self._concat_check, self._currency_check):
            cb.setChecked(False)
            cb.setEnabled(False)
        self._date_format_combo.blockSignals(True)
        self._date_format_combo.setCurrentText("")
        self._date_format_combo.setEnabled(False)
        self._date_format_combo.blockSignals(False)
        self._skip_pages_edit.clear()
        self._page_from.setValue(0)
        self._page_to.setValue(0)

    def _delete_template(self):
        idx  = self._tpl_combo.currentIndex()
        slug = self._tpl_combo.itemData(idx)
        if not slug:
            QMessageBox.information(self, "Delete", "No saved template selected.")
            return
        name = self._tpl_combo.itemText(idx)   # use stored name, not typed text
        reply = QMessageBox.question(
            self, "Delete Template",
            f"Delete template '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_template(slug)
            self._refresh_template_list()
            self._new_template()   # clear canvas/fields/name so deleted template can't be re-saved
            self.status_message.emit(f"Deleted template '{name}'")

    def _save_template(self):
        name = self._tpl_combo.currentText().strip()
        if not name:
            QMessageBox.warning(self, "Save Template",
                "Enter a template name in the field at the top before saving.")
            return
        fields = self._canvas.get_field_defs()
        if not fields:
            QMessageBox.warning(self, "Save Template", "Draw at least one field box first.")
            return

        w = float(self._source_img.width) if self._source_img else 0.0
        h = float(self._source_img.height) if self._source_img else 0.0

        rd = {
            "strategy": self._strategy_combo.currentData() or "fixed_regions",
            "row_height_pts": self._row_height.value(),
            "start_y_pts": self._start_y.value(),
            "end_y_pts": self._end_y.value(),
            "anchor_field": fields[0]["name"] if fields else "",
        }

        # Parse skip_pages
        skip_raw = self._skip_pages_edit.text().strip()
        skip_pages = []
        if skip_raw:
            for tok in skip_raw.replace(",", " ").split():
                try:
                    skip_pages.append(int(tok))
                except ValueError:
                    pass

        # Parse page_range
        pf = self._page_from.value()
        pt = self._page_to.value()
        page_range = [pf, pt] if (pf > 0 or pt > 0) else []

        old_slug = self._tpl_combo.itemData(self._tpl_combo.currentIndex())

        tpl = build_template(
            name=name,
            page_width_pts=w,
            page_height_pts=h,
            fields=fields,
            row_detection=rd,
            sample_image_path=Path(self._source_path).name if self._source_path else "",
            skip_pages=skip_pages,
            page_range=page_range,
        )
        slug = save_template(tpl)

        # If the user renamed the template the slug changes — remove the old file
        if old_slug and old_slug != slug:
            delete_template(old_slug)

        self._refresh_template_list()

        # Select the just-saved template so the combo reflects the saved state
        self._tpl_combo.blockSignals(True)
        idx = self._tpl_combo.findData(slug)
        if idx >= 0:
            self._tpl_combo.setCurrentIndex(idx)
        self._tpl_combo.blockSignals(False)

        from core.config import get_config
        saved_path = Path(get_config().templates_dir) / f"{slug}.json"
        self._save_info_lbl.setText(f"Saved: {saved_path}")
        self.status_message.emit(f"Saved: {saved_path}")
        QMessageBox.information(self, "Saved",
            f"Template '{name}' saved with {len(fields)} field(s).\n\n{saved_path}")


# ── Field name dialog ─────────────────────────────────────────────────────────

class _FieldNameDialog(QWidget):
    """Modal to choose a field name and set its repeat / sub_group flags."""

    def __init__(self, presets: list[str], parent=None):
        super().__init__(parent)
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox
        self._dialog = QDialog(parent)
        self._dialog.setWindowTitle("Label this field")
        self._dialog.setMinimumWidth(340)

        layout = QVBoxLayout(self._dialog)
        layout.setSpacing(10)
        layout.addWidget(QLabel("Choose a preset or type a custom name:"))

        self._combo = QComboBox()
        self._combo.addItems(presets)
        self._combo.setEditable(True)
        self._combo.setCurrentText(presets[0])
        layout.addWidget(self._combo)

        self._repeat_chk = QCheckBox("Repeat on every row")
        self._repeat_chk.setToolTip(
            "Value appears once (e.g. bank name) but should stamp onto every row."
        )
        layout.addWidget(self._repeat_chk)

        self._subgroup_chk = QCheckBox("Sub-group field")
        self._subgroup_chk.setToolTip(
            "Value appears once per group of rows (e.g. date or balance in RBS statements).\n"
            "Carried forward to blank rows; balance check sums the whole group."
        )
        layout.addWidget(self._subgroup_chk)

        self._group_anchor_chk = QCheckBox("Group anchor (⊕)")
        self._group_anchor_chk.setToolTip(
            "Marks the field (e.g. date) that signals the start of a new transaction group.\n"
            "When this field has a value, all previous rows collapse into one.\n"
            "Use with 'Concat in group' on description."
        )
        layout.addWidget(self._group_anchor_chk)

        self._concat_chk = QCheckBox("Concat in group (∑)")
        self._concat_chk.setToolTip(
            "Concatenates values across all rows in the group into a single field.\n"
            "Use on description fields that span multiple lines per transaction."
        )
        layout.addWidget(self._concat_chk)

        # all four structural flags are mutually exclusive
        all_chks = [self._repeat_chk, self._subgroup_chk,
                    self._group_anchor_chk, self._concat_chk]
        for chk in all_chks:
            others = [c for c in all_chks if c is not chk]
            chk.toggled.connect(
                lambda on, oth=others: [c.setEnabled(not on) for c in oth] if on else
                                       [c.setEnabled(True) for c in oth]
            )

        # currency is orthogonal — can be combined with any structural flag
        self._currency_chk = QCheckBox("Currency (2 decimal places  $)")
        self._currency_chk.setToolTip(
            "OCR sometimes drops the decimal point and/or thousands comma.\n"
            "Enabling this reconstructs the correct value from raw digits:\n"
            "  '100000'  →  1000.00  (from '1,000.00')\n"
            "  '10050'   →   100.50  (from '100.50')\n"
            "Can be combined with any grouping flag above."
        )
        layout.addWidget(self._currency_chk)

        layout.addWidget(QLabel("Date format (optional):"))
        self._date_fmt_dlg = QComboBox()
        self._date_fmt_dlg.setEditable(True)
        self._date_fmt_dlg.lineEdit().setPlaceholderText("e.g. DD MMM YY  (blank = auto-detect)")
        self._date_fmt_dlg.addItems([
            "", "DD MMM YY", "DD MMM YYYY", "DD-MMM-YYYY",
            "DD/MM/YY", "DD/MM/YYYY", "D/M/YY", "D/M/YYYY",
            "MM/DD/YY", "MM/DD/YYYY", "M/D/YY", "M/D/YYYY",
            "YYYY-MM-DD",
        ])
        self._date_fmt_dlg.setCurrentIndex(0)
        self._date_fmt_dlg.setToolTip(
            "Tokens: DD day (01-31), D day (1-31), MM month (01-12), M month (1-12),\n"
            "        MMM month abbreviation (Jan/Feb/…), YY 2-digit year, YYYY 4-digit year\n"
            "Separators: - / space (OCR mismatches are tolerated)"
        )
        layout.addWidget(self._date_fmt_dlg)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._dialog.accept)
        buttons.rejected.connect(self._dialog.reject)
        layout.addWidget(buttons)

    def exec(self) -> bool:
        return self._dialog.exec() == 1

    def chosen_name(self) -> str:
        return self._combo.currentText().strip()

    def repeat(self) -> bool:
        return self._repeat_chk.isChecked()

    def sub_group(self) -> bool:
        return self._subgroup_chk.isChecked()

    def group_anchor(self) -> bool:
        return self._group_anchor_chk.isChecked()

    def concat_in_group(self) -> bool:
        return self._concat_chk.isChecked()

    def currency(self) -> bool:
        return self._currency_chk.isChecked()

    def date_format(self) -> str:
        return self._date_fmt_dlg.currentText().strip()
