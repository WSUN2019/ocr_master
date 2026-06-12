"""
Extract page — upload PDFs, pick a template, run extraction, review table, save to DB / export CSV.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st

from core.extractor import extract_with_template, extract_table_mode
from core.renderer import render_page, page_count
from core.storage import insert_transactions, df_to_csv_bytes, init_db
from core.template import list_templates, load_template

st.set_page_config(page_title="Extract", layout="wide")
st.title("Extract Transactions")

init_db()

# ── Template selection ────────────────────────────────────────────────────────
templates = list_templates()
if not templates:
    st.warning("No templates saved yet. Go to **Template Builder** to create one first.")
    st.stop()

tpl_map = {t["name"]: t["slug"] for t in templates}
col1, col2 = st.columns([2, 1])
with col1:
    chosen_name = st.selectbox("Select template", list(tpl_map.keys()))
with col2:
    mode = st.selectbox("Extraction mode", ["Template (bbox)", "Auto table detect"])

template = load_template(tpl_map[chosen_name])

# ── Upload PDFs ───────────────────────────────────────────────────────────────
st.subheader("Upload PDF(s)")
uploaded_files = st.file_uploader(
    "Choose one or more PDF statements",
    type=["pdf"],
    accept_multiple_files=True,
    key="extract_upload",
)

if not uploaded_files:
    st.info("Upload one or more PDFs to begin.")
    st.stop()

# ── Run extraction ────────────────────────────────────────────────────────────
if "extracted_df" not in st.session_state:
    st.session_state.extracted_df = None
    st.session_state.extracted_source = None

if st.button("▶ Run Extraction", type="primary"):
    all_rows = []
    progress = st.progress(0)
    for i, f in enumerate(uploaded_files):
        pdf_bytes = f.read()
        with st.spinner(f"Processing {f.name}…"):
            try:
                if mode == "Auto table detect":
                    rows = extract_table_mode(pdf_bytes)
                else:
                    rows = extract_with_template(pdf_bytes, template)
                for r in rows:
                    r["_source_file"] = f.name
                all_rows.extend(rows)
            except Exception as e:
                st.error(f"Error processing {f.name}: {e}")
        progress.progress((i + 1) / len(uploaded_files))

    if all_rows:
        df = pd.DataFrame(all_rows)
        # move internal cols to end
        front = [c for c in df.columns if not c.startswith("_")]
        back = [c for c in df.columns if c.startswith("_")]
        df = df[front + back]
        st.session_state.extracted_df = df
        st.session_state.extracted_source = [f.name for f in uploaded_files]
        st.success(f"Extracted **{len(df)} rows** from {len(uploaded_files)} file(s).")
    else:
        st.warning("No rows extracted. Check template alignment or try Auto table detect.")

# ── Review table ─────────────────────────────────────────────────────────────
if st.session_state.extracted_df is not None:
    df = st.session_state.extracted_df

    st.subheader(f"Review — {len(df)} rows")

    # Quick filters
    with st.expander("Filter / search"):
        col_a, col_b = st.columns(2)
        search = col_a.text_input("Search description")
        if search:
            df = df[df.get("description", pd.Series(dtype=str)).astype(str).str.contains(search, case=False, na=False)]
        min_amt = col_b.number_input("Min amount", value=None, placeholder="e.g. -500")
        if min_amt is not None and "amount" in df.columns:
            df = df[df["amount"] >= min_amt]

    edited = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        key="edit_table",
    )
    st.session_state.extracted_df = edited

    # ── Actions ───────────────────────────────────────────────────────────────
    st.subheader("Actions")
    c1, c2 = st.columns(2)

    with c1:
        csv_bytes = df_to_csv_bytes(edited)
        st.download_button(
            label="⬇ Download CSV",
            data=csv_bytes,
            file_name="transactions.csv",
            mime="text/csv",
        )

    with c2:
        if st.button("💾 Save to Database", type="primary"):
            total = 0
            for src_file in (st.session_state.extracted_source or []):
                subset = edited[edited.get("_source_file", pd.Series(dtype=str)) == src_file] if "_source_file" in edited.columns else edited
                rows_dicts = subset.to_dict("records")
                n = insert_transactions(rows_dicts, source_file=src_file, template_name=chosen_name)
                total += n
            st.success(f"Saved **{total} rows** to database.")

    # ── PDF preview (first uploaded) ──────────────────────────────────────────
    with st.expander("Preview first PDF page"):
        first_pdf = uploaded_files[0].read() if uploaded_files else None
        if first_pdf:
            render = render_page(first_pdf, page_index=0)
            st.image(render.image, caption=uploaded_files[0].name, use_container_width=True)
