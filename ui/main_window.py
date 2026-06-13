"""
Main application window — sidebar navigation + stacked content pages.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QStatusBar, QSizePolicy
)

from ui.template_builder import TemplateBuilderWidget
from ui.extract_widget import ExtractWidget
from ui.history_widget import HistoryWidget
from ui.settings_widget import SettingsWidget
from ui.help_widget import HelpWidget
from ui.about_widget import AboutWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OCR Master — Bank Statement Extractor")
        self.resize(1280, 820)
        self.setMinimumSize(900, 600)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(195)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(8, 0, 8, 16)
        sb_layout.setSpacing(4)

        title = QLabel("OCR Master")
        title.setObjectName("app_title")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        sb_layout.addWidget(title)

        subtitle = QLabel("Bank Statement Extractor")
        subtitle.setStyleSheet(
            "color: #253449; font-size: 10px; padding-left: 20px; padding-bottom: 16px;"
        )
        subtitle.setWordWrap(True)
        sb_layout.addWidget(subtitle)

        self._nav_buttons: list[QPushButton] = []
        nav_items = [
            ("  \U0001f5fa  Template Builder", "Map fields on a sample image"),
            ("  \U0001f4c4  Extract",           "Run OCR on statements"),
            ("  \U0001f4ca  History",           "Browse extracted data"),
            ("  ⚙️  Settings",        "Templates & database"),
            ("  ❓  How to Use",      "Workflow guide & diagram"),
            ("  ℹ️  About",           "About OCR Master"),
        ]
        for text, tip in nav_items:
            btn = QPushButton(text)
            btn.setToolTip(tip)
            btn.setCheckable(False)
            btn.setProperty("active", "false")
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self._nav_buttons.append(btn)
            sb_layout.addWidget(btn)

        sb_layout.addStretch()

        root_layout.addWidget(sidebar)

        # ── Stacked content ───────────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.setObjectName("content")

        self._template_builder = TemplateBuilderWidget()
        self._extract_widget   = ExtractWidget()
        self._history_widget   = HistoryWidget()
        self._settings_widget  = SettingsWidget()
        self._help_widget      = HelpWidget()
        self._about_widget     = AboutWidget()

        for w in [self._template_builder, self._extract_widget,
                  self._history_widget, self._settings_widget,
                  self._help_widget, self._about_widget]:
            self._stack.addWidget(w)

        root_layout.addWidget(self._stack)

        # ── Status bar ────────────────────────────────────────────────────────
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")

        # ── Wire navigation ───────────────────────────────────────────────────
        for i, btn in enumerate(self._nav_buttons):
            btn.clicked.connect(lambda checked, idx=i: self._navigate(idx))

        self._navigate(0)

        for w in [self._template_builder, self._extract_widget,
                  self._history_widget, self._settings_widget]:
            if hasattr(w, "status_message"):
                w.status_message.connect(self.status.showMessage)

    def _navigate(self, index: int):
        self._stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_buttons):
            btn.setProperty("active", "true" if i == index else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        widget = self._stack.currentWidget()
        if hasattr(widget, "refresh"):
            widget.refresh()
