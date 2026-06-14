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
    _BW, _BH = 130, 62
    _GAP      = 36

    _C = {
        "bg":      QColor(241, 245, 249),   # slate-100
        "box_bg":  QColor(255, 255, 255),
        "blue":    QColor(37, 99, 235),     # blue-600
        "amber":   QColor(217, 119, 6),     # amber-600
        "green":   QColor(5, 150, 105),     # emerald-600
        "teal":    QColor(13, 148, 136),    # teal-600
        "slate":   QColor(100, 116, 139),
        "text":    QColor(30, 41, 59),
        "muted":   QColor(100, 116, 139),
        "arrow":   QColor(148, 163, 184),
    }

    # Row 1 — shared input pipeline
    _ROW1 = [
        ("📄", "Input Files",      "JPG · PNG · PDF",     "blue"),
        ("🗺",  "Template Builder", "Draw field boxes",    "blue"),
        ("🔍", "Tesseract OCR",    "pytesseract engine",  "amber"),
    ]

    # Row 2a — single-file path
    _ROW2A = [
        ("📋", "Single Extract",  "Add files manually",  "blue"),
        ("✏️", "Review & Edit",   "Balance check · Fix", "blue"),
    ]

    # Row 2b — batch path
    _ROW2B = [
        ("📁", "Batch Folder",    "Point to folder",     "amber"),
        ("⚡", "Batch Run",       "Auto-OCR · Move",     "amber"),
    ]

    # Row 3 — shared output
    _ROW3 = [
        ("💾", "Save to Database", "SQLite — local only", "green"),
        ("📈", "History",          "Filter · Export",     "teal"),
    ]

    def __init__(self):
        super().__init__()
        self.setFixedHeight(430)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W = self.width()

        BW, BH, GAP = self._BW, self._BH, self._GAP
        C = self._C

        ROW1_Y = 22
        ROW2_Y = 168
        ROW3_Y = 320

        p.fillRect(self.rect(), C["bg"])

        # ── Row 1 (3 boxes, centered) ─────────────────────────────────────────
        total1 = 3 * BW + 2 * GAP
        x0_1 = (W - total1) / 2

        r1_x = []
        for i, (icon, label, sub, acc) in enumerate(self._ROW1):
            x = x0_1 + i * (BW + GAP)
            r1_x.append(x)
            self._draw_box(p, x, ROW1_Y, icon, label, sub, C[acc])
            if i < 2:
                self._arrow_h(p, x + BW, ROW1_Y + BH / 2, x + BW + GAP)

        # ── Row 2a (single-file path, left quarter) ───────────────────────────
        total_sub = 2 * BW + GAP
        x0_2a = max(8.0, W * 0.25 - total_sub / 2)

        r2a_x = []
        for i, (icon, label, sub, acc) in enumerate(self._ROW2A):
            x = x0_2a + i * (BW + GAP)
            r2a_x.append(x)
            self._draw_box(p, x, ROW2_Y, icon, label, sub, C[acc])
            if i < 1:
                self._arrow_h(p, x + BW, ROW2_Y + BH / 2, x + BW + GAP)

        # ── Row 2b (batch path, right quarter) ───────────────────────────────
        x0_2b = min(W - total_sub - 8.0, W * 0.75 - total_sub / 2)

        r2b_x = []
        for i, (icon, label, sub, acc) in enumerate(self._ROW2B):
            x = x0_2b + i * (BW + GAP)
            r2b_x.append(x)
            self._draw_box(p, x, ROW2_Y, icon, label, sub, C[acc])
            if i < 1:
                self._arrow_h(p, x + BW, ROW2_Y + BH / 2, x + BW + GAP)

        # "OR" label between the two paths
        mid_between = (r2a_x[1] + BW + r2b_x[0]) / 2
        f_or = QFont("Segoe UI", 8)
        f_or.setBold(True)
        p.setFont(f_or)
        p.setPen(QPen(C["slate"]))
        p.drawText(QRectF(mid_between - 18, ROW2_Y + BH / 2 - 10, 36, 20),
                   Qt.AlignmentFlag.AlignCenter, "OR")

        # ── Row 3 (2 boxes, centered) ─────────────────────────────────────────
        x0_3 = (W - (2 * BW + GAP)) / 2

        r3_x = []
        for i, (icon, label, sub, acc) in enumerate(self._ROW3):
            x = x0_3 + i * (BW + GAP)
            r3_x.append(x)
            self._draw_box(p, x, ROW3_Y, icon, label, sub, C[acc])
            if i < 1:
                self._arrow_h(p, x + BW, ROW3_Y + BH / 2, x + BW + GAP)

        pen = QPen(C["arrow"], 1.5, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)

        # ── Fork: Tesseract OCR → two paths ───────────────────────────────────
        tess_cx = r1_x[2] + BW / 2
        tess_bot = ROW1_Y + BH
        fork_y = tess_bot + (ROW2_Y - tess_bot) * 0.45

        cx_2a = r2a_x[0] + BW / 2
        cx_2b = r2b_x[0] + BW / 2

        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        # Stem down from Tesseract
        p.drawLine(QPointF(tess_cx, tess_bot), QPointF(tess_cx, fork_y))

        # Left branch → Single Extract
        path_l = QPainterPath()
        path_l.moveTo(tess_cx, fork_y)
        path_l.lineTo(cx_2a, fork_y)
        path_l.lineTo(cx_2a, ROW2_Y - 7)
        p.drawPath(path_l)
        self._arrowhead_v(p, cx_2a, ROW2_Y)

        # Right branch → Batch Folder
        path_r = QPainterPath()
        path_r.moveTo(tess_cx, fork_y)
        path_r.lineTo(cx_2b, fork_y)
        path_r.lineTo(cx_2b, ROW2_Y - 7)
        p.drawPath(path_r)
        self._arrowhead_v(p, cx_2b, ROW2_Y)

        # Fork labels
        p.setFont(QFont("Segoe UI", 7))
        p.setPen(QPen(C["muted"]))
        label_y = fork_y - 13
        p.drawText(QRectF(cx_2a, label_y, tess_cx - cx_2a - 6, 12),
                   Qt.AlignmentFlag.AlignRight, "single file")
        p.drawText(QRectF(tess_cx + 6, label_y, cx_2b - tess_cx, 12),
                   Qt.AlignmentFlag.AlignLeft, "batch folder")

        # ── Merge: both paths → Save to Database ──────────────────────────────
        save_cx = r3_x[0] + BW / 2
        merge_y = ROW2_Y + BH + (ROW3_Y - ROW2_Y - BH) * 0.5

        re_cx = r2a_x[1] + BW / 2     # Review & Edit center
        br_cx = r2b_x[1] + BW / 2     # Batch Run center

        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        # From Review & Edit down and right to merge point
        path_m1 = QPainterPath()
        path_m1.moveTo(re_cx, ROW2_Y + BH)
        path_m1.lineTo(re_cx, merge_y)
        path_m1.lineTo(save_cx, merge_y)
        p.drawPath(path_m1)

        # From Batch Run down and left to merge point
        path_m2 = QPainterPath()
        path_m2.moveTo(br_cx, ROW2_Y + BH)
        path_m2.lineTo(br_cx, merge_y)
        path_m2.lineTo(save_cx, merge_y)
        p.drawPath(path_m2)

        # Shared stem down to Save to Database
        p.drawLine(QPointF(save_cx, merge_y), QPointF(save_cx, ROW3_Y - 7))
        self._arrowhead_v(p, save_cx, ROW3_Y)

    # ── Drawing helpers ───────────────────────────────────────────────────────

    def _draw_box(self, p, x, y, icon, label, sub, accent):
        BW, BH = self._BW, self._BH
        C = self._C

        rect = QRectF(x, y, BW, BH)
        grad = QLinearGradient(x, y, x, y + BH)
        grad.setColorAt(0, C["box_bg"].lighter(110))
        grad.setColorAt(1, C["box_bg"])
        p.setBrush(QBrush(grad))
        p.setPen(QPen(accent, 1.5))
        p.drawRoundedRect(rect, 8, 8)

        p.setFont(QFont("Segoe UI Emoji", 14))
        p.setPen(QPen(C["text"]))
        p.drawText(QRectF(x, y + 4, BW, 24),
                   Qt.AlignmentFlag.AlignHCenter, icon)

        f = QFont("Segoe UI", 8)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QPen(C["text"]))
        p.drawText(QRectF(x, y + 28, BW, 16),
                   Qt.AlignmentFlag.AlignHCenter, label)

        p.setFont(QFont("Segoe UI", 7))
        p.setPen(QPen(C["muted"]))
        p.drawText(QRectF(x, y + 44, BW, 14),
                   Qt.AlignmentFlag.AlignHCenter, sub)

    def _arrow_h(self, p, x1, y, x2):
        p.setPen(QPen(self._C["arrow"], 1.5))
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
        lbl_step.setFixedWidth(28)
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
                  "header fields as <i>Repeat</i> (value copies to every row) or "
                  "<i>Sub-group</i> (e.g. RBS-style where date appears once per group). "
                  "Create one template per bank layout."),
            ("2", "<b>Single File Extract</b> — Switch to Extract, click <i>Add Files</i>, "
                  "and select statement JPGs, PNGs, or PDFs. Right-click or press Delete "
                  "to remove files from the list. Choose the matching template, then click "
                  "<i>Run OCR</i>. Review the extracted table, edit inline, then save to "
                  "the database. <i>Use this path for one-off or ad-hoc processing.</i>"),
            ("3", "<b>Batch Processing</b> <i>(alternative to step 2)</i> — Drop all "
                  "statement files into your batch import folder. Switch to Batch, set a "
                  "batch name (auto-filled with today's date/time), choose the template, "
                  "and click <i>Start Batch</i>. Each file is OCR-processed in sequence; "
                  "on success it moves automatically to the batch complete folder and is "
                  "saved to the database. All rows in the batch share the same batch name. "
                  "A live log shows per-file status. <i>Use this path for bulk runs of "
                  "multiple statements at once.</i>"),
            ("4", "<b>Review Extracted Data</b> — After single-file OCR, rows appear in "
                  "the table. The <i>balance_check</i> column (✓ green / ✗ red) "
                  "automatically verifies the running balance using debit/credit math. "
                  "Sign convention (standard vs inverted) is auto-detected per batch. "
                  "In batch mode, data is already saved — review it in History."),
            ("5", "<b>Fix Errors Inline</b> — Double-click any editable cell to correct "
                  "OCR mistakes. The original value is pre-filled; edit and press Enter. "
                  "The <i>note</i> column auto-stamps "
                  "<i>Manual override: [field] 'before' → 'after'</i>. "
                  "Editing a balance or amount cell instantly reruns the balance check. "
                  "Clicking away without changing anything leaves no note."),
            ("6", "<b>Save to Database</b> — Click <i>Save to Database</i> to persist "
                  "all rows (including your edits) to the local SQLite file "
                  "<code>ocr_master.db</code>. Use <i>Export CSV</i> to save a flat file "
                  "for use in Excel or other tools. Batch runs save automatically — "
                  "no manual step needed."),
            ("7", "<b>History</b> — Browse all saved transactions across all batches. "
                  "Filter by date range, template, or keyword. Continue editing rows "
                  "inline — balance check reruns just as in Extract. Delete entire batches "
                  "when no longer needed. Export any filtered view to CSV."),
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
            ("📁", "<b>Batch folder setup</b> — Create an import folder (e.g. "
                  "<code>batch_import/</code>) and a complete folder (e.g. "
                  "<code>batch_complete/</code>). Configure both paths in the Batch module "
                  "before starting. Processed files move out of import automatically, "
                  "so a re-run never double-processes the same file."),
        ]))

        lay.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)
