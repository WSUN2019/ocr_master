"""
Interactive image canvas — display a bank statement image and let the user
draw red bounding boxes over fields with the mouse.
"""
import io
from typing import Optional

from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPointF, QTimer
from PyQt6.QtGui import (
    QPixmap, QImage, QPen, QBrush, QColor, QCursor, QPainter
)
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsPixmapItem, QSizePolicy
)
from PIL import Image


# ── Colours ───────────────────────────────────────────────────────────────────
RED_PEN   = QPen(QColor(230, 57, 70), 2)
RED_BRUSH = QBrush(QColor(230, 57, 70, 50))


def _pil_to_qpixmap(img: Image.Image) -> QPixmap:
    """Convert PIL Image to QPixmap via an in-memory PNG (avoids raw-byte alignment issues)."""
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    pix = QPixmap()
    pix.loadFromData(buf.getvalue(), "PNG")
    return pix


class BoxItem(QGraphicsRectItem):
    """A single labelled red bounding box on the canvas."""

    def __init__(self, rect: QRectF, field_name: str = ""):
        super().__init__(rect)
        self.field_name = field_name
        self.setPen(RED_PEN)
        self.setBrush(RED_BRUSH)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable)
        self.setToolTip(field_name)

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        if self.field_name:
            painter.setPen(QPen(QColor(255, 255, 255)))
            r = self.rect()
            painter.drawText(int(r.x()) + 3, int(r.y()) + 14, self.field_name)


class CanvasWidget(QGraphicsView):
    """
    Displays a PIL image and lets the user draw red rectangles.
    Scene coordinates == source image pixels (image placed at origin 0,0).
    """

    box_drawn   = pyqtSignal(QRectF)
    box_removed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setBackgroundBrush(QBrush(QColor(26, 26, 46)))
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        self.setMinimumSize(400, 300)

        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._boxes: list[BoxItem] = []
        self._drawing = False
        self._draw_start: Optional[QPointF] = None
        self._temp_rect: Optional[QGraphicsRectItem] = None
        self._image_loaded = False

    # ── Image loading ─────────────────────────────────────────────────────────

    def set_image(self, img: Image.Image):
        self._scene.clear()
        self._boxes.clear()
        self._temp_rect = None
        self._image_loaded = False

        pix = _pil_to_qpixmap(img)
        if pix.isNull():
            return

        self._pixmap_item = self._scene.addPixmap(pix)
        self._scene.setSceneRect(0, 0, pix.width(), pix.height())
        self._image_loaded = True

        # Reset any previous transform, then fit — deferred so layout is complete
        self.resetTransform()
        QTimer.singleShot(50, self._fit_image)

    def fit_image(self):
        """Public slot — also wired to the 'Fit' button in template builder."""
        self._fit_image()

    def _fit_image(self):
        if self._pixmap_item and self._image_loaded:
            self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
            self.viewport().update()

    # ── Box management ────────────────────────────────────────────────────────

    def clear_boxes(self):
        for b in self._boxes:
            self._scene.removeItem(b)
        self._boxes.clear()

    def load_boxes(self, field_defs: list[dict], img_w: float, img_h: float):
        self.clear_boxes()
        for f in field_defs:
            x0, y0, x1, y1 = f["bbox"]
            self._add_box(QRectF(x0, y0, x1 - x0, y1 - y0), f["name"])

    # ── Mouse drawing ─────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drawing = True
            self._draw_start = self.mapToScene(event.pos())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drawing and self._draw_start:
            end = self.mapToScene(event.pos())
            rect = QRectF(self._draw_start, end).normalized()
            if self._temp_rect:
                self._scene.removeItem(self._temp_rect)
            self._temp_rect = self._scene.addRect(rect, RED_PEN, RED_BRUSH)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drawing and event.button() == Qt.MouseButton.LeftButton:
            self._drawing = False
            if self._temp_rect:
                self._scene.removeItem(self._temp_rect)
                self._temp_rect = None
            if self._draw_start:
                end = self.mapToScene(event.pos())
                rect = QRectF(self._draw_start, end).normalized()
                if rect.width() > 5 and rect.height() > 5:
                    self.box_drawn.emit(rect)
        super().mouseReleaseEvent(event)

    def _add_box(self, rect: QRectF, field_name: str) -> BoxItem:
        box = BoxItem(rect, field_name)
        self._scene.addItem(box)
        self._boxes.append(box)
        return box

    def add_named_box(self, rect: QRectF, field_name: str):
        self._add_box(rect, field_name)

    def remove_selected_box(self):
        for i, box in enumerate(self._boxes):
            if box.isSelected():
                self._scene.removeItem(box)
                self._boxes.pop(i)
                self.box_removed.emit(i)
                return

    def get_field_defs(self) -> list[dict]:
        defs = []
        for box in self._boxes:
            r = box.sceneBoundingRect()
            defs.append({
                "name": box.field_name,
                "label": box.field_name.replace("_", " ").title(),
                "page": 0,
                "bbox": [round(r.x(), 2), round(r.y(), 2),
                         round(r.x() + r.width(), 2), round(r.y() + r.height(), 2)],
            })
        return defs

    # ── Zoom / resize ─────────────────────────────────────────────────────────

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def showEvent(self, event):
        super().showEvent(event)
        # First time the widget is actually shown — now fitInView has real dimensions
        QTimer.singleShot(10, self._fit_image)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_image()
