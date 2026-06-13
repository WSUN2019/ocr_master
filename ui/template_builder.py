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
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # ── Title row ─────────────────────────────────────────────────────────
        title_row = QHBoxLayout()
        lbl = QLabel("Template Builder")
        lbl.setObjectName("section_title")
        lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_row.addWidget(lbl)
        title_row.addStretch()

        btn_open = QPushButton("Open Image / PDF")
        btn_open.setObjectName("btn_primary")
        btn_open.clicked.connect(self._open_file)
        title_row.addWidget(btn_open)

        btn_fit = QPushButton("Fit Image")
        btn_fit.clicked.connect(lambda: self._canvas.fit_image())
        btn_fit.setToolTip("Reset zoom so the full image fits in the canvas")
        title_row.addWidget(btn_fit)

        root.addLayout(title_row)

        # ── Template selector ─────────────────────────────────────────────────
        tpl_row = QHBoxLayout()
        tpl_row.addWidget(QLabel("Template:"))
        self._tpl_combo = QComboBox()
        self._tpl_combo.setMinimumWidth(200)
        self._tpl_combo.currentIndexChanged.connect(self._load_selected_template)
        tpl_row.addWidget(self._tpl_combo)

        btn_new = QPushButton("New")
        btn_new.clicked.connect(self._new_template)
        tpl_row.addWidget(btn_new)

        btn_del = QPushButton("Delete")
        btn_del.setObjectName("btn_danger")
        btn_del.clicked.connect(self._delete_template)
        tpl_row.addWidget(btn_del)

        tpl_row.addStretch()
        root.addLayout(tpl_row)

        # ── Main splitter: canvas | right panel ───────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(4)

        # Canvas
        self._canvas = CanvasWidget()
        self._canvas.box_drawn.connect(self._on_box_drawn)
        self._canvas.box_removed.connect(self._on_box_removed)
        self._canvas.box_selected.connect(self._on_canvas_box_selected)
        splitter.addWidget(self._canvas)

        # Right panel
        right = QWidget()
        right.setMaximumWidth(300)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(10)

        # Field list
        fg = QGroupBox("Fields (draw a box, then label it)")
        fg_layout = QVBoxLayout(fg)

        self._field_list = QListWidget()
        self._field_list.setAlternatingRowColors(True)
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

        btn_row = QHBoxLayout()
        btn_rm = QPushButton("Remove Selected Box")
        btn_rm.setObjectName("btn_danger")
        btn_rm.clicked.connect(self._remove_selected)
        btn_row.addWidget(btn_rm)
        fg_layout.addLayout(btn_row)
        right_layout.addWidget(fg)

        # Row detection
        rd_group = QGroupBox("Row Detection")
        rd_form = QFormLayout(rd_group)
        rd_form.setSpacing(8)

        self._strategy_combo = QComboBox()
        self._strategy_combo.addItem("fixed_regions  — draw full columns (recommended)", "fixed_regions")
        self._strategy_combo.addItem("repeat_vertical  — draw one row, repeat at fixed height", "repeat_vertical")
        rd_form.addRow("Strategy:", self._strategy_combo)

        self._row_height = QDoubleSpinBox()
        self._row_height.setRange(2.0, 500.0)
        self._row_height.setValue(12.0)
        self._row_height.setSuffix(" px")
        rd_form.addRow("Row height:", self._row_height)

        self._start_y = QDoubleSpinBox()
        self._start_y.setRange(0.0, 99999.0)
        self._start_y.setValue(0.0)
        self._start_y.setSuffix(" px")
        rd_form.addRow("Start Y:", self._start_y)

        self._end_y = QDoubleSpinBox()
        self._end_y.setRange(0.0, 99999.0)
        self._end_y.setValue(800.0)
        self._end_y.setSuffix(" px")
        rd_form.addRow("End Y:", self._end_y)

        right_layout.addWidget(rd_group)

        # Template name + save
        save_group = QGroupBox("Save")
        save_layout = QVBoxLayout(save_group)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. Chase Checking 2024")
        save_layout.addWidget(QLabel("Template name:"))
        save_layout.addWidget(self._name_edit)

        btn_save = QPushButton("Save Template")
        btn_save.setObjectName("btn_primary")
        btn_save.clicked.connect(self._save_template)
        save_layout.addWidget(btn_save)
        right_layout.addWidget(save_group)

        right_layout.addStretch()
        splitter.addWidget(right)
        splitter.setSizes([900, 280])
        root.addWidget(splitter)

    # ── File open ─────────────────────────────────────────────────────────────

    def _open_file(self, path: str = ""):
        if not path:
            start_dir = Path(__file__).parent.parent / "input_files"
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
        dlg = _FieldNameDialog(PRESET_FIELDS, self)
        if dlg.exec():
            name = dlg.chosen_name()
            if name:
                self._canvas.add_named_box(
                    rect, name,
                    repeat=dlg.repeat(),
                    sub_group=dlg.sub_group(),
                )
                self._refresh_field_list()
        # If cancelled, box is discarded (not added to canvas)

    def _on_box_removed(self, index: int):
        self._refresh_field_list()

    def _remove_selected(self):
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
        """Update repeat + sub_group checkboxes from the selected box state."""
        defs = self._canvas.get_field_defs()
        has = 0 <= index < len(defs)
        for cb, key in ((self._repeat_check, "repeat"), (self._subgroup_check, "sub_group")):
            cb.blockSignals(True)
            cb.setChecked(defs[index].get(key, False) if has else False)
            cb.setEnabled(has)
            cb.blockSignals(False)

    # keep old name as alias so nothing else breaks
    def _sync_repeat_checkbox(self, index: int):
        self._sync_field_checkboxes(index)

    def _on_repeat_toggled(self, state: int):
        index = self._field_list.currentRow()
        if index < 0:
            return
        self._canvas.set_box_repeat(index, bool(state))
        # turning on repeat disables sub_group (mutually exclusive)
        if state:
            self._subgroup_check.blockSignals(True)
            self._subgroup_check.setChecked(False)
            self._subgroup_check.blockSignals(False)
        self._refresh_field_list()

    def _on_subgroup_toggled(self, state: int):
        index = self._field_list.currentRow()
        if index < 0:
            return
        self._canvas.set_box_sub_group(index, bool(state))
        # turning on sub_group disables repeat (mutually exclusive)
        if state:
            self._repeat_check.blockSignals(True)
            self._repeat_check.setChecked(False)
            self._repeat_check.blockSignals(False)
        self._refresh_field_list()

    def _refresh_field_list(self):
        row = self._field_list.currentRow()
        self._field_list.blockSignals(True)
        self._field_list.clear()
        for f in self._canvas.get_field_defs():
            bbox = f["bbox"]
            if f.get("sub_group"):
                prefix = "⊞ "
            elif f.get("repeat"):
                prefix = "↺ "
            else:
                prefix = "   "
            text = f"{prefix}{f['name']}  [{bbox[0]:.0f},{bbox[1]:.0f}  →  {bbox[2]:.0f},{bbox[3]:.0f}]"
            self._field_list.addItem(QListWidgetItem(text))
        self._field_list.blockSignals(False)
        if row >= 0:
            self._field_list.setCurrentRow(row)

    # ── Template CRUD ─────────────────────────────────────────────────────────

    def _refresh_template_list(self):
        self._tpl_combo.blockSignals(True)
        self._tpl_combo.clear()
        self._tpl_combo.addItem("— New template —", None)
        for t in list_templates():
            self._tpl_combo.addItem(t["name"], t["slug"])
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

        # Populate settings
        self._name_edit.setText(tpl.get("name", ""))
        rd = tpl.get("row_detection", {})
        strategy = rd.get("strategy", "fixed_regions")
        idx = self._strategy_combo.findData(strategy)
        if idx >= 0:
            self._strategy_combo.setCurrentIndex(idx)
        self._row_height.setValue(float(rd.get("row_height_pts", 12.0)))
        self._start_y.setValue(float(rd.get("start_y_pts", 0.0)))
        self._end_y.setValue(float(rd.get("end_y_pts", 800.0)))

        # Always show field list from template data
        self._refresh_field_list_from_template(tpl)

        # Auto-load the sample image stored in the template (if still accessible)
        saved_path = tpl.get("sample_image_path", "")
        if saved_path and Path(saved_path).exists() and saved_path != self._source_path:
            self._open_file(saved_path)
        else:
            # Draw boxes onto whichever image is already open
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
        self._tpl_combo.setCurrentIndex(0)
        self._tpl_combo.blockSignals(False)
        self._name_edit.clear()
        self._current_tpl = None
        self._source_img = None
        self._source_path = ""
        self._source_filename = ""
        self._canvas.clear_image()
        self._refresh_field_list()
        for cb in (self._repeat_check, self._subgroup_check):
            cb.setChecked(False)
            cb.setEnabled(False)

    def _delete_template(self):
        slug = self._tpl_combo.currentData()
        if not slug:
            QMessageBox.information(self, "Delete", "No saved template selected.")
            return
        name = self._tpl_combo.currentText()
        reply = QMessageBox.question(
            self, "Delete Template",
            f"Delete template '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_template(slug)
            self._refresh_template_list()
            self.status_message.emit(f"Deleted template '{name}'")

    def _save_template(self):
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Save Template", "Please enter a template name.")
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

        tpl = build_template(
            name=name,
            page_width_pts=w,
            page_height_pts=h,
            fields=fields,
            row_detection=rd,
            sample_image_path=self._source_path,
        )
        slug = save_template(tpl)
        self._refresh_template_list()

        # Select the just-saved template in the combo
        idx = self._tpl_combo.findData(slug)
        if idx >= 0:
            self._tpl_combo.setCurrentIndex(idx)

        self.status_message.emit(f"Saved template '{name}'")
        QMessageBox.information(self, "Saved", f"Template '{name}' saved with {len(fields)} field(s).")


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

        # mutually exclusive
        self._repeat_chk.toggled.connect(lambda on: self._subgroup_chk.setEnabled(not on))
        self._subgroup_chk.toggled.connect(lambda on: self._repeat_chk.setEnabled(not on))

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
