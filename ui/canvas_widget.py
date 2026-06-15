"""
Interactive image canvas — display a bank statement image and let the user
draw red bounding boxes over fields with the mouse.
"""
import io
from typing import Optional

from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPointF, QTimer
from PyQt6.QtGui import (
    QPixmap, QPen, QBrush, QColor, QCursor, QPainter
)
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsPixmapItem, QSizePolicy, QGraphicsItem
)
from PIL import Image


RED_PEN   = QPen(QColor(230, 57, 70), 2)
RED_BRUSH = QBrush(QColor(230, 57, 70, 50))
HANDLE_SIZE = 8

# Handle position indices
TL, TC, TR, ML, MR, BL, BC, BR = range(8)

_HANDLE_CURSORS = [
    Qt.CursorShape.SizeFDiagCursor,  # TL
    Qt.CursorShape.SizeVerCursor,    # TC
    Qt.CursorShape.SizeBDiagCursor,  # TR
    Qt.CursorShape.SizeHorCursor,    # ML
    Qt.CursorShape.SizeHorCursor,    # MR
    Qt.CursorShape.SizeBDiagCursor,  # BL
    Qt.CursorShape.SizeVerCursor,    # BC
    Qt.CursorShape.SizeFDiagCursor,  # BR
]


def _pil_to_qpixmap(img: Image.Image) -> QPixmap:
    """Convert PIL Image to QPixmap via PNG buffer (avoids raw-byte alignment issues)."""
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    pix = QPixmap()
    pix.loadFromData(buf.getvalue(), "PNG")
    return pix


class _ResizeHandle(QGraphicsRectItem):
    """Small drag handle on a BoxItem corner/edge used to resize it."""

    def __init__(self, parent: "BoxItem", pos_index: int):
        super().__init__(parent)
        self._pos_index = pos_index
        self._dragging = False
        s = HANDLE_SIZE
        self.setRect(-s / 2, -s / 2, s, s)
        self.setPen(QPen(QColor(255, 255, 255), 1))
        self.setBrush(QBrush(QColor(230, 57, 70)))
        self.setZValue(10)
        self.setVisible(False)
        self.setCursor(QCursor(_HANDLE_CURSORS[pos_index]))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)

    def update_pos(self):
        r = self.parentItem().rect()
        cx, cy = r.center().x(), r.center().y()
        pts = [
            QPointF(r.left(),  r.top()),     # TL
            QPointF(cx,        r.top()),     # TC
            QPointF(r.right(), r.top()),     # TR
            QPointF(r.left(),  cy),          # ML
            QPointF(r.right(), cy),          # MR
            QPointF(r.left(),  r.bottom()),  # BL
            QPointF(cx,        r.bottom()),  # BC
            QPointF(r.right(), r.bottom()),  # BR
        ]
        self.setPos(pts[self._pos_index])

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            parent = self.parentItem()
            if parent is not None and parent._canvas is not None:
                parent._canvas.push_undo()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self._dragging:
            super().mouseMoveEvent(event)
            return
        parent = self.parentItem()
        r = parent.rect()
        local = parent.mapFromScene(event.scenePos())
        new_rect = QRectF(r)
        idx = self._pos_index
        if idx in (TL, TC, TR):
            new_rect.setTop(local.y())
        if idx in (BL, BC, BR):
            new_rect.setBottom(local.y())
        if idx in (TL, ML, BL):
            new_rect.setLeft(local.x())
        if idx in (TR, MR, BR):
            new_rect.setRight(local.x())
        new_rect = new_rect.normalized()
        if new_rect.width() > 5 and new_rect.height() > 5:
            parent.setRect(new_rect)
            parent._update_handles()
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)


REPEAT_PEN        = QPen(QColor(255, 200, 0),   2, Qt.PenStyle.DashLine)
REPEAT_BRUSH      = QBrush(QColor(255, 200, 0,  40))
SUBGROUP_PEN      = QPen(QColor(6,  182, 212),  2, Qt.PenStyle.DashDotLine)
SUBGROUP_BRUSH    = QBrush(QColor(6, 182, 212,  35))
GROUP_ANCHOR_PEN  = QPen(QColor(168, 85, 247),  2, Qt.PenStyle.DashLine)
GROUP_ANCHOR_BRUSH= QBrush(QColor(168, 85, 247, 40))
CONCAT_PEN        = QPen(QColor(249, 115, 22),  2, Qt.PenStyle.DotLine)
CONCAT_BRUSH      = QBrush(QColor(249, 115, 22, 40))


class BoxItem(QGraphicsRectItem):
    """A labelled bounding box with 8 resize handles that appear on selection.

    Colours:
      red solid       — normal field
      yellow dashed   — repeat (header value stamped on every row)
      teal dash-dot   — sub_group (value shared across a group of rows; fill-forward)
    """

    def __init__(self, rect: QRectF, field_name: str = "",
                 repeat: bool = False, sub_group: bool = False,
                 group_anchor: bool = False, concat_in_group: bool = False,
                 currency: bool = False,
                 date_format: str = "",
                 canvas: "CanvasWidget | None" = None):
        super().__init__(rect)
        self._canvas             = canvas
        self._move_undo_pushed   = False
        self.field_name          = field_name
        self.repeat              = repeat
        self.sub_group           = sub_group
        self.group_anchor        = group_anchor
        self.concat_in_group     = concat_in_group
        self.currency            = currency
        self.date_format         = date_format
        self._apply_style()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self._update_tooltip()

        self._handles = [_ResizeHandle(self, i) for i in range(8)]
        self._update_handles()

    def _apply_style(self):
        if self.group_anchor:
            self.setPen(GROUP_ANCHOR_PEN)
            self.setBrush(GROUP_ANCHOR_BRUSH)
        elif self.concat_in_group:
            self.setPen(CONCAT_PEN)
            self.setBrush(CONCAT_BRUSH)
        elif self.sub_group:
            self.setPen(SUBGROUP_PEN)
            self.setBrush(SUBGROUP_BRUSH)
        elif self.repeat:
            self.setPen(REPEAT_PEN)
            self.setBrush(REPEAT_BRUSH)
        else:
            self.setPen(RED_PEN)
            self.setBrush(RED_BRUSH)

    def _update_tooltip(self):
        if self.group_anchor:
            suffix = " [group anchor: new transaction starts here]"
        elif self.concat_in_group:
            suffix = " [concat: values joined across group rows]"
        elif self.sub_group:
            suffix = " [sub-group: value shared across rows]"
        elif self.repeat:
            suffix = " [repeats every row]"
        else:
            suffix = ""
        currency_note = " [$: 2dp currency normalisation]" if self.currency else ""
        date_note     = f" [date format: {self.date_format}]" if self.date_format else ""
        self.setToolTip(f"{self.field_name}{suffix}{currency_note}{date_note}")

    def set_repeat(self, value: bool):
        self.repeat = value
        if value:
            self.sub_group = self.group_anchor = self.concat_in_group = False
        self._apply_style()
        self._update_tooltip()
        self.update()

    def set_sub_group(self, value: bool):
        self.sub_group = value
        if value:
            self.repeat = self.group_anchor = self.concat_in_group = False
        self._apply_style()
        self._update_tooltip()
        self.update()

    def set_group_anchor(self, value: bool):
        self.group_anchor = value
        if value:
            self.repeat = self.sub_group = self.concat_in_group = False
        self._apply_style()
        self._update_tooltip()
        self.update()

    def set_concat_in_group(self, value: bool):
        self.concat_in_group = value
        if value:
            self.repeat = self.sub_group = self.group_anchor = False
        self._apply_style()
        self._update_tooltip()
        self.update()

    def set_currency(self, value: bool):
        self.currency = value
        self._update_tooltip()
        self.update()

    def set_date_format(self, value: str):
        self.date_format = value
        self._update_tooltip()
        self.update()

    def _update_handles(self):
        for h in self._handles:
            h.update_pos()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            if not self._move_undo_pushed and self._canvas is not None:
                self._canvas.push_undo()
                self._move_undo_pushed = True
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            for h in self._handles:
                h.setVisible(bool(value))
        return super().itemChange(change, value)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self._move_undo_pushed = False

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        if self.field_name:
            painter.setPen(QPen(QColor(255, 255, 255)))
            r = self.rect()
            if self.group_anchor:
                label = f"⊕ {self.field_name}"
            elif self.concat_in_group:
                label = f"∑ {self.field_name}"
            elif self.sub_group:
                label = f"⊞ {self.field_name}"
            elif self.repeat:
                label = f"↺ {self.field_name}"
            else:
                label = self.field_name
            if self.currency:
                label = f"{label} $"
            painter.drawText(int(r.x()) + 3, int(r.y()) + 14, label)


class CanvasWidget(QGraphicsView):
    """
    Displays a PIL image and lets the user draw red rectangles.
    Scene coordinates == source image pixels (image placed at origin 0,0).
    """

    box_drawn    = pyqtSignal(QRectF)
    box_removed  = pyqtSignal(int)
    box_selected = pyqtSignal(int)   # index into _boxes list; -1 = none
    boxes_changed = pyqtSignal()     # emitted after undo/redo restores state

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

        self._undo_stack: list[list[dict]] = []
        self._redo_stack: list[list[dict]] = []
        self._restoring  = False

        self._scene.selectionChanged.connect(self._on_selection_changed)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # ── Selection sync ────────────────────────────────────────────────────────

    def _on_selection_changed(self):
        for i, box in enumerate(self._boxes):
            if box.isSelected():
                self.box_selected.emit(i)
                return
        self.box_selected.emit(-1)

    def select_box_by_index(self, index: int):
        """Select a box by list index (called when user clicks the field list)."""
        self._scene.clearSelection()
        if 0 <= index < len(self._boxes):
            self._boxes[index].setSelected(True)

    # ── Image loading ─────────────────────────────────────────────────────────

    def set_image(self, img: Image.Image):
        self._undo_stack.clear()
        self._redo_stack.clear()
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

        self.resetTransform()
        QTimer.singleShot(50, self._fit_image)

    def fit_image(self):
        """Public slot wired to the 'Fit Image' button."""
        self._fit_image()

    def _fit_image(self):
        if self._pixmap_item and self._image_loaded:
            self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
            self.viewport().update()

    def clear_image(self):
        """Remove the background image and all boxes, leaving a blank canvas."""
        self._scene.clear()
        self._boxes.clear()
        self._pixmap_item = None
        self._image_loaded = False
        self._temp_rect = None

    # ── Box management ────────────────────────────────────────────────────────

    def clear_boxes(self):
        for b in self._boxes:
            self._scene.removeItem(b)
        self._boxes.clear()

    def load_boxes(self, field_defs: list[dict], img_w: float, img_h: float):
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.clear_boxes()
        for f in field_defs:
            x0, y0, x1, y1 = f["bbox"]
            self._add_box(QRectF(x0, y0, x1 - x0, y1 - y0), f["name"],
                          repeat=f.get("repeat", False),
                          sub_group=f.get("sub_group", False),
                          group_anchor=f.get("group_anchor", False),
                          concat_in_group=f.get("concat_in_group", False),
                          currency=f.get("currency", False),
                          date_format=f.get("date_format", ""))

    def _add_box(self, rect: QRectF, field_name: str,
                 repeat: bool = False, sub_group: bool = False,
                 group_anchor: bool = False, concat_in_group: bool = False,
                 currency: bool = False, date_format: str = "") -> BoxItem:
        box = BoxItem(rect, field_name, repeat=repeat, sub_group=sub_group,
                      group_anchor=group_anchor, concat_in_group=concat_in_group,
                      currency=currency, date_format=date_format, canvas=self)
        self._scene.addItem(box)
        self._boxes.append(box)
        return box

    def add_named_box(self, rect: QRectF, field_name: str,
                      repeat: bool = False, sub_group: bool = False,
                      group_anchor: bool = False, concat_in_group: bool = False,
                      currency: bool = False, date_format: str = ""):
        self._add_box(rect, field_name, repeat=repeat, sub_group=sub_group,
                      group_anchor=group_anchor, concat_in_group=concat_in_group,
                      currency=currency, date_format=date_format)

    def set_box_repeat(self, index: int, value: bool):
        if 0 <= index < len(self._boxes):
            self._boxes[index].set_repeat(value)

    def set_box_sub_group(self, index: int, value: bool):
        if 0 <= index < len(self._boxes):
            self._boxes[index].set_sub_group(value)

    def set_box_group_anchor(self, index: int, value: bool):
        if 0 <= index < len(self._boxes):
            self._boxes[index].set_group_anchor(value)

    def set_box_concat_in_group(self, index: int, value: bool):
        if 0 <= index < len(self._boxes):
            self._boxes[index].set_concat_in_group(value)

    def set_box_currency(self, index: int, value: bool):
        if 0 <= index < len(self._boxes):
            self._boxes[index].set_currency(value)

    def set_box_date_format(self, index: int, value: str):
        if 0 <= index < len(self._boxes):
            self._boxes[index].set_date_format(value)

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
                "name":           box.field_name,
                "label":          box.field_name.replace("_", " ").title(),
                "page":           0,
                "bbox":           [round(r.x(), 2), round(r.y(), 2),
                                   round(r.x() + r.width(), 2), round(r.y() + r.height(), 2)],
                "repeat":         box.repeat,
                "sub_group":      box.sub_group,
                "group_anchor":   box.group_anchor,
                "concat_in_group":box.concat_in_group,
                "currency":       box.currency,
                "date_format":    box.date_format,
            })
        return defs

    # ── Undo / redo ───────────────────────────────────────────────────────────

    def _snapshot(self) -> list[dict]:
        return [dict(d) for d in self.get_field_defs()]

    def push_undo(self):
        if self._restoring:
            return
        self._undo_stack.append(self._snapshot())
        if len(self._undo_stack) > 50:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self):
        if not self._undo_stack:
            return
        self._redo_stack.append(self._snapshot())
        self._restore_snapshot(self._undo_stack.pop())

    def redo(self):
        if not self._redo_stack:
            return
        self._undo_stack.append(self._snapshot())
        self._restore_snapshot(self._redo_stack.pop())

    def _restore_snapshot(self, state: list[dict]):
        self._restoring = True
        try:
            for b in self._boxes:
                self._scene.removeItem(b)
            self._boxes.clear()
            for f in state:
                x0, y0, x1, y1 = f["bbox"]
                self._add_box(
                    QRectF(x0, y0, x1 - x0, y1 - y0),
                    f["name"],
                    repeat=f.get("repeat", False),
                    sub_group=f.get("sub_group", False),
                    group_anchor=f.get("group_anchor", False),
                    concat_in_group=f.get("concat_in_group", False),
                    currency=f.get("currency", False),
                    date_format=f.get("date_format", ""),
                )
        finally:
            self._restoring = False
        self.boxes_changed.emit()

    # ── Mouse drawing ─────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            # Only start drawing if clicking on empty canvas (not an existing box/handle)
            items = self._scene.items(scene_pos)
            non_bg = [i for i in items if not isinstance(i, QGraphicsPixmapItem)]
            if not non_bg:
                self._drawing = True
                self._draw_start = scene_pos
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

    # ── Zoom / resize ─────────────────────────────────────────────────────────

    def keyPressEvent(self, event):
        ctrl  = event.modifiers() & Qt.KeyboardModifier.ControlModifier
        shift = event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        if ctrl and event.key() == Qt.Key.Key_Z:
            if shift:
                self.redo()
            else:
                self.undo()
            event.accept()
        elif ctrl and event.key() == Qt.Key.Key_Y:
            self.redo()
            event.accept()
        elif event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.push_undo()
            self.remove_selected_box()
        else:
            super().keyPressEvent(event)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(10, self._fit_image)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_image()
