"""
OCR Master — Bank Statement Extractor
Entry point. Run with: streamlit run app.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from core.storage import init_db

st.set_page_config(
    page_title="OCR Master",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

st.title("OCR Master")
st.subheader("Bank Statement Extractor — 100% Local")

st.markdown("""
All processing happens on your machine. No data is sent externally.

---

### How to use

| Step | Page | What you do |
|------|------|-------------|
| **1** | Template Builder | Upload a sample PDF, draw red boxes over each field, label them, save as a named template |
| **2** | Extract | Upload your statements, pick the matching template, run extraction, review the table |
| **3** | History | Browse all imported transactions, filter by date or template, export CSV |
| **4** | Settings | Manage templates, backup or compact the database |

---

### Quick start

Use the **sidebar** to navigate between pages.

> **Tip:** Start by going to **Template Builder** with one sample statement from each bank format you have.
> Once you have templates A, B, C, D saved, batch-extract all your statements in **Extract**.
""")

st.divider()
col1, col2, col3 = st.columns(3)
from core.storage import query_transactions, query_import_log, db_size_mb
from core.template import list_templates

try:
    df = query_transactions(limit=1)
    total = query_transactions(limit=100000)
    col1.metric("Total transactions", len(total))
except Exception:
    col1.metric("Total transactions", "—")

try:
    col2.metric("Templates saved", len(list_templates()))
except Exception:
    col2.metric("Templates saved", "—")

try:
    col3.metric("Database size", f"{db_size_mb():.2f} MB")
except Exception:
    col3.metric("Database size", "—")
