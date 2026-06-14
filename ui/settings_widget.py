"""
Settings page — manage templates, all configurable paths, and database maintenance.
"""
import json
import os
import sys
from pathlib import Path

from PyQt6.QtCore import pyqtSignal, QUrl
from PyQt6.QtGui import QFont, QDesktopServices
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QListWidget, QListWidgetItem, QTextEdit,
    QFileDialog, QMessageBox, QLineEdit, QFormLayout, QScrollArea,
    QFrame, QSizePolicy
)

from core.storage import vacuum_db, wipe_db, db_size_mb, init_db
from core.template import list_templates, load_template, delete_template, save_template
from core.config import get_config


class SettingsWidget(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        init_db()
        self._path_edits: dict[str, QLineEdit] = {}
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        root = QVBoxLayout(content)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        title = QLabel("Settings")
        title.setObjectName("section_title")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        root.addWidget(title)

        root.addWidget(self._build_templates_group())
        root.addWidget(self._build_paths_group())
        root.addWidget(self._build_database_group())
        root.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

    # ── Template management ───────────────────────────────────────────────────

    def _build_templates_group(self) -> QGroupBox:
        tpl_group = QGroupBox("Templates")
        tpl_layout = QHBoxLayout(tpl_group)

        left = QVBoxLayout()
        self._tpl_list = QListWidget()
        self._tpl_list.currentRowChanged.connect(self._on_template_selected)
        left.addWidget(self._tpl_list)

        btn_row = QHBoxLayout()
        btn_export_tpl = QPushButton("Export JSON")
        btn_export_tpl.clicked.connect(self._export_template)
        btn_row.addWidget(btn_export_tpl)

        btn_import_tpl = QPushButton("Import JSON")
        btn_import_tpl.clicked.connect(self._import_template)
        btn_row.addWidget(btn_import_tpl)

        btn_del_tpl = QPushButton("Delete")
        btn_del_tpl.setObjectName("btn_danger")
        btn_del_tpl.clicked.connect(self._delete_template)
        btn_row.addWidget(btn_del_tpl)

        left.addLayout(btn_row)
        tpl_layout.addLayout(left, 1)

        right = QVBoxLayout()
        right.addWidget(QLabel("Template JSON:"))
        self._tpl_detail = QTextEdit()
        self._tpl_detail.setReadOnly(True)
        self._tpl_detail.setFont(QFont("Courier New", 11))
        right.addWidget(self._tpl_detail)
        tpl_layout.addLayout(right, 2)

        return tpl_group

    # ── Paths ─────────────────────────────────────────────────────────────────

    def _build_paths_group(self) -> QGroupBox:
        group = QGroupBox("Paths & Locations")
        outer = QVBoxLayout(group)

        note = QLabel("Changes take effect immediately. Restart the app if the database path changes.")
        note.setStyleSheet("color: #64748b; font-size: 11px;")
        note.setWordWrap(True)
        outer.addWidget(note)

        form = QFormLayout()
        form.setLabelAlignment(form.labelAlignment())
        form.setSpacing(8)

        self._add_path_row(form, "Tesseract exe:",     "tesseract_path", is_file=True,  test_btn=True)
        self._add_path_row(form, "Database file:",     "db_path",        is_file=True)
        self._add_path_row(form, "Templates folder:",  "templates_dir",  is_file=False)
        self._add_path_row(form, "Input files:",       "input_dir",      is_file=False)
        self._add_path_row(form, "Output folder:",     "output_dir",     is_file=False)
        self._add_path_row(form, "Batch import:",      "batch_import_dir",   is_file=False)
        self._add_path_row(form, "Batch complete:",    "batch_complete_dir", is_file=False)

        btn_widget = QWidget()
        btn_widget.setAutoFillBackground(False)
        btn_lay = QHBoxLayout(btn_widget)
        btn_lay.setContentsMargins(0, 4, 0, 0)
        btn_lay.setSpacing(6)
        btn_lay.addStretch()

        btn_reset = QPushButton("Reset to Defaults")
        btn_reset.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn_reset.clicked.connect(self._reset_paths)
        btn_lay.addWidget(btn_reset)

        btn_save = QPushButton("Save All Paths")
        btn_save.setObjectName("btn_primary")
        btn_save.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn_save.clicked.connect(self._save_paths)
        btn_lay.addWidget(btn_save)

        form.addRow("", btn_widget)
        outer.addLayout(form)
        return group

    def _add_path_row(self, form: QFormLayout, label: str, key: str,
                      is_file: bool, test_btn: bool = False):
        edit = QLineEdit()
        edit.setMinimumWidth(120)
        edit.setMaximumWidth(360)
        self._path_edits[key] = edit

        row = QWidget()
        row.setAutoFillBackground(False)
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        lay.addWidget(edit, 1)

        btn_browse = QPushButton("Browse…")
        btn_browse.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        if is_file:
            btn_browse.clicked.connect(lambda _, e=edit, k=key: self._browse_file(e, k))
        else:
            btn_browse.clicked.connect(lambda _, e=edit: self._browse_folder(e))
        lay.addWidget(btn_browse)

        if test_btn:
            btn_test = QPushButton("Test")
            btn_test.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            btn_test.clicked.connect(self._test_tesseract)
            lay.addWidget(btn_test)
        else:
            btn_open = QPushButton("Open")
            btn_open.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            btn_open.clicked.connect(lambda _, e=edit: self._open_in_explorer(e.text()))
            lay.addWidget(btn_open)

        form.addRow(label, row)

    def _browse_file(self, edit: QLineEdit, key: str):
        current = edit.text().strip() or str(Path.home())
        if key == "tesseract_path":
            path, _ = QFileDialog.getOpenFileName(
                self, "Find tesseract.exe", current, "Executable (*.exe)"
            )
        elif key == "db_path":
            path, _ = QFileDialog.getSaveFileName(
                self, "Database file location", current, "SQLite DB (*.db)"
            )
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Select file", current, "All files (*)")
        if path:
            edit.setText(path)

    def _browse_folder(self, edit: QLineEdit):
        current = edit.text().strip() or str(Path.home())
        path = QFileDialog.getExistingDirectory(self, "Select Folder", current)
        if path:
            edit.setText(path)

    def _open_in_explorer(self, path_str: str):
        if not path_str.strip():
            return
        p = Path(path_str.strip())
        target = p.parent if p.is_file() else p
        target.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    def _save_paths(self):
        cfg = get_config()
        updates = {key: edit.text().strip() for key, edit in self._path_edits.items()
                   if edit.text().strip()}
        cfg.update_many(updates)

        # Apply tesseract change immediately
        if "tesseract_path" in updates and sys.platform == "win32":
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = updates["tesseract_path"]

        # Ensure all folder paths exist
        for key in ("templates_dir", "input_dir", "output_dir",
                    "batch_import_dir", "batch_complete_dir"):
            if key in updates:
                Path(updates[key]).mkdir(parents=True, exist_ok=True)

        # Ensure DB schema exists at new location
        if "db_path" in updates:
            Path(updates["db_path"]).parent.mkdir(parents=True, exist_ok=True)
            init_db()

        self.status_message.emit("Paths saved")
        QMessageBox.information(self, "Saved", "All paths have been saved.")

    def _reset_paths(self):
        reply = QMessageBox.question(
            self, "Reset Paths",
            "Reset all paths to their defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        get_config().reset_to_defaults()
        self._load_paths_into_ui()
        self.status_message.emit("Paths reset to defaults")

    def _test_tesseract(self):
        import pytesseract
        custom = self._path_edits["tesseract_path"].text().strip()
        if custom:
            pytesseract.pytesseract.tesseract_cmd = custom
        try:
            ver = pytesseract.get_tesseract_version()
            if custom:
                get_config().set("tesseract_path", custom)
            QMessageBox.information(self, "Tesseract OK", f"Tesseract version: {ver}")
            self.status_message.emit(f"Tesseract {ver} found")
        except Exception as e:
            QMessageBox.critical(
                self, "Tesseract Not Found",
                f"Could not run Tesseract:\n{e}\n\n"
                "Linux: sudo apt install tesseract-ocr\n"
                "Windows: https://github.com/UB-Mannheim/tesseract/wiki"
            )

    # ── Database maintenance ──────────────────────────────────────────────────

    def _build_database_group(self) -> QGroupBox:
        db_group = QGroupBox("Database")
        db_layout = QVBoxLayout(db_group)

        self._db_size_lbl = QLabel()
        db_layout.addWidget(self._db_size_lbl)

        self._db_path_lbl = QLabel()
        self._db_path_lbl.setStyleSheet("color: #a0a0b0; font-size: 11px;")
        self._db_path_lbl.setWordWrap(True)
        db_layout.addWidget(self._db_path_lbl)

        btn_row1 = QHBoxLayout()
        btn_vacuum = QPushButton("Compact (VACUUM)")
        btn_vacuum.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn_vacuum.clicked.connect(self._vacuum)
        btn_row1.addWidget(btn_vacuum)

        btn_backup = QPushButton("Backup Database + Templates…")
        btn_backup.setObjectName("btn_primary")
        btn_backup.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn_backup.clicked.connect(self._backup_db)
        btn_row1.addWidget(btn_backup)
        btn_row1.addStretch()
        db_layout.addLayout(btn_row1)

        btn_row = QHBoxLayout()
        btn_wipe = QPushButton("Delete Database Only…")
        btn_wipe.setObjectName("btn_danger")
        btn_wipe.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn_wipe.setToolTip("Permanently delete every transaction and import log")
        btn_wipe.clicked.connect(self._wipe_db)
        btn_row.addWidget(btn_wipe)

        btn_wipe_all = QPushButton("Delete Everything (Database + Templates)…")
        btn_wipe_all.setObjectName("btn_danger")
        btn_wipe_all.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn_wipe_all.setToolTip("Permanently delete all transactions AND all saved templates")
        btn_wipe_all.clicked.connect(self._wipe_all)
        btn_row.addWidget(btn_wipe_all)

        btn_row.addStretch()
        db_layout.addLayout(btn_row)
        return db_group

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def refresh(self):
        self._refresh_templates()
        self._refresh_db_info()
        self._load_paths_into_ui()

    def _load_paths_into_ui(self):
        cfg = get_config()
        data = cfg.as_dict()
        for key, edit in self._path_edits.items():
            edit.setText(data.get(key, ""))

    def _refresh_db_info(self):
        cfg = get_config()
        self._db_size_lbl.setText(f"Size: {db_size_mb():.3f} MB")
        self._db_path_lbl.setText(f"Location: {cfg.db_path}")

    # ── Templates ─────────────────────────────────────────────────────────────

    def _refresh_templates(self):
        self._tpl_list.clear()
        for t in list_templates():
            item = QListWidgetItem(f"{t['name']}  [{t['slug']}]")
            item.setData(256, t["slug"])
            self._tpl_list.addItem(item)

    def _on_template_selected(self, row: int):
        item = self._tpl_list.item(row)
        if not item:
            return
        tpl = load_template(item.data(256))
        if tpl:
            self._tpl_detail.setPlainText(json.dumps(tpl, indent=2))

    def _export_template(self):
        item = self._tpl_list.currentItem()
        if not item:
            QMessageBox.information(self, "Export", "Select a template first.")
            return
        slug = item.data(256)
        tpl = load_template(slug)
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Template", str(Path.home() / f"{slug}.json"), "JSON (*.json)"
        )
        if path:
            Path(path).write_text(json.dumps(tpl, indent=2))
            self.status_message.emit(f"Exported template to {Path(path).name}")

    def _validate_template(self, tpl: dict):
        if not isinstance(tpl, dict):
            raise ValueError("Template must be a JSON object.")
        if not tpl.get("name"):
            raise ValueError("Template is missing a 'name' field.")
        fields = tpl.get("fields")
        if not isinstance(fields, list) or len(fields) == 0:
            raise ValueError("Template must have at least one field in 'fields'.")
        for f in fields:
            if "name" not in f:
                raise ValueError("A field is missing a 'name' key.")
            if "bbox" not in f:
                raise ValueError(f"Field '{f.get('name')}' is missing a 'bbox' key.")
            if not isinstance(f["bbox"], (list, tuple)) or len(f["bbox"]) != 4:
                raise ValueError(f"Field '{f.get('name')}' bbox must be a list of 4 numbers.")

    def _import_template(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Template", str(Path.home()), "JSON (*.json)"
        )
        if not path:
            return
        try:
            tpl = json.loads(Path(path).read_text())
            self._validate_template(tpl)
            slug = save_template(tpl)
            self._refresh_templates()
            self.status_message.emit(f"Imported template '{tpl.get('name', slug)}'")
            QMessageBox.information(self, "Imported", f"Template '{tpl.get('name', slug)}' imported.")
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", str(e))

    def _delete_template(self):
        item = self._tpl_list.currentItem()
        if not item:
            return
        reply = QMessageBox.question(
            self, "Delete Template", f"Delete '{item.text()}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_template(item.data(256))
            self._tpl_list.blockSignals(True)
            self._refresh_templates()
            self._tpl_list.blockSignals(False)
            self._tpl_list.setCurrentRow(-1)
            self._tpl_detail.clear()

    # ── Database maintenance ──────────────────────────────────────────────────

    def _vacuum(self):
        vacuum_db()
        self._refresh_db_info()
        self.status_message.emit("Database compacted")
        QMessageBox.information(self, "VACUUM", "Database compacted successfully.")

    def _wipe_db(self):
        reply = QMessageBox.warning(
            self, "Delete Database",
            "This will permanently delete ALL transactions and import logs.\n\n"
            "This cannot be undone. Back up the database first if needed.\n\n"
            "Are you absolutely sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "Confirm Delete", "Type  DELETE  to confirm:")
        if not ok or text.strip().upper() != "DELETE":
            QMessageBox.information(self, "Cancelled", "Database was not deleted.")
            return
        wipe_db()
        self._refresh_db_info()
        self.status_message.emit("Database deleted — all transactions removed")
        QMessageBox.information(self, "Done", "All transactions and import logs have been deleted.")

    def _wipe_all(self):
        reply = QMessageBox.warning(
            self, "Wipe All Data",
            "This will permanently delete ALL transactions, import logs AND every saved template.\n\n"
            "This cannot be undone.\n\n"
            "Are you absolutely sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "Confirm Wipe All", "Type  WIPE  to confirm:")
        if not ok or text.strip().upper() != "WIPE":
            QMessageBox.information(self, "Cancelled", "Nothing was deleted.")
            return
        wipe_db()
        for json_file in get_config().templates_dir.glob("*.json"):
            try:
                json_file.unlink()
            except Exception:
                pass
        self._refresh_templates()
        self._tpl_detail.clear()
        self._refresh_db_info()
        self.status_message.emit("All data wiped — database and templates deleted")
        QMessageBox.information(self, "Done", "All transactions and templates have been deleted.")

    def _backup_db(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Backup (Database + Templates)",
            str(Path.home() / "ocr_master_backup.zip"),
            "ZIP archive (*.zip)"
        )
        if not path:
            return
        import zipfile
        cfg = get_config()
        try:
            with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                if cfg.db_path.exists():
                    zf.write(cfg.db_path, "ocr_master.db")
                if cfg.templates_dir.exists():
                    for tpl_file in cfg.templates_dir.glob("*.json"):
                        zf.write(tpl_file, f"templates/{tpl_file.name}")
            self.status_message.emit(f"Backup saved to {Path(path).name}")
            QMessageBox.information(self, "Backup", f"Database and templates backed up to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Backup Failed", str(e))
