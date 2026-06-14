"""
OCR Master — light theme.

Palette:
  Page bg   #f1f5f9     Surface   #ffffff     Surface+  #f8fafc
  Border    #e2e8f0     Border+   #cbd5e1     Divider   #e2e8f0
  Primary   #2563eb     Primary+  #3b82f6     Primary-  #1d4ed8
  Sidebar   #1e3a5f     SidebarT  #ffffff     SidebarM  #93c5fd
  Text      #1e293b     Text2     #475569     Muted     #94a3b8
  Success   #059669     Danger    #dc2626     Warn      #d97706

Dark theme backup: docs/styles_dark.py
"""

DARK_THEME = """

/* ── Base ──────────────────────────────────────────────────────────── */
QMainWindow, QDialog {
    background-color: #f1f5f9;
    color: #1e293b;
    font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
    font-size: 13px;
}

QWidget {
    background-color: #f1f5f9;
    color: #1e293b;
    font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
    font-size: 13px;
}

/* ── Sidebar ────────────────────────────────────────────────────────── */
#sidebar {
    background-color: #1e3a5f;
    border-right: 1px solid #162f4e;
    min-width: 190px;
    max-width: 190px;
}

#sidebar QWidget, #sidebar QLabel {
    background-color: transparent;
    color: #93c5fd;
}

#app_title {
    color: #ffffff;
    font-size: 15px;
    font-weight: bold;
    letter-spacing: 1px;
    padding: 22px 16px 14px 20px;
    background-color: transparent;
}

#sidebar QPushButton {
    background-color: transparent;
    color: #93c5fd;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0px;
    padding: 13px 16px 13px 17px;
    text-align: left;
    font-size: 13px;
}

#sidebar QPushButton:hover {
    background-color: #1e4976;
    color: #dbeafe;
    border-left: 3px solid #60a5fa;
}

#sidebar QPushButton[active="true"] {
    background-color: #1d4ed8;
    color: #ffffff;
    border-left: 3px solid #93c5fd;
    font-weight: bold;
}

/* ── Content area ───────────────────────────────────────────────────── */
#content {
    background-color: #f1f5f9;
}

/* ── Section titles ─────────────────────────────────────────────────── */
QLabel#section_title {
    font-size: 18px;
    font-weight: bold;
    color: #1e293b;
    padding-bottom: 2px;
}

/* ── Group boxes ────────────────────────────────────────────────────── */
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    margin-top: 14px;
    padding: 12px 10px 10px 10px;
    font-weight: 600;
    font-size: 12px;
    color: #2563eb;
    letter-spacing: 0.3px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: #ffffff;
    text-transform: uppercase;
}

/* ── Buttons ────────────────────────────────────────────────────────── */
QPushButton {
    background-color: #ffffff;
    color: #475569;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 13px;
    min-height: 28px;
}

QPushButton:hover {
    background-color: #f8fafc;
    color: #1e293b;
    border-color: #94a3b8;
}

QPushButton:pressed {
    background-color: #e2e8f0;
    color: #1e293b;
}

QPushButton:disabled {
    background-color: #f8fafc;
    color: #cbd5e1;
    border-color: #e2e8f0;
}

QPushButton#btn_primary {
    background-color: #2563eb;
    border-color: #1d4ed8;
    color: #ffffff;
    font-weight: bold;
}

QPushButton#btn_primary:hover {
    background-color: #1d4ed8;
    border-color: #1e40af;
}

QPushButton#btn_primary:pressed {
    background-color: #1e40af;
}

QPushButton#btn_primary:disabled {
    background-color: #bfdbfe;
    border-color: #bfdbfe;
    color: #ffffff;
}

QPushButton#btn_danger {
    background-color: #fef2f2;
    border-color: #fecaca;
    color: #dc2626;
}

QPushButton#btn_danger:hover {
    background-color: #dc2626;
    border-color: #b91c1c;
    color: #ffffff;
}

/* ── Inputs ─────────────────────────────────────────────────────────── */
QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 10px;
    color: #1e293b;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    min-height: 26px;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #2563eb;
    background-color: #ffffff;
}

QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: #94a3b8;
}

QLineEdit:read-only {
    background-color: #f8fafc;
    color: #64748b;
}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background-color: #f1f5f9;
    border: none;
    width: 18px;
    border-radius: 3px;
}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #e2e8f0;
}

/* ── Combo boxes ────────────────────────────────────────────────────── */
QComboBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 10px;
    color: #1e293b;
    min-height: 26px;
    selection-background-color: #2563eb;
}

QComboBox:hover { border-color: #94a3b8; }
QComboBox:focus { border-color: #2563eb; }

QComboBox::drop-down {
    border: none;
    width: 24px;
    subcontrol-origin: padding;
    subcontrol-position: top right;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #64748b;
    width: 0;
    height: 0;
    margin-right: 6px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    selection-background-color: #eff6ff;
    selection-color: #2563eb;
    color: #1e293b;
    padding: 4px;
    outline: none;
}

/* ── Date edit ──────────────────────────────────────────────────────── */
QDateEdit {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 10px;
    color: #1e293b;
    min-height: 26px;
}

QDateEdit:focus { border-color: #2563eb; }
QDateEdit:hover { border-color: #94a3b8; }

QDateEdit::drop-down {
    border: none;
    width: 24px;
}

QCalendarWidget {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
}

QCalendarWidget QAbstractItemView {
    background-color: #ffffff;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    color: #1e293b;
}

QCalendarWidget QWidget#qt_calendar_navigationbar {
    background-color: #f1f5f9;
    border-radius: 6px;
}

/* ── Checkboxes ─────────────────────────────────────────────────────── */
QCheckBox {
    background-color: transparent;
    color: #475569;
    spacing: 8px;
}

QCheckBox:hover { color: #1e293b; }

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    background-color: #ffffff;
}

QCheckBox::indicator:hover { border-color: #2563eb; }

QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #1d4ed8;
}

/* ── Tables ─────────────────────────────────────────────────────────── */
QTableView {
    background-color: #ffffff;
    alternate-background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    gridline-color: #f1f5f9;
    color: #1e293b;
    selection-background-color: #eff6ff;
    selection-color: #1e40af;
    outline: none;
}

QTableView::item {
    padding: 4px 8px;
    border: none;
}

QTableView::item:selected {
    background-color: #eff6ff;
    color: #1e40af;
}

QTableView::item:hover {
    background-color: #f0f9ff;
}

QHeaderView {
    background-color: #f8fafc;
    border: none;
}

QHeaderView::section {
    background-color: #f8fafc;
    color: #2563eb;
    padding: 8px 10px;
    border: none;
    border-right: 1px solid #e2e8f0;
    border-bottom: 2px solid #2563eb;
    font-weight: 600;
    font-size: 12px;
    letter-spacing: 0.3px;
    text-transform: uppercase;
}

QHeaderView::section:hover {
    background-color: #eff6ff;
    color: #1d4ed8;
}

QHeaderView::section:pressed {
    background-color: #dbeafe;
}

/* ── List widget ────────────────────────────────────────────────────── */
QListWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    color: #1e293b;
    outline: none;
}

QListWidget::item {
    padding: 6px 10px;
    border-radius: 4px;
    color: #1e293b;
}

QListWidget::item:alternate {
    background-color: #f8fafc;
    color: #1e293b;
}

QListWidget::item:selected {
    background-color: #eff6ff;
    color: #2563eb;
}

QListWidget::item:hover {
    background-color: #f0f9ff;
}

/* ── Scroll bars ────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 4px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover { background: #2563eb; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 2px;
}

QScrollBar::handle:horizontal {
    background: #cbd5e1;
    border-radius: 4px;
    min-width: 24px;
}

QScrollBar::handle:horizontal:hover { background: #2563eb; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::corner { background: transparent; }

/* ── Progress bar ───────────────────────────────────────────────────── */
QProgressBar {
    background-color: #e2e8f0;
    border: none;
    border-radius: 5px;
    text-align: center;
    color: #1e293b;
    font-size: 12px;
    height: 20px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #2563eb, stop:1 #3b82f6);
    border-radius: 5px;
}

/* ── Labels — transparent so they inherit parent surface color ───────── */
QLabel {
    background-color: transparent;
}

/* ── Scroll area ────────────────────────────────────────────────────── */
QScrollArea {
    background-color: #ffffff;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background-color: #ffffff;
}

/* ── Splitter ───────────────────────────────────────────────────────── */
QSplitter::handle { background-color: #e2e8f0; }
QSplitter::handle:horizontal { width: 3px; }
QSplitter::handle:vertical   { height: 3px; }
QSplitter::handle:hover      { background-color: #2563eb; }

/* ── Status bar ─────────────────────────────────────────────────────── */
QStatusBar {
    background-color: #1e3a5f;
    color: #93c5fd;
    border-top: 1px solid #1e3a5f;
    font-size: 12px;
    padding: 2px 8px;
}

QStatusBar::item { border: none; }

/* ── Tooltips ───────────────────────────────────────────────────────── */
QToolTip {
    background-color: #1e293b;
    color: #f1f5f9;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}

/* ── Dialogs ────────────────────────────────────────────────────────── */
QDialog {
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
}

QDialogButtonBox QPushButton { min-width: 80px; }

/* ── Message boxes ──────────────────────────────────────────────────── */
QMessageBox {
    background-color: #ffffff;
}

QMessageBox QLabel {
    color: #1e293b;
}

/* ── Text edit (log areas) ──────────────────────────────────────────── */
QTextEdit {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

"""
