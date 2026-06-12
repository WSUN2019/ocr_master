"""
About page — app info, tech stack, version, creator.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QFrame
)

from core.extractor import tesseract_available


def _row(label: str, value: str) -> QHBoxLayout:
    row = QHBoxLayout()
    lbl = QLabel(label)
    lbl.setFixedWidth(160)
    lbl.setStyleSheet("color: #4b5563; font-size: 12px;")
    val = QLabel(value)
    val.setStyleSheet("color: #e2e8f0; font-size: 12px;")
    val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    row.addWidget(lbl)
    row.addWidget(val)
    row.addStretch()
    return row


def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("color: #1e2d45;")
    return line


class AboutWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(24)
        root.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ── App header ────────────────────────────────────────────────────────
        hdr = QVBoxLayout()
        hdr.setSpacing(6)

        name_lbl = QLabel("OCR Master")
        name_lbl.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        name_lbl.setStyleSheet("color: #60a5fa; letter-spacing: 1px;")
        hdr.addWidget(name_lbl)

        tagline = QLabel("Offline bank statement extractor — your data never leaves this machine.")
        tagline.setStyleSheet("color: #64748b; font-size: 14px;")
        hdr.addWidget(tagline)

        root.addLayout(hdr)
        root.addWidget(_divider())

        # ── App info ──────────────────────────────────────────────────────────
        info_group = QGroupBox("Application")
        info_layout = QVBoxLayout(info_group)
        info_layout.setSpacing(10)

        info_layout.addLayout(_row("Version",       "1.0.0"))
        info_layout.addLayout(_row("Created",        "June 2026"))
        info_layout.addLayout(_row("Creator",        "WSUN2019"))
        info_layout.addLayout(_row("Platform",       "Linux · Windows"))
        info_layout.addLayout(_row("Repository",     "github.com/WSUN2019/ocr_master"))

        root.addWidget(info_group)

        # ── Tech stack ────────────────────────────────────────────────────────
        tech_group = QGroupBox("Technology Stack")
        tech_layout = QVBoxLayout(tech_group)
        tech_layout.setSpacing(10)

        ok, tess_ver = tesseract_available()
        tess_str = f"Tesseract {tess_ver}" if ok else "Tesseract — NOT FOUND (install tesseract-ocr)"
        tess_color = "#10b981" if ok else "#ef4444"

        tess_row = QHBoxLayout()
        tll = QLabel("OCR Engine")
        tll.setFixedWidth(160)
        tll.setStyleSheet("color: #4b5563; font-size: 12px;")
        tvl = QLabel(tess_str)
        tvl.setStyleSheet(f"color: {tess_color}; font-size: 12px;")
        tess_row.addWidget(tll)
        tess_row.addWidget(tvl)
        tess_row.addStretch()
        tech_layout.addLayout(tess_row)

        stack = [
            ("UI Framework",     "PyQt6  (Qt 6)"),
            ("Image Processing", "Pillow · PyMuPDF (fitz)"),
            ("Data Layer",       "SQLite · pandas"),
            ("Language",         f"Python {sys.version.split()[0]}"),
        ]
        for label, value in stack:
            tech_layout.addLayout(_row(label, value))

        root.addWidget(tech_group)

        # ── Security note ─────────────────────────────────────────────────────
        sec_group = QGroupBox("Privacy & Security")
        sec_layout = QVBoxLayout(sec_group)

        note = QLabel(
            "OCR Master runs entirely on your local machine.\n"
            "No statement images, transaction data, or database content is ever\n"
            "transmitted to the internet, cloud services, or any third party.\n\n"
            "Sensitive files (images, PDFs, CSVs, the database) are excluded from\n"
            "version control via .gitignore."
        )
        note.setStyleSheet("color: #94a3b8; font-size: 12px; line-height: 1.6;")
        note.setWordWrap(True)
        sec_layout.addWidget(note)
        root.addWidget(sec_group)

        root.addStretch()
