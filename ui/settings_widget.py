"""
Settings page — manage templates, database maintenance, Tesseract path.
"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QListWidget, QListWidgetItem, QTextEdit,
    QFileDialog, QMessageBox, QLineEdit, QFormLayout
)

from core.storage import vacuum_db, db_size_mb, init_db, DB_PATH
from core.template import list_templates, load_template, delete_template, save_template


class SettingsWidget(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        init_db()
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        title = QLabel("Settings")
        title.setObjectName("section_title")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        root.addWidget(title)

        # ── Template management ───────────────────────────────────────────────
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

        # Template detail
        right = QVBoxLayout()
        right.addWidget(QLabel("Template JSON:"))
        self._tpl_detail = QTextEdit()
        self._tpl_detail.setReadOnly(True)
        self._tpl_detail.setFont(QFont("Courier New", 11))
        right.addWidget(self._tpl_detail)
        tpl_layout.addLayout(right, 2)

        root.addWidget(tpl_group)

        # ── Tesseract path (Windows) ──────────────────────────────────────────
        ocr_group = QGroupBox("Tesseract OCR Path (Windows only)")
        ocr_form = QFormLayout(ocr_group)
        self._tess_path = QLineEdit()
        self._tess_path.setPlaceholderText(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        ocr_form.addRow("Tesseract exe:", self._tess_path)

        btn_tess_browse = QPushButton("Browse…")
        btn_tess_browse.clicked.connect(self._browse_tesseract)
        ocr_form.addRow("", btn_tess_browse)

        btn_tess_test = QPushButton("Test Tesseract")
        btn_tess_test.clicked.connect(self._test_tesseract)
        ocr_form.addRow("", btn_tess_test)
        root.addWidget(ocr_group)

        # ── Database ──────────────────────────────────────────────────────────
        db_group = QGroupBox("Database")
        db_layout = QVBoxLayout(db_group)

        self._db_size_lbl = QLabel()
        db_layout.addWidget(self._db_size_lbl)

        db_path_lbl = QLabel(f"Location: {DB_PATH}")
        db_path_lbl.setStyleSheet("color: #a0a0b0; font-size: 11px;")
        db_path_lbl.setWordWrap(True)
        db_layout.addWidget(db_path_lbl)

        btn_row2 = QHBoxLayout()
        btn_vacuum = QPushButton("Compact Database (VACUUM)")
        btn_vacuum.clicked.connect(self._vacuum)
        btn_row2.addWidget(btn_vacuum)

        btn_backup = QPushButton("Backup Database…")
        btn_backup.setObjectName("btn_primary")
        btn_backup.clicked.connect(self._backup_db)
        btn_row2.addWidget(btn_backup)

        btn_row2.addStretch()
        db_layout.addLayout(btn_row2)
        root.addWidget(db_group)

        root.addStretch()
        self._refresh_templates()

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_templates()
        self._db_size_lbl.setText(f"Size: {db_size_mb():.3f} MB")

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
        slug = item.data(256)
        tpl = load_template(slug)
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

    def _import_template(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Template", str(Path.home()), "JSON (*.json)"
        )
        if not path:
            return
        try:
            tpl = json.loads(Path(path).read_text())
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
        slug = item.data(256)
        name = item.text()
        reply = QMessageBox.question(
            self, "Delete Template", f"Delete '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_template(slug)
            self._refresh_templates()
            self._tpl_detail.clear()

    # ── Tesseract ─────────────────────────────────────────────────────────────

    def _browse_tesseract(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Find tesseract.exe",
            r"C:\Program Files\Tesseract-OCR",
            "Executable (*.exe)"
        )
        if path:
            self._tess_path.setText(path)

    def _test_tesseract(self):
        import pytesseract
        custom = self._tess_path.text().strip()
        if custom:
            pytesseract.pytesseract.tesseract_cmd = custom
        try:
            ver = pytesseract.get_tesseract_version()
            QMessageBox.information(self, "Tesseract OK", f"Tesseract version: {ver}")
            self.status_message.emit(f"Tesseract {ver} found")
        except Exception as e:
            QMessageBox.critical(self, "Tesseract Not Found",
                f"Could not run Tesseract:\n{e}\n\n"
                "Linux: sudo apt install tesseract-ocr\n"
                "Windows: install from https://github.com/UB-Mannheim/tesseract/wiki")

    # ── Database ──────────────────────────────────────────────────────────────

    def _vacuum(self):
        vacuum_db()
        self._db_size_lbl.setText(f"Size: {db_size_mb():.3f} MB")
        self.status_message.emit("Database compacted")
        QMessageBox.information(self, "VACUUM", "Database compacted successfully.")

    def _backup_db(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Backup Database", str(Path.home() / "ocr_master_backup.db"),
            "SQLite (*.db)"
        )
        if path and DB_PATH.exists():
            import shutil
            shutil.copy2(DB_PATH, path)
            self.status_message.emit(f"Database backed up to {Path(path).name}")
            QMessageBox.information(self, "Backup", f"Database backed up to:\n{path}")
