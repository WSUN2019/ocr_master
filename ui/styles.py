DARK_THEME = """
QMainWindow, QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}

/* Sidebar */
#sidebar {
    background-color: #16213e;
    border-right: 1px solid #0f3460;
    min-width: 180px;
    max-width: 180px;
}

#sidebar QPushButton {
    background-color: transparent;
    color: #a0a0b0;
    border: none;
    border-radius: 6px;
    padding: 12px 16px;
    text-align: left;
    font-size: 13px;
}

#sidebar QPushButton:hover {
    background-color: #0f3460;
    color: #e0e0e0;
}

#sidebar QPushButton[active="true"] {
    background-color: #e63946;
    color: #ffffff;
    font-weight: bold;
}

#app_title {
    color: #e63946;
    font-size: 16px;
    font-weight: bold;
    padding: 20px 16px 10px 16px;
}

/* Content area */
#content {
    background-color: #1a1a2e;
    padding: 10px;
}

/* Cards / panels */
QGroupBox {
    border: 1px solid #0f3460;
    border-radius: 8px;
    margin-top: 12px;
    padding: 10px;
    font-weight: bold;
    color: #a0c4ff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
}

/* Buttons */
QPushButton {
    background-color: #0f3460;
    color: #e0e0e0;
    border: 1px solid #1a4a80;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #1a4a80;
    border-color: #e63946;
}

QPushButton:pressed {
    background-color: #e63946;
}

QPushButton#btn_primary {
    background-color: #e63946;
    border-color: #e63946;
    color: white;
    font-weight: bold;
}

QPushButton#btn_primary:hover {
    background-color: #c1121f;
}

QPushButton#btn_danger {
    background-color: #6b0d14;
    border-color: #e63946;
    color: #ffb3b3;
}

QPushButton#btn_danger:hover {
    background-color: #e63946;
    color: white;
}

/* Inputs */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #16213e;
    border: 1px solid #0f3460;
    border-radius: 4px;
    padding: 6px 8px;
    color: #e0e0e0;
    selection-background-color: #e63946;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #e63946;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #16213e;
    border: 1px solid #0f3460;
    selection-background-color: #e63946;
    color: #e0e0e0;
}

/* Tables */
QTableView, QTableWidget {
    background-color: #16213e;
    alternate-background-color: #1a2540;
    border: 1px solid #0f3460;
    border-radius: 4px;
    gridline-color: #0f3460;
    color: #e0e0e0;
    selection-background-color: #e63946;
}

QHeaderView::section {
    background-color: #0f3460;
    color: #a0c4ff;
    padding: 6px;
    border: none;
    border-right: 1px solid #1a4a80;
    font-weight: bold;
}

/* Scroll bars */
QScrollBar:vertical {
    background: #16213e;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #0f3460;
    border-radius: 5px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #e63946;
}

QScrollBar:horizontal {
    background: #16213e;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background: #0f3460;
    border-radius: 5px;
}

/* Labels */
QLabel#section_title {
    font-size: 18px;
    font-weight: bold;
    color: #e0e0e0;
    padding-bottom: 4px;
}

QLabel#field_label {
    color: #a0c4ff;
    font-size: 12px;
}

/* Progress bar */
QProgressBar {
    background-color: #16213e;
    border: 1px solid #0f3460;
    border-radius: 4px;
    text-align: center;
    color: white;
    height: 18px;
}

QProgressBar::chunk {
    background-color: #e63946;
    border-radius: 3px;
}

/* List widget */
QListWidget {
    background-color: #16213e;
    border: 1px solid #0f3460;
    border-radius: 4px;
    color: #e0e0e0;
}

QListWidget::item:selected {
    background-color: #e63946;
    color: white;
}

QListWidget::item:hover {
    background-color: #0f3460;
}

/* Splitter */
QSplitter::handle {
    background-color: #0f3460;
    width: 2px;
}

/* Status bar */
QStatusBar {
    background-color: #16213e;
    color: #a0a0b0;
    border-top: 1px solid #0f3460;
}

/* Tab widget */
QTabWidget::pane {
    border: 1px solid #0f3460;
    border-radius: 4px;
}

QTabBar::tab {
    background: #16213e;
    color: #a0a0b0;
    padding: 8px 16px;
    border-bottom: 2px solid transparent;
}

QTabBar::tab:selected {
    color: #e63946;
    border-bottom: 2px solid #e63946;
}

QTabBar::tab:hover {
    color: #e0e0e0;
}

/* Tooltips */
QToolTip {
    background-color: #0f3460;
    color: #e0e0e0;
    border: 1px solid #e63946;
    border-radius: 4px;
    padding: 4px;
}
"""
