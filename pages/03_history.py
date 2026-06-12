"""
History page — query SQLite transactions, filter, re-export CSV, delete batches.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd

from core.storage import query_transactions, query_import_log, delete_by_source, df_to_csv_bytes, init_db
from core.template import template_names

st.set_page_config(page_title="History", layout="wide")
st.title("Transaction History")

init_db()

# ── Filters ───────────────────────────────────────────────────────────────────
with st.expander("Filters", expanded=True):
    c1, c2, c3, c4 = st.columns(4)
    date_from = c1.date_input("From date", value=None)
    date_to   = c2.date_input("To date",   value=None)
    tnames    = ["All"] + template_names()
    tpl_filter = c3.selectbox("Template", tnames)
    limit     = c4.number_input("Max rows", min_value=100, max_value=50000, value=5000, step=500)

df = query_transactions(
    date_from=str(date_from) if date_from else None,
    date_to=str(date_to) if date_to else None,
    template_name=tpl_filter if tpl_filter != "All" else None,
    limit=int(limit),
)

st.subheader(f"{len(df)} transactions")

if df.empty:
    st.info("No transactions in the database yet. Use the Extract page to import statements.")
else:
    st.dataframe(df, use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        csv_bytes = df_to_csv_bytes(df)
        st.download_button("⬇ Export filtered CSV", data=csv_bytes, file_name="history_export.csv", mime="text/csv")

    with c2:
        sources = df["source_file"].dropna().unique().tolist() if "source_file" in df.columns else []
        if sources:
            to_delete = st.selectbox("Delete batch by file", ["— select —"] + sources)
            if to_delete != "— select —":
                if st.button("🗑 Delete this batch", type="secondary"):
                    n = delete_by_source(to_delete)
                    st.success(f"Deleted {n} rows from '{to_delete}'")
                    st.rerun()

# ── Import log ────────────────────────────────────────────────────────────────
st.divider()
st.subheader("Import Log")
log_df = query_import_log()
if log_df.empty:
    st.caption("No imports recorded.")
else:
    st.dataframe(log_df, use_container_width=True, hide_index=True)
