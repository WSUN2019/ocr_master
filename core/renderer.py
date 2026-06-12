"""
PDF page rendering and coordinate scaling between canvas pixels and PDF points.
"""
import io
from dataclasses import dataclass
from typing import Optional

import fitz  # pymupdf
from PIL import Image

CANVAS_WIDTH = 900  # fixed display width in pixels


@dataclass
class PageRender:
    image: Image.Image
    scale_x: float   # pixels per PDF point (x)
    scale_y: float   # pixels per PDF point (y)
    width_pts: float
    height_pts: float
    canvas_w: int
    canvas_h: int


def render_page(pdf_bytes: bytes, page_index: int = 0, canvas_width: int = CANVAS_WIDTH) -> PageRender:
    """Render a PDF page to a PIL Image scaled to canvas_width pixels wide."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_index]
    rect = page.rect

    width_pts = rect.width
    height_pts = rect.height

    scale = canvas_width / width_pts
    canvas_h = int(height_pts * scale)

    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    doc.close()

    return PageRender(
        image=img,
        scale_x=scale,
        scale_y=scale,
        width_pts=width_pts,
        height_pts=height_pts,
        canvas_w=pix.width,
        canvas_h=pix.height,
    )


def page_count(pdf_bytes: bytes) -> int:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    n = doc.page_count
    doc.close()
    return n


def canvas_bbox_to_pdf(bbox_px: list[float], render: PageRender) -> list[float]:
    """Convert [x0,y0,x1,y1] in canvas pixels to PDF points."""
    x0, y0, x1, y1 = bbox_px
    return [
        x0 / render.scale_x,
        y0 / render.scale_y,
        x1 / render.scale_x,
        y1 / render.scale_y,
    ]


def pdf_bbox_to_canvas(bbox_pts: list[float], render: PageRender) -> list[float]:
    """Convert [x0,y0,x1,y1] in PDF points to canvas pixels."""
    x0, y0, x1, y1 = bbox_pts
    return [
        x0 * render.scale_x,
        y0 * render.scale_y,
        x1 * render.scale_x,
        y1 * render.scale_y,
    ]


def image_to_bytes(img: Image.Image, fmt: str = "PNG") -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()
