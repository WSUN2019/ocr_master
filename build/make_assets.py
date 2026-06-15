"""Generate MSIX placeholder assets for OCR Master."""

import os
import math
from PIL import Image, ImageDraw

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "msix", "Assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

# Palette
BG_TOP    = (18, 42, 74)     # #122a4a  deep navy
BG_BOT    = (28, 62, 106)    # #1c3e6a  slightly lighter
WHITE     = (255, 255, 255)
ACCENT    = (82, 162, 224)   # #52a2e0  sky blue
DOC       = (220, 238, 252)  # very pale blue — document face
DOC_FOLD  = (170, 205, 235)  # folded corner
LINE      = (120, 170, 215)  # text-line marks on document


# ── helpers ──────────────────────────────────────────────────────────────────

def gradient_bg(img: Image.Image):
    draw = ImageDraw.Draw(img)
    w, h = img.size
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * t)
        draw.line([(0, y), (w - 1, y)], fill=(r, g, b))


def document(draw: ImageDraw.ImageDraw, x, y, w, h):
    """Document shape with folded top-right corner."""
    fold = max(4, int(w * 0.22))
    body = [
        (x,         y),
        (x + w - fold, y),
        (x + w,     y + fold),
        (x + w,     y + h),
        (x,         y + h),
    ]
    draw.polygon(body, fill=DOC)
    # fold triangle
    draw.polygon(
        [(x + w - fold, y), (x + w, y + fold), (x + w - fold, y + fold)],
        fill=DOC_FOLD,
    )
    # text lines (3 lines, last one shorter)
    lx = x + max(2, int(w * 0.12))
    lw = int(w * 0.65)
    lh = max(1, int(h * 0.06))
    gap = int(h * 0.13)
    for i, frac in enumerate([1.0, 1.0, 0.6]):
        ly = y + int(h * 0.35) + i * gap
        draw.rectangle([lx, ly, lx + int(lw * frac), ly + lh], fill=LINE)


def magnifier(draw: ImageDraw.ImageDraw, cx, cy, r, lw):
    """Magnifying glass circle + handle at 45°."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ACCENT, width=lw)
    # inner highlight arc suggestion — just a thinner inner ring
    ir = max(1, r - lw - 1)
    if ir > 1:
        draw.ellipse(
            [cx - ir, cy - ir, cx + ir, cy + ir],
            outline=(*ACCENT[:3], 80),  # semi-transparent tint
            width=max(1, lw - 1),
        )
    # handle
    angle = math.pi / 4
    hx1 = int(cx + r * math.cos(angle))
    hy1 = int(cy + r * math.sin(angle))
    hlen = int(r * 1.1)
    hx2 = int(cx + (r + hlen) * math.cos(angle))
    hy2 = int(cy + (r + hlen) * math.sin(angle))
    draw.line([hx1, hy1, hx2, hy2], fill=ACCENT, width=lw + 1)


def text_label(draw: ImageDraw.ImageDraw, img_w, img_h, lines, sizes):
    """Draw stacked centred text using PIL's default bitmap font (scaled via resize)."""
    # We'll draw text on an oversized surface then composite — simpler: just
    # draw directly using a stroke trick for weight.
    from PIL import ImageFont
    y = img_h // 2
    total_h = sum(s + 4 for s in sizes)
    y -= total_h // 2
    for line, size in zip(lines, sizes):
        # Use default font scaled by drawing on temp image
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", size)
        except Exception:
            try:
                font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", size)
            except Exception:
                font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        tx = (img_w - tw) // 2 - bbox[0]
        # thin shadow
        draw.text((tx + 1, y + 1), line, font=font, fill=(0, 0, 0, 80))
        draw.text((tx, y), line, font=font, fill=WHITE)
        y += (bbox[3] - bbox[1]) + 6


# ── per-size generators ───────────────────────────────────────────────────────

def make_square_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gradient_bg(img)
    draw = ImageDraw.Draw(img, "RGBA")
    pad = max(4, int(size * 0.12))
    doc_w = int(size * 0.52)
    doc_h = int(size * 0.62)
    doc_x = pad
    doc_y = int(size * 0.12)
    document(draw, doc_x, doc_y, doc_w, doc_h)
    mag_r = max(4, int(size * 0.18))
    lw    = max(2, int(size * 0.055))
    mag_cx = int(size * 0.62)
    mag_cy = int(size * 0.52)
    magnifier(draw, mag_cx, mag_cy, mag_r, lw)
    return img


def make_square150() -> Image.Image:
    size = 150
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gradient_bg(img)
    draw = ImageDraw.Draw(img, "RGBA")
    document(draw, 18, 18, 74, 90)
    magnifier(draw, 96, 82, 30, 5)
    text_label(draw, size, size - 12, ["OCR"], [18])
    # push label to bottom quarter
    from PIL import ImageFont
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 16)
    except Exception:
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 16)
        except Exception:
            font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), "OCR Master", font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((size - tw) // 2 - bbox[0] + 1, 122), "OCR Master", font=font, fill=(0, 0, 0, 80))
    draw.text(((size - tw) // 2 - bbox[0],     121), "OCR Master", font=font, fill=WHITE)
    return img


def make_wide310x150() -> Image.Image:
    W, H = 310, 150
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gradient_bg(img)
    draw = ImageDraw.Draw(img, "RGBA")
    # icon left side
    doc_x, doc_y, doc_w, doc_h = 20, 18, 72, 88
    document(draw, doc_x, doc_y, doc_w, doc_h)
    magnifier(draw, 108, 72, 26, 5)
    # text right side
    from PIL import ImageFont
    try:
        font_big = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 32)
    except Exception:
        try:
            font_big = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 32)
        except Exception:
            font_big = ImageFont.load_default()
    try:
        font_sm = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 16)
    except Exception:
        try:
            font_sm = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 16)
        except Exception:
            font_sm = ImageFont.load_default()
    tx = 148
    draw.text((tx + 1, 41), "OCR", font=font_big, fill=(0, 0, 0, 80))
    draw.text((tx,     40), "OCR", font=font_big, fill=WHITE)
    draw.text((tx + 1, 81), "Master", font=font_big, fill=(0, 0, 0, 80))
    draw.text((tx,     80), "Master", font=font_big, fill=WHITE)
    draw.text((tx + 1, 117), "Bank Statement Extractor", font=font_sm, fill=(0, 0, 0, 60))
    draw.text((tx,     116), "Bank Statement Extractor", font=font_sm, fill=(*ACCENT,))
    return img


def make_splash620x300() -> Image.Image:
    W, H = 620, 300
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gradient_bg(img)
    draw = ImageDraw.Draw(img, "RGBA")
    # large icon centred-left
    icon_cx = 160
    document(draw, icon_cx - 60, 50, 90, 110)
    magnifier(draw, icon_cx + 44, 118, 40, 7)
    # text right of icon
    from PIL import ImageFont
    try:
        font_title = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 52)
    except Exception:
        try:
            font_title = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 52)
        except Exception:
            font_title = ImageFont.load_default()
    try:
        font_sub = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 20)
    except Exception:
        try:
            font_sub = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 20)
        except Exception:
            font_sub = ImageFont.load_default()
    tx = 280
    draw.text((tx + 2, 72), "OCR Master", font=font_title, fill=(0, 0, 0, 90))
    draw.text((tx,     70), "OCR Master", font=font_title, fill=WHITE)
    draw.text((tx + 1, 133), "Bank Statement Extractor", font=font_sub, fill=(0, 0, 0, 60))
    draw.text((tx,     132), "Bank Statement Extractor", font=font_sub, fill=(*ACCENT,))
    # thin accent line under title
    b = draw.textbbox((0, 0), "OCR Master", font=font_title)
    line_y = 130
    draw.rectangle([tx, line_y, tx + b[2] - b[0], line_y + 2], fill=ACCENT)
    return img


# ── generate ──────────────────────────────────────────────────────────────────

assets = [
    ("StoreLogo.png",          make_square_icon(50)),
    ("Square44x44Logo.png",    make_square_icon(44)),
    ("Square150x150Logo.png",  make_square150()),
    ("Wide310x150Logo.png",    make_wide310x150()),
    ("SplashScreen.png",       make_splash620x300()),
]

for fname, img in assets:
    path = os.path.join(ASSETS_DIR, fname)
    img.save(path, "PNG")
    print(f"  Saved {fname}  ({img.width}x{img.height})")

print("\nDone. Assets in:", ASSETS_DIR)
