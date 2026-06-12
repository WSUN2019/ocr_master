"""
Settings page — manage templates, database maintenance.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import streamlit as st

from core.storage import vacuum_db, db_size_mb, init_db
from core.template import list_templates, load_template, delete_template, save_template

st.set_page_config(page_title="Settings", layout="wide")
st.title("Settings")

init_db()

# ── Templates ─────────────────────────────────────────────────────────────────
st.subheader("Saved Templates")
templates = list_templates()

if not templates:
    st.info("No templates yet. Create one in Template Builder.")
else:
    for t in templates:
        with st.expander(f"**{t['name']}**  `{t['slug']}`"):
            tpl = load_template(t["slug"])
            if tpl:
                fields = tpl.get("fields", [])
                st.markdown(f"**Fields ({len(fields)}):** " + ", ".join(f"`{f['name']}`" for f in fields))
                rd = tpl.get("row_detection", {})
                st.markdown(f"**Row detection:** `{rd.get('strategy','—')}` · row height `{rd.get('row_height_pts','—')} pts`")
                st.markdown(f"**Page size:** {tpl.get('page_width_pts','?')} × {tpl.get('page_height_pts','?')} pts")

                c1, c2 = st.columns(2)
                with c1:
                    st.download_button(
                        "⬇ Export JSON",
                        data=json.dumps(tpl, indent=2).encode(),
                        file_name=f"{t['slug']}.json",
                        mime="application/json",
                        key=f"dl_{t['slug']}",
                    )
                with c2:
                    if st.button(f"🗑 Delete '{t['name']}'", key=f"del_{t['slug']}", type="secondary"):
                        delete_template(t["slug"])
                        st.success(f"Deleted '{t['name']}'")
                        st.rerun()

# ── Import template JSON ──────────────────────────────────────────────────────
st.divider()
st.subheader("Import Template from JSON")
uploaded_tpl = st.file_uploader("Upload a template .json file", type=["json"], key="tpl_import")
if uploaded_tpl:
    try:
        tpl_data = json.loads(uploaded_tpl.read())
        st.json(tpl_data)
        if st.button("Import this template", type="primary"):
            slug = save_template(tpl_data)
            st.success(f"Imported as `{slug}`")
            st.rerun()
    except Exception as e:
        st.error(f"Invalid JSON: {e}")

# ── Database ──────────────────────────────────────────────────────────────────
st.divider()
st.subheader("Database")
size = db_size_mb()
st.metric("Database size", f"{size:.2f} MB")

c1, c2 = st.columns(2)
with c1:
    if st.button("Run VACUUM (compact DB)"):
        vacuum_db()
        st.success("Database vacuumed.")
with c2:
    db_path = Path(__file__).parent.parent / "ocr_master.db"
    if db_path.exists():
        st.download_button(
            "⬇ Backup database file",
            data=db_path.read_bytes(),
            file_name="ocr_master_backup.db",
            mime="application/octet-stream",
        )
