"""
Template Builder — draw red bounding boxes on a PDF page to define field locations.
Save mappings as named templates for reuse during extraction.
"""
import json

import pandas as pd
import streamlit as st
from streamlit_drawable_canvas import st_canvas

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.renderer import render_page, canvas_bbox_to_pdf, pdf_bbox_to_canvas, page_count, image_to_bytes
from core.template import (
    list_templates, load_template, save_template, delete_template,
    build_template, slugify
)

st.set_page_config(page_title="Template Builder", layout="wide")
st.title("Template Builder")
st.caption("Draw red boxes over each field. Label them. Save as a named template.")

# ── Sidebar: load existing or start new ──────────────────────────────────────
with st.sidebar:
    st.header("Templates")
    templates = list_templates()
    template_names = ["— New template —"] + [t["name"] for t in templates]
    selected = st.selectbox("Load existing", template_names)

    if selected != "— New template —":
        slug = next(t["slug"] for t in templates if t["name"] == selected)
        loaded = load_template(slug)
        if st.button("Delete this template", type="secondary"):
            delete_template(slug)
            st.success(f"Deleted '{selected}'")
            st.rerun()
    else:
        loaded = None

# ── Upload PDF ────────────────────────────────────────────────────────────────
st.subheader("1 · Upload a sample PDF")
uploaded = st.file_uploader("Choose a PDF", type=["pdf"], key="tb_upload")

if not uploaded:
    st.info("Upload a sample statement PDF to begin mapping fields.")
    st.stop()

pdf_bytes = uploaded.read()
n_pages = page_count(pdf_bytes)

col_a, col_b = st.columns([2, 1])
with col_a:
    page_idx = st.number_input("Page to map", min_value=0, max_value=n_pages - 1, value=0, step=1)

render = render_page(pdf_bytes, page_index=page_idx)

# ── Canvas ────────────────────────────────────────────────────────────────────
st.subheader("2 · Draw boxes over each field (red rectangles)")
st.caption(f"Page size: {render.width_pts:.1f} × {render.height_pts:.1f} pts  |  Canvas: {render.canvas_w} × {render.canvas_h} px")

# Pre-draw existing template boxes if loading
initial_drawing = {"version": "4.4.0", "objects": []}
if loaded:
    for f in loaded.get("fields", []):
        if f.get("page", 0) == page_idx:
            bpx = pdf_bbox_to_canvas(f["bbox"], render)
            initial_drawing["objects"].append({
                "type": "rect",
                "version": "4.4.0",
                "left": bpx[0],
                "top": bpx[1],
                "width": bpx[2] - bpx[0],
                "height": bpx[3] - bpx[1],
                "fill": "rgba(230,57,70,0.15)",
                "stroke": "#e63946",
                "strokeWidth": 2,
            })

canvas_result = st_canvas(
    fill_color="rgba(230, 57, 70, 0.15)",
    stroke_width=2,
    stroke_color="#e63946",
    background_image=render.image,
    update_streamlit=True,
    width=render.canvas_w,
    height=render.canvas_h,
    drawing_mode="rect",
    initial_drawing=initial_drawing if loaded else None,
    key="canvas",
)

# ── Field labeling ────────────────────────────────────────────────────────────
st.subheader("3 · Label each box with a field name")

PRESET_FIELDS = [
    "transaction_date", "post_date", "description",
    "amount", "balance", "account_number", "statement_period", "custom…"
]

objects = []
if canvas_result.json_data:
    objects = [o for o in canvas_result.json_data.get("objects", []) if o.get("type") == "rect"]

if not objects:
    st.info("Draw at least one rectangle on the PDF above.")
else:
    field_defs = []
    for i, obj in enumerate(objects):
        left = obj.get("left", 0)
        top = obj.get("top", 0)
        width = obj.get("width", 0) * obj.get("scaleX", 1)
        height = obj.get("height", 0) * obj.get("scaleY", 1)
        bbox_px = [left, top, left + width, top + height]
        bbox_pts = canvas_bbox_to_pdf(bbox_px, render)

        c1, c2, c3 = st.columns([2, 2, 3])
        with c1:
            preset = st.selectbox(f"Box {i+1} field", PRESET_FIELDS, key=f"preset_{i}")
        with c2:
            if preset == "custom…":
                fname = st.text_input(f"Custom name", key=f"custom_{i}", placeholder="my_field_name")
            else:
                fname = preset
                st.markdown(f"**`{fname}`**")
        with c3:
            st.caption(
                f"PDF bbox: [{bbox_pts[0]:.1f}, {bbox_pts[1]:.1f}, {bbox_pts[2]:.1f}, {bbox_pts[3]:.1f}] pts"
            )

        if fname:
            field_defs.append({
                "name": fname,
                "label": fname.replace("_", " ").title(),
                "page": page_idx,
                "bbox": [round(v, 2) for v in bbox_pts],
            })

    # ── Row detection config ──────────────────────────────────────────────────
    st.subheader("4 · Row detection")
    strategy = st.selectbox(
        "Strategy",
        ["repeat_vertical", "fixed_regions", "table_detect"],
        help="repeat_vertical: rows repeat at a fixed height. fixed_regions: one-off labeled areas. table_detect: auto-detect PDF table."
    )

    row_detection = {"strategy": strategy}

    if strategy == "repeat_vertical":
        c1, c2, c3 = st.columns(3)
        anchor = field_defs[0]["name"] if field_defs else ""
        row_h = c1.number_input("Row height (pts)", min_value=4.0, max_value=100.0, value=12.0, step=0.5)
        start_y = c2.number_input("Start Y (pts)", min_value=0.0, max_value=render.height_pts, value=field_defs[0]["bbox"][1] if field_defs else 0.0, step=1.0)
        end_y = c3.number_input("End Y (pts)", min_value=0.0, max_value=render.height_pts, value=render.height_pts - 50.0, step=1.0)
        row_detection.update({
            "anchor_field": anchor,
            "row_height_pts": row_h,
            "start_y_pts": start_y,
            "end_y_pts": end_y,
        })

    # ── Save ─────────────────────────────────────────────────────────────────
    st.subheader("5 · Save template")
    default_name = loaded["name"] if loaded else ""
    tpl_name = st.text_input("Template name (e.g. Chase Checking 2024)", value=default_name)

    if st.button("💾 Save Template", type="primary", disabled=not tpl_name or not field_defs):
        tpl = build_template(
            name=tpl_name,
            page_width_pts=render.width_pts,
            page_height_pts=render.height_pts,
            fields=field_defs,
            row_detection=row_detection,
            source_page=page_idx,
        )
        slug = save_template(tpl)
        st.success(f"Saved as **{tpl_name}** (slug: `{slug}`)")
        st.json(tpl)
