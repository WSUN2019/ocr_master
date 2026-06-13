"""
How to Use — visual workflow guide for OCR Master.
"""
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush, QPainterPath, QLinearGradient
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QLabel, QFrame,
    QHBoxLayout, QSizePolicy, QGroupBox
)


# ── Flow diagram ──────────────────────────────────────────────────────────────

class _FlowDiagram(QWidget):
    _BW, _BH = 136, 64
    _GAP      = 40

    _C = {
        "bg":      QColor(241, 245, 249),   # slate-100
        "box_bg":  QColor(255, 255, 255),   # white
        "blue":    QColor(37, 99, 235),     # blue-600
        "amber":   QColor(217, 119, 6),     # amber-600
        "green":   QColor(5, 150, 105),     # emerald-600
        "teal":    QColor(13, 148, 136),    # teal-600
        "slate":   QColor(100, 116, 139),   # slate-500
        "text":    QColor(30, 41, 59),      # slate-800
        "muted":   QColor(100, 116, 139),   # slate-500
        "arrow":   QColor(148, 163, 184),   # slate-400
    }

    # (icon, label, sublabel, accent-key)
    _ROW1 = [
        ("📄", "Input Files",       "JPG · PNG · PDF",      "blue"),
        ("🗺",  "Template Builder",  "Draw field boxes",     "blue"),
        ("🔍", "Tesseract OCR",     "pytesseract engine",   "amber"),
        ("📊", "Extracted Data",    "Structured rows",      "blue"),
    ]
    _ROW2 = [
        ("✏️", "Review & Edit",    "Balance check · Fix",  "blue"),
        ("💾", "Save to Database", "SQLite — local only",  "green"),
        ("📈", "History",          "Filter · Export · Del","teal"),
    ]

    def __init__(self):
        super().__init__()
        self.setFixedHeight(310)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W = self.width()

        BW, BH, GAP = self._BW, self._BH, self._GAP
        C = self._C

        # Background
        p.fillRect(self.rect(), C["bg"])

        # ── Row 1 ────────────────────────────────────────────────────────────
        total1 = len(self._ROW1) * BW + (len(self._ROW1) - 1) * GAP
        x0_1   = (W - total1) / 2
        ROW1_Y = 30

        r1_boxes = []
        for i, (icon, label, sub, acc) in enumerate(self._ROW1):
            x = x0_1 + i * (BW + GAP)
            r1_boxes.append((x, ROW1_Y))
            self._draw_box(p, x, ROW1_Y, icon, label, sub, C[acc])
            if i < len(self._ROW1) - 1:
                self._arrow_h(p, x + BW, ROW1_Y + BH / 2, x + BW + GAP)

        # ── Row 2 ────────────────────────────────────────────────────────────
        total2 = len(self._ROW2) * BW + (len(self._ROW2) - 1) * GAP
        x0_2   = (W - total2) / 2
        ROW2_Y = 200

        r2_boxes = []
        for i, (icon, label, sub, acc) in enumerate(self._ROW2):
            x = x0_2 + i * (BW + GAP)
            r2_boxes.append((x, ROW2_Y))
            self._draw_box(p, x, ROW2_Y, icon, label, sub, C[acc])
            if i < len(self._ROW2) - 1:
                self._arrow_h(p, x + BW, ROW2_Y + BH / 2, x + BW + GAP)

        # ── Connector: bottom of "Extracted Data" → top of "Review & Edit" ──
        x_from = r1_boxes[3][0] + BW / 2
        y_from = ROW1_Y + BH
        x_to   = r2_boxes[0][0] + BW / 2
        y_to   = ROW2_Y
        mid_y  = (y_from + y_to) / 2

        p.setPen(QPen(C["arrow"], 1.5, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath()
        path.moveTo(x_from, y_from)
        path.lineTo(x_from, mid_y)
        path.lineTo(x_to,   mid_y)
        path.lineTo(x_to,   y_to - 7)
        p.drawPath(path)
        self._arrowhead_v(p, x_to, y_to)

        # ── "Export CSV" branch label ─────────────────────────────────────────
        ex_x = r2_boxes[1][0] + BW / 2
        ex_y = ROW2_Y + BH + 12
        p.setFont(QFont("Segoe UI", 7))
        p.setPen(QPen(C["muted"]))
        p.drawText(QRectF(ex_x - 60, ex_y, 120, 14),
                   Qt.AlignmentFlag.AlignHCenter, "also → Export CSV")

    def _draw_box(self, p, x, y, icon, label, sub, accent):
        BW, BH = self._BW, self._BH
        C = self._C

        rect = QRectF(x, y, BW, BH)

        # Subtle gradient fill
        grad = QLinearGradient(x, y, x, y + BH)
        grad.setColorAt(0, C["box_bg"].lighter(110))
        grad.setColorAt(1, C["box_bg"])
        p.setBrush(QBrush(grad))
        p.setPen(QPen(accent, 1.5))
        p.drawRoundedRect(rect, 8, 8)

        # Icon
        p.setFont(QFont("Segoe UI Emoji", 15))
        p.setPen(QPen(C["text"]))
        p.drawText(QRectF(x, y + 4, BW, 26),
                   Qt.AlignmentFlag.AlignHCenter, icon)

        # Label
        f = QFont("Segoe UI", 8)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QPen(C["text"]))
        p.drawText(QRectF(x, y + 30, BW, 16),
                   Qt.AlignmentFlag.AlignHCenter, label)

        # Sub-label
        p.setFont(QFont("Segoe UI", 7))
        p.setPen(QPen(C["muted"]))
        p.drawText(QRectF(x, y + 46, BW, 14),
                   Qt.AlignmentFlag.AlignHCenter, sub)

    def _arrow_h(self, p, x1, y, x2):
        C = self._C
        p.setPen(QPen(C["arrow"], 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(x1, y), QPointF(x2 - 7, y))
        self._arrowhead_h(p, x2, y)

    def _arrowhead_h(self, p, x, y):
        path = QPainterPath()
        path.moveTo(x, y)
        path.lineTo(x - 7, y - 4)
        path.lineTo(x - 7, y + 4)
        path.closeSubpath()
        p.setBrush(QBrush(self._C["arrow"]))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(path)

    def _arrowhead_v(self, p, x, y):
        path = QPainterPath()
        path.moveTo(x, y)
        path.lineTo(x - 4, y - 7)
        path.lineTo(x + 4, y - 7)
        path.closeSubpath()
        p.setBrush(QBrush(self._C["arrow"]))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(path)


# ── Help widget ───────────────────────────────────────────────────────────────

def _section(title: str, items: list[tuple[str, str]]) -> QGroupBox:
    box = QGroupBox(title)
    lay = QVBoxLayout(box)
    lay.setSpacing(6)
    for step, desc in items:
        row = QHBoxLayout()
        row.setSpacing(10)

        lbl_step = QLabel(step)
        lbl_step.setFixedWidth(26)
        lbl_step.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        lbl_step.setStyleSheet("color: #2563eb; font-weight: bold; font-size: 13px;")
        row.addWidget(lbl_step)

        lbl_desc = QLabel(desc)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #334155; font-size: 12px;")
        lbl_desc.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row.addWidget(lbl_desc)

        lay.addLayout(row)
    return box


class HelpWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(0)

        title = QLabel("How to Use OCR Master")
        title.setObjectName("section_title")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        outer.addWidget(title)

        subtitle = QLabel(
            "A fully offline, local tool for extracting structured transaction data "
            "from bank statement images and PDFs. No data is sent to the internet."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #94a3b8; font-size: 12px; padding: 6px 0 12px 0;")
        outer.addWidget(subtitle)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setSpacing(14)
        lay.setContentsMargins(0, 0, 8, 8)

        # Flow diagram
        diag_box = QGroupBox("Workflow Overview")
        diag_lay = QVBoxLayout(diag_box)
        diag_lay.setContentsMargins(4, 8, 4, 4)
        diag_lay.addWidget(_FlowDiagram())
        lay.addWidget(diag_box)

        # Step-by-step
        lay.addWidget(_section("Step-by-Step Guide", [
            ("1", "<b>Build a Template</b> — Open Template Builder and load a sample "
                  "statement image. Draw bounding boxes over each column or field "
                  "(date, description, debit, credit, balance). Name each box and mark "
                  "header fields as <i>Repeat</i> (appears on every row) or "
                  "<i>Sub-group</i> (e.g. RBS-style where date appears once per group)."),
            ("2", "<b>Add Files</b> — Switch to Extract and click <i>Add Files</i>. "
                  "Select your bank statement JPGs, PNGs, or PDFs. You can add multiple "
                  "files at once; select and right-click (or press Delete) to remove "
                  "individual files from the list."),
            ("3", "<b>Choose Template & Run OCR</b> — Pick the matching template from "
                  "the dropdown, then click <i>Run OCR</i>. Tesseract OCR reads every "
                  "page once and crops each field's bounding box to extract text. "
                  "Progress is shown file-by-file."),
            ("4", "<b>Review Extracted Data</b> — Rows appear in the table. A "
                  "<i>balance_check</i> column (✓ green / ✗ red) automatically verifies "
                  "the running balance using debit/credit math. Sign convention "
                  "(standard vs inverted) is auto-detected per batch."),
            ("5", "<b>Fix Errors Inline</b> — Double-click any editable cell to correct "
                  "OCR mistakes. The original value is pre-filled; edit and press Enter. "
                  "A <i>note</i> column records <i>Manual override: [field] before → after</i>. "
                  "Editing a balance or amount field instantly reruns the balance check."),
            ("6", "<b>Save to Database</b> — Click <i>Save to Database</i> to persist "
                  "all rows (including your edits) to the local SQLite file "
                  "<code>ocr_master.db</code>. Use <i>Export CSV</i> for a one-off file."),
            ("7", "<b>History</b> — Browse all saved transactions, filter by date or "
                  "template, search descriptions, and continue editing inline. "
                  "Delete entire batches when no longer needed."),
        ]))

        # Template tips
        lay.addWidget(_section("Template Tips", [
            ("↺", "<b>Repeat field</b> — Mark fields that appear on every transaction "
                  "row (e.g. account number in a header). Their value is copied to "
                  "every row automatically."),
            ("⊞", "<b>Sub-group field</b> — For banks like Royal Bank of Scotland where "
                  "date and balance appear once at the top of a group of rows. The last "
                  "seen value is carried forward (fill-down) to all rows in the group."),
            ("📐", "<b>Box sizing</b> — Draw column boxes to span the full height of the "
                  "transaction area. For header fields (e.g. statement period), draw a "
                  "short box — any box under 60 px tall is treated as a single-value "
                  "header field."),
            ("💡", "<b>One template per layout</b> — Different banks (or even different "
                  "statement designs from the same bank) need separate templates. "
                  "Name them clearly, e.g. <i>RBS Savings 2024</i>."),
        ]))

        # Tech stack
        lay.addWidget(_section("Technology", [
            ("🔍", "<b>Tesseract OCR</b> — Open-source OCR engine (v4+). Must be "
                  "installed separately: <code>sudo apt install tesseract-ocr</code> "
                  "on Linux; installer available for Windows. OCR runs once per page "
                  "using <code>--psm 11</code> (sparse text) for maximum coverage."),
            ("📄", "<b>PyMuPDF (fitz)</b> — Renders PDF pages to 300 DPI images before "
                  "passing to Tesseract, preserving fine print on scanned statements."),
            ("💾", "<b>SQLite</b> — All transaction data is stored in a single local "
                  "file (<code>ocr_master.db</code>) next to the app. No cloud, no "
                  "network, no third-party service is involved."),
            ("🐼", "<b>pandas</b> — Used internally for data manipulation, column "
                  "ordering, balance math, and CSV export. Not exposed externally."),
        ]))

        lay.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)
