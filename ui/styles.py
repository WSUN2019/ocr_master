"""
OCR Master — dark fintech theme.

Palette:
  Deep bg   #080c14     Base bg   #0d1321     Surface   #162032
  Elevated  #1e2d45     Border    #253449     Border+   #2f4262
  Primary   #3b82f6     Primary+  #60a5fa     Dim blue  #1e3a5f
  Success   #10b981     Danger    #ef4444     Warn      #f59e0b
  Text      #e2e8f0     Text2     #94a3b8     Muted     #4b5563
"""

DARK_THEME = """

/* ── Base ──────────────────────────────────────────────────────────── */
QMainWindow, QDialog {
    background-color: #080c14;
    color: #e2e8f0;
    font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
    font-size: 13px;
}

QWidget {
    background-color: #0d1321;
    color: #e2e8f0;
    font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
    font-size: 13px;
}

/* ── Sidebar ────────────────────────────────────────────────────────── */
#sidebar {
    background-color: #080c14;
    border-right: 1px solid #1e2d45;
    min-width: 190px;
    max-width: 190px;
}

#app_title {
    color: #60a5fa;
    font-size: 15px;
    font-weight: bold;
    letter-spacing: 1px;
    padding: 22px 16px 14px 20px;
}

#sidebar QPushButton {
    background-color: transparent;
    color: #64748b;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0px;
    padding: 13px 16px 13px 17px;
    text-align: left;
    font-size: 13px;
}

#sidebar QPushButton:hover {
    background-color: #162032;
    color: #94a3b8;
    border-left: 3px solid #2f4262;
}

#sidebar QPushButton[active="true"] {
    background-color: #1e3a5f;
    color: #60a5fa;
    border-left: 3px solid #3b82f6;
    font-weight: bold;
}

/* ── Content ────────────────────────────────────────────────────────── */
#content {
    background-color: #0d1321;
}

/* ── Section titles ─────────────────────────────────────────────────── */
QLabel#section_title {
    font-size: 18px;
    font-weight: bold;
    color: #e2e8f0;
    padding-bottom: 2px;
}

/* ── Group boxes ────────────────────────────────────────────────────── */
QGroupBox {
    background-color: #162032;
    border: 1px solid #253449;
    border-radius: 8px;
    margin-top: 14px;
    padding: 12px 10px 10px 10px;
    font-weight: 600;
    font-size: 12px;
    color: #60a5fa;
    letter-spacing: 0.5px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: #162032;
    text-transform: uppercase;
}

/* ── Buttons ────────────────────────────────────────────────────────── */
QPushButton {
    background-color: #1e2d45;
    color: #94a3b8;
    border: 1px solid #2f4262;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 13px;
    min-height: 28px;
}

QPushButton:hover {
    background-color: #253449;
    color: #e2e8f0;
    border-color: #3b82f6;
}

QPushButton:pressed {
    background-color: #1e3a5f;
    color: #60a5fa;
}

QPushButton:disabled {
    background-color: #0d1321;
    color: #253449;
    border-color: #1e2d45;
}

QPushButton#btn_primary {
    background-color: #2563eb;
    border-color: #3b82f6;
    color: #ffffff;
    font-weight: bold;
}

QPushButton#btn_primary:hover {
    background-color: #3b82f6;
    border-color: #60a5fa;
}

QPushButton#btn_primary:pressed {
    background-color: #1d4ed8;
}

QPushButton#btn_danger {
    background-color: #2d1515;
    border-color: #7f1d1d;
    color: #fca5a5;
}

QPushButton#btn_danger:hover {
    background-color: #7f1d1d;
    border-color: #ef4444;
    color: #ffffff;
}

/* ── Inputs ─────────────────────────────────────────────────────────── */
QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #0d1321;
    border: 1px solid #253449;
    border-radius: 6px;
    padding: 6px 10px;
    color: #e2e8f0;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    min-height: 26px;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #3b82f6;
    background-color: #0a1020;
}

QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: #2f4262;
}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background-color: #1e2d45;
    border: none;
    width: 18px;
    border-radius: 3px;
}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #2f4262;
}

/* ── Combo boxes ────────────────────────────────────────────────────── */
QComboBox {
    background-color: #0d1321;
    border: 1px solid #253449;
    border-radius: 6px;
    padding: 6px 10px;
    color: #e2e8f0;
    min-height: 26px;
    selection-background-color: #2563eb;
}

QComboBox:hover {
    border-color: #2f4262;
}

QComboBox:focus {
    border-color: #3b82f6;
}

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
    background-color: #162032;
    border: 1px solid #2f4262;
    border-radius: 6px;
    selection-background-color: #1e3a5f;
    selection-color: #60a5fa;
    color: #e2e8f0;
    padding: 4px;
    outline: none;
}

/* ── Date edit ──────────────────────────────────────────────────────── */
QDateEdit {
    background-color: #0d1321;
    border: 1px solid #253449;
    border-radius: 6px;
    padding: 6px 10px;
    color: #e2e8f0;
    min-height: 26px;
}

QDateEdit:focus { border-color: #3b82f6; }
QDateEdit:hover { border-color: #2f4262; }

QDateEdit::drop-down {
    border: none;
    width: 24px;
}

QCalendarWidget {
    background-color: #162032;
    color: #e2e8f0;
    border: 1px solid #2f4262;
    border-radius: 8px;
}

QCalendarWidget QAbstractItemView {
    background-color: #162032;
    selection-background-color: #2563eb;
    selection-color: white;
    color: #e2e8f0;
}

QCalendarWidget QWidget#qt_calendar_navigationbar {
    background-color: #1e2d45;
    border-radius: 6px;
}

/* ── Checkboxes ─────────────────────────────────────────────────────── */
QCheckBox {
    color: #94a3b8;
    spacing: 8px;
}

QCheckBox:hover { color: #e2e8f0; }

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #2f4262;
    border-radius: 4px;
    background-color: #0d1321;
}

QCheckBox::indicator:hover {
    border-color: #3b82f6;
}

QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #3b82f6;
}

/* ── Tables ─────────────────────────────────────────────────────────── */
QTableView {
    background-color: #0d1321;
    alternate-background-color: #111b2e;
    border: 1px solid #1e2d45;
    border-radius: 8px;
    gridline-color: #1e2d45;
    color: #e2e8f0;
    selection-background-color: #1e3a5f;
    selection-color: #e2e8f0;
    outline: none;
}

QTableView::item {
    padding: 4px 8px;
    border: none;
}

QTableView::item:selected {
    background-color: #1e3a5f;
    color: #60a5fa;
}

QTableView::item:hover {
    background-color: #162032;
}

QHeaderView {
    background-color: #162032;
    border: none;
}

QHeaderView::section {
    background-color: #162032;
    color: #60a5fa;
    padding: 8px 10px;
    border: none;
    border-right: 1px solid #1e2d45;
    border-bottom: 2px solid #2563eb;
    font-weight: 600;
    font-size: 12px;
    letter-spacing: 0.3px;
    text-transform: uppercase;
}

QHeaderView::section:hover {
    background-color: #1e2d45;
    color: #93c5fd;
}

QHeaderView::section:pressed {
    background-color: #1e3a5f;
}

/* ── List widget ────────────────────────────────────────────────────── */
QListWidget {
    background-color: #0d1321;
    border: 1px solid #1e2d45;
    border-radius: 6px;
    color: #e2e8f0;
    outline: none;
}

QListWidget::item {
    padding: 6px 10px;
    border-radius: 4px;
}

QListWidget::item:selected {
    background-color: #1e3a5f;
    color: #60a5fa;
}

QListWidget::item:hover {
    background-color: #162032;
}

/* ── Scroll bars ────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background: #253449;
    border-radius: 4px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: #3b82f6;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 2px;
}

QScrollBar::handle:horizontal {
    background: #253449;
    border-radius: 4px;
    min-width: 24px;
}

QScrollBar::handle:horizontal:hover {
    background: #3b82f6;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QScrollBar::corner {
    background: transparent;
}

/* ── Progress bar ───────────────────────────────────────────────────── */
QProgressBar {
    background-color: #1e2d45;
    border: none;
    border-radius: 5px;
    text-align: center;
    color: #e2e8f0;
    font-size: 12px;
    height: 20px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #2563eb, stop:1 #3b82f6);
    border-radius: 5px;
}

/* ── Splitter ───────────────────────────────────────────────────────── */
QSplitter::handle {
    background-color: #1e2d45;
}

QSplitter::handle:horizontal { width: 3px; }
QSplitter::handle:vertical   { height: 3px; }

QSplitter::handle:hover {
    background-color: #3b82f6;
}

/* ── Status bar ─────────────────────────────────────────────────────── */
QStatusBar {
    background-color: #080c14;
    color: #4b5563;
    border-top: 1px solid #1e2d45;
    font-size: 12px;
    padding: 2px 8px;
}

QStatusBar::item { border: none; }

/* ── Tooltips ───────────────────────────────────────────────────────── */
QToolTip {
    background-color: #1e2d45;
    color: #e2e8f0;
    border: 1px solid #2f4262;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}

/* ── Dialogs ────────────────────────────────────────────────────────── */
QDialog {
    background-color: #0d1321;
    border: 1px solid #253449;
    border-radius: 8px;
}

QDialogButtonBox QPushButton {
    min-width: 80px;
}

/* ── Message boxes ──────────────────────────────────────────────────── */
QMessageBox {
    background-color: #0d1321;
}

QMessageBox QLabel {
    color: #e2e8f0;
}

"""
