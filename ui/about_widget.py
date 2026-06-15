"""
About page — app info, tech stack, version, creator. Light mode style.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QFrame, QScrollArea, QSizePolicy
)

from core.extractor import tesseract_available

# ── Light palette ─────────────────────────────────────────────────────────────
_PAGE_BG   = "#f1f5f9"
_CARD_BG   = "#ffffff"
_BORDER    = "#e2e8f0"
_TITLE     = "#1e3a5f"
_HEADING   = "#1e40af"
_BODY      = "#334155"
_MUTED     = "#64748b"
_ACCENT    = "#2563eb"
_GREEN     = "#059669"
_RED       = "#dc2626"

_CARD_STYLE = f"""
    QGroupBox {{
        background: {_CARD_BG};
        border: 1px solid {_BORDER};
        border-radius: 8px;
        margin-top: 12px;
        padding: 10px 14px 10px 14px;
        font-size: 12px;
        font-weight: bold;
        color: {_TITLE};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: {_HEADING};
        font-size: 12px;
        font-weight: bold;
    }}
"""


def _kv_row(label: str, value: str, value_color: str = _BODY) -> QHBoxLayout:
    row = QHBoxLayout()
    lbl = QLabel(label)
    lbl.setFixedWidth(180)
    lbl.setStyleSheet(f"color: {_MUTED}; font-size: 12px; background: transparent;")
    val = QLabel(value)
    val.setStyleSheet(f"color: {value_color}; font-size: 12px; background: transparent;")
    val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    row.addWidget(lbl)
    row.addWidget(val)
    row.addStretch()
    return row


def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"background: {_BORDER}; border: none; max-height: 1px;")
    return line


class AboutWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background: {_PAGE_BG};")
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"background: {_PAGE_BG};")

        body = QWidget()
        body.setStyleSheet(f"background: {_PAGE_BG};")
        root = QVBoxLayout(body)
        root.setContentsMargins(40, 32, 40, 32)
        root.setSpacing(16)
        root.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ── Header ────────────────────────────────────────────────────────────
        name_lbl = QLabel("OCR Master")
        name_lbl.setFont(QFont("Segoe UI", 30, QFont.Weight.Bold))
        name_lbl.setStyleSheet(f"color: {_TITLE}; background: transparent; letter-spacing: 1px;")
        root.addWidget(name_lbl)

        tagline = QLabel("Bank statement extractor — proof of concept technology demonstrator. Use at your own risk.")
        tagline.setStyleSheet(f"color: {_MUTED}; font-size: 13px; background: transparent;")
        root.addWidget(tagline)

        root.addWidget(_divider())

        # ── App info ──────────────────────────────────────────────────────────
        info = QGroupBox("Application")
        info.setStyleSheet(_CARD_STYLE)
        il = QVBoxLayout(info)
        il.setSpacing(8)
        for label, value in [
            ("Version",    "1.2.0"),
            ("Created",    "June 2026"),
            ("Creator",    "WSUN2019"),
            ("Platform",   "Linux · Windows"),
            ("Repository", "github.com/WSUN2019/ocr_master"),
        ]:
            il.addLayout(_kv_row(label, value, _ACCENT if label == "Repository" else _BODY))
        root.addWidget(info)

        # ── Features ──────────────────────────────────────────────────────────
        feat = QGroupBox("Features")
        feat.setStyleSheet(_CARD_STYLE)
        fl = QVBoxLayout(feat)
        fl.setSpacing(10)

        for name, desc in [
            ("Template Builder",    "Draw bounding boxes on a sample image to define field positions per bank layout"),
            ("Repeat & Sub-group",  "Repeat fields copy to every row; sub-group fields fill-down (e.g. RBS date/balance per group)"),
            ("Single-file Extract", "Add files manually, run OCR, review and edit inline before saving"),
            ("Batch Processing",    "Point at a folder — all files process under one batch name; each moves to a complete folder on finish"),
            ("Balance Validation",  "Auto-computed ✓/✗ column checks running balance as a review aid only — not a guarantee of accuracy; reruns on edit"),
            ("Inline Editing",      "Double-click any cell to correct OCR errors; note column auto-stamped with before/after values"),
            ("History",             "Browse, filter, search, re-edit, and delete batches of saved transactions"),
            ("Export",              "CSV export from both Extract and History views"),
        ]:
            row = QHBoxLayout()
            ln = QLabel(name)
            ln.setFixedWidth(180)
            ln.setAlignment(Qt.AlignmentFlag.AlignTop)
            ln.setStyleSheet(f"color: {_HEADING}; font-size: 12px; font-weight: bold; background: transparent;")
            ld = QLabel(desc)
            ld.setWordWrap(True)
            ld.setStyleSheet(f"color: {_BODY}; font-size: 12px; background: transparent;")
            ld.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            row.addWidget(ln)
            row.addWidget(ld)
            fl.addLayout(row)

        root.addWidget(feat)

        # ── Tech stack ────────────────────────────────────────────────────────
        tech = QGroupBox("Technology Stack")
        tech.setStyleSheet(_CARD_STYLE)
        tl = QVBoxLayout(tech)
        tl.setSpacing(8)

        ok, tess_ver = tesseract_available()
        tl.addLayout(_kv_row(
            "OCR Engine",
            f"Tesseract {tess_ver}" if ok else "Tesseract — NOT FOUND (install tesseract-ocr)",
            _GREEN if ok else _RED,
        ))
        for label, value in [
            ("UI Framework",     "PyQt6  (Qt 6)"),
            ("Image Processing", "Pillow · PyMuPDF (fitz)"),
            ("Data Layer",       "SQLite · pandas"),
            ("Language",         f"Python {sys.version.split()[0]}"),
        ]:
            tl.addLayout(_kv_row(label, value))

        root.addWidget(tech)

        # ── Experiment ────────────────────────────────────────────────────────
        exp = QGroupBox("About This Project")
        exp.setStyleSheet(_CARD_STYLE)
        el = QVBoxLayout(exp)
        el.setSpacing(10)

        exp_text = QLabel(
            "OCR Master was built as an experiment: use VS Code + Claude Code "
            "(Anthropic's AI coding assistant) to write a fully functioning desktop "
            "application from scratch — including a Windows .exe installer and a "
            "documented path to Microsoft Store publishing — with no prior codebase.\n\n"
            "The experiment confirmed that AI-assisted coding delivers remarkable "
            "speed through the first 80% of a project. Architecture, core logic, "
            "UI layout, OCR pipeline, and the build/installer system all came "
            "together rapidly.\n\n"
            "The final 20% — true polish, edge-case handling, and production-grade "
            "fit-and-finish — proved to take as much effort as the first 80%. "
            "Layout quirks, button sizing, cascading stylesheet bugs, and subtle UX "
            "details each required careful human judgment that AI alone could not "
            "reliably close out.\n\n"
            "Conclusion: AI coding assistance is a genuine force multiplier for "
            "getting to a working product fast. But the classic Tortoise and Hare "
            "dynamic applies — the finish line of a truly polished product still "
            "demands the same deliberate craft it always has."
        )
        exp_text.setWordWrap(True)
        exp_text.setStyleSheet(f"color: {_BODY}; font-size: 12px; background: transparent;")
        el.addWidget(exp_text)

        built_with = QLabel("Built with: VS Code · Claude Code (claude-sonnet-4-6) · Python 3.11 · PyQt6")
        built_with.setStyleSheet(f"color: {_MUTED}; font-size: 11px; background: transparent;")
        el.addWidget(built_with)

        root.addWidget(exp)

        root.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll)
