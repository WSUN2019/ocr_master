"""
Open PDFs or images for display and coordinate scaling between canvas pixels and source pixels/points.
"""
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import fitz  # pymupdf
from PIL import Image

CANVAS_WIDTH = 900  # fixed display width in pixels


@dataclass
class PageRender:
    image: Image.Image
    scale_x: float   # canvas pixels per source unit (pt or px)
    scale_y: float
    width_pts: float  # source width in pts (PDFs) or px (images)
    height_pts: float
    canvas_w: int
    canvas_h: int
    source_type: str  # "pdf" or "image"


# ── PDF support ───────────────────────────────────────────────────────────────

def render_pdf_page(pdf_bytes: bytes, page_index: int = 0, canvas_width: int = CANVAS_WIDTH) -> PageRender:
    """Render a PDF page to a PIL Image scaled to canvas_width pixels wide."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_index]
    rect = page.rect
    width_pts, height_pts = rect.width, rect.height

    scale = canvas_width / width_pts
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
        source_type="pdf",
    )


def pdf_page_count(pdf_bytes: bytes) -> int:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    n = doc.page_count
    doc.close()
    return n


# ── Image support ─────────────────────────────────────────────────────────────

def render_image(image_bytes: bytes, canvas_width: int = CANVAS_WIDTH) -> PageRender:
    """Open a JPG/PNG image and scale it to canvas_width for display."""
    img_src = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = img_src.size

    scale = canvas_width / w
    canvas_h = int(h * scale)
    img_display = img_src.resize((canvas_width, canvas_h), Image.LANCZOS)

    return PageRender(
        image=img_display,
        scale_x=scale,
        scale_y=scale,
        width_pts=float(w),   # source pixels, called "pts" for consistency
        height_pts=float(h),
        canvas_w=canvas_width,
        canvas_h=canvas_h,
        source_type="image",
    )


def open_source_image(image_bytes: bytes, filename: str = "") -> Image.Image:
    """Return the full-resolution source image (for OCR cropping and canvas display)."""
    ext = Path(filename).suffix.lower() if filename else ""
    if ext == ".pdf":
        doc = fitz.open(stream=image_bytes, filetype="pdf")
        page = doc[0]
        mat = fitz.Matrix(2.0, 2.0)  # 144 DPI — good for display + template mapping
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()
        return img
    return Image.open(io.BytesIO(image_bytes)).convert("RGB")


# ── Unified entry point ───────────────────────────────────────────────────────

def render_file(file_bytes: bytes, filename: str, page_index: int = 0) -> PageRender:
    """
    Detect file type by extension and render for canvas display.
    For PDFs renders the given page; for images renders the single image.
    """
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return render_pdf_page(file_bytes, page_index=page_index)
    else:
        return render_image(file_bytes)


def file_page_count(file_bytes: bytes, filename: str) -> int:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return pdf_page_count(file_bytes)
    return 1


# ── Coordinate conversion (same math for PDF and images) ─────────────────────

def canvas_bbox_to_source(bbox_px: list[float], render: PageRender) -> list[float]:
    """Convert [x0,y0,x1,y1] in canvas pixels → source units (PDF pts or image px)."""
    x0, y0, x1, y1 = bbox_px
    return [
        x0 / render.scale_x,
        y0 / render.scale_y,
        x1 / render.scale_x,
        y1 / render.scale_y,
    ]


def source_bbox_to_canvas(bbox_src: list[float], render: PageRender) -> list[float]:
    """Convert [x0,y0,x1,y1] in source units → canvas pixels."""
    x0, y0, x1, y1 = bbox_src
    return [
        x0 * render.scale_x,
        y0 * render.scale_y,
        x1 * render.scale_x,
        y1 * render.scale_y,
    ]


# Keep old names as aliases so pages don't break
def canvas_bbox_to_pdf(bbox_px, render):
    return canvas_bbox_to_source(bbox_px, render)

def pdf_bbox_to_canvas(bbox_pts, render):
    return source_bbox_to_canvas(bbox_pts, render)

def page_count(pdf_bytes):
    return pdf_page_count(pdf_bytes)

def render_page(pdf_bytes, page_index=0, canvas_width=CANVAS_WIDTH):
    return render_pdf_page(pdf_bytes, page_index, canvas_width)


def image_to_bytes(img: Image.Image, fmt: str = "PNG") -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()
