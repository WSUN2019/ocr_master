"""
SQLite persistence and CSV export for extracted transaction data.
"""
import io
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from core.app_paths import APP_DIR
DB_PATH = APP_DIR / "ocr_master.db"

# Fixed columns that exist as real DB columns (for indexing / filtering)
_FIXED_COLS = {
    "transaction_date", "post_date", "description",
    "amount", "balance", "category", "account_number", "statement_period",
}


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    """Create tables if they don't exist, and migrate existing ones."""
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS transactions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_name       TEXT,
                source_file      TEXT,
                file_row         INTEGER,
                template_name    TEXT,
                account_number   TEXT,
                statement_period TEXT,
                transaction_date TEXT,
                post_date        TEXT,
                description      TEXT,
                amount           REAL,
                balance          REAL,
                category         TEXT,
                imported_at      TEXT,
                raw_data         TEXT
            );

            CREATE TABLE IF NOT EXISTS import_log (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                filename      TEXT,
                template_name TEXT,
                pages         INTEGER,
                rows_found    INTEGER,
                imported_at   TEXT,
                status        TEXT
            );
        """)
        # Migrate: add columns to existing DBs that predate this version
        for col_def in [
            "ALTER TABLE transactions ADD COLUMN raw_data TEXT",
            "ALTER TABLE transactions ADD COLUMN batch_name TEXT",
            "ALTER TABLE transactions ADD COLUMN file_row INTEGER",
            "ALTER TABLE transactions ADD COLUMN note TEXT",
        ]:
            try:
                con.execute(col_def)
            except sqlite3.OperationalError:
                pass


def insert_transactions(
    rows: list[dict],
    source_file: str,
    template_name: str,
    batch_name: str = "",
    field_map: Optional[dict] = None,
) -> int:
    """
    Insert extracted rows into the transactions table.
    source_file: original filename (e.g. ABCBank.jpg)
    batch_name:  timestamped import key (e.g. ABCBank__20260612_143000.jpg)
    All template fields are stored in raw_data JSON so history can show every column.
    Known fixed columns are also populated for filtering / sorting.
    Returns number of rows inserted.
    """
    init_db()
    now = datetime.now().isoformat()

    # Always ensure a batch_name so rows can be targeted for deletion
    if not batch_name:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = Path(source_file).stem
        ext  = Path(source_file).suffix
        batch_name = f"{stem}__{ts}{ext}"

    inserted = 0
    with _conn() as con:
        for file_row, row in enumerate(rows, start=1):
            mapped = {
                "batch_name":    batch_name,
                "source_file":   source_file,
                "file_row":      file_row,
                "template_name": template_name,
                "imported_at":   now,
            }

            # Collect all user-facing fields (skip internal _ keys)
            raw = {}
            for k, v in row.items():
                if k.startswith("_"):
                    continue
                raw[k] = v
                # Also populate fixed columns so date/amount filters work
                col = (field_map or {}).get(k, k)
                if col in _FIXED_COLS:
                    mapped[col] = v

            mapped["raw_data"] = json.dumps(raw)

            cols = ", ".join(mapped.keys())
            placeholders = ", ".join("?" * len(mapped))
            con.execute(
                f"INSERT INTO transactions ({cols}) VALUES ({placeholders})",
                list(mapped.values()),
            )
            inserted += 1

    log_import(source_file, template_name, rows_found=inserted)
    return inserted


def log_import(filename: str, template_name: str, pages: int = 0,
               rows_found: int = 0, status: str = "ok"):
    init_db()
    with _conn() as con:
        con.execute(
            "INSERT INTO import_log (filename, template_name, pages, rows_found, imported_at, status) "
            "VALUES (?,?,?,?,?,?)",
            (filename, template_name, pages, rows_found, datetime.now().isoformat(), status),
        )


def is_already_imported(filename: str) -> bool:
    """Return True if this filename appears in import_log (was previously imported)."""
    init_db()
    with _conn() as con:
        count = con.execute(
            "SELECT COUNT(*) FROM import_log WHERE filename = ?", (filename,)
        ).fetchone()[0]
        return count > 0


def update_transaction_field(row_id: int, field_name: str, new_value: str,
                             note: str = "") -> bool:
    """
    Overwrite a single field value for a transaction row.
    Updates raw_data JSON and any matching fixed column.
    Caller supplies the note; if omitted and field != 'note', a generic note is set.
    """
    init_db()
    with _conn() as con:
        row = con.execute("SELECT raw_data FROM transactions WHERE id = ?",
                          (row_id,)).fetchone()
        if not row:
            return False
        raw = json.loads(row["raw_data"] or "{}")
        raw[field_name] = new_value

        set_clauses = ["raw_data = ?"]
        params: list = [json.dumps(raw)]

        if field_name in _FIXED_COLS:
            set_clauses.append(f"{field_name} = ?")
            params.append(new_value)

        if field_name != "note":
            set_clauses.append("note = ?")
            params.append(note or f"[{field_name}] overridden")

        params.append(row_id)
        con.execute(f"UPDATE transactions SET {', '.join(set_clauses)} WHERE id = ?", params)
    return True


def query_transactions(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    template_name: Optional[str] = None,
    source_file: Optional[str] = None,
    limit: int = 5000,
) -> pd.DataFrame:
    """
    Query transactions and expand raw_data JSON into individual columns
    so every template field appears in the result.
    """
    init_db()
    clauses, params = [], []
    if date_from:
        clauses.append("(transaction_date IS NULL OR transaction_date >= ?)")
        params.append(date_from)
    if date_to:
        clauses.append("(transaction_date IS NULL OR transaction_date <= ?)")
        params.append(date_to)
    if template_name:
        clauses.append("template_name = ?")
        params.append(template_name)
    if source_file:
        clauses.append("source_file = ?")
        params.append(source_file)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT * FROM transactions {where} ORDER BY source_file, file_row, id LIMIT ?"
    params.append(limit)

    with _conn() as con:
        df = pd.read_sql_query(sql, con, params=params)

    if df.empty:
        return df

    # Expand raw_data JSON into per-template columns
    if "raw_data" in df.columns:
        expanded = df["raw_data"].apply(
            lambda x: json.loads(x) if (pd.notna(x) and x) else {}
        )
        expanded_df = pd.DataFrame(expanded.tolist(), index=df.index)

        # For columns that exist in both: prefer raw_data value when fixed col is NULL
        for col in expanded_df.columns:
            if col in df.columns:
                df[col] = df[col].where(df[col].notna(), expanded_df[col])
            else:
                df[col] = expanded_df[col]

        df = df.drop(columns=["raw_data"])

    # Column order: id first (hidden in UI), then metadata, template fields, note last
    meta = ["batch_name", "source_file", "file_row", "template_name", "imported_at"]
    fixed = [c for c in _FIXED_COLS if c in df.columns]
    template_extra = [c for c in df.columns
                      if c not in meta and c not in fixed and c not in ("id", "note")]
    ordered = ["id"] + [c for c in meta + fixed + template_extra if c in df.columns]
    if "note" in df.columns:
        ordered.append("note")
    return df[ordered]


def query_import_log() -> pd.DataFrame:
    init_db()
    with _conn() as con:
        return pd.read_sql_query("SELECT * FROM import_log ORDER BY id DESC", con)


def delete_by_batch(batch_name: str) -> int:
    init_db()
    with _conn() as con:
        cur = con.execute(
            "DELETE FROM transactions WHERE batch_name = ? OR (batch_name IS NULL AND source_file = ?)",
            (batch_name, batch_name),
        )
        return cur.rowcount


def delete_by_source(source_file: str) -> int:
    init_db()
    with _conn() as con:
        cur = con.execute("DELETE FROM transactions WHERE source_file = ?", (source_file,))
        return cur.rowcount


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def wipe_db():
    """Delete all rows from transactions and import_log. Keeps the DB file and schema."""
    init_db()
    with _conn() as con:
        con.execute("DELETE FROM transactions")
        con.execute("DELETE FROM import_log")
    # VACUUM must run outside any transaction
    con2 = _conn()
    con2.execute("VACUUM")
    con2.close()


def vacuum_db():
    with _conn() as con:
        con.execute("VACUUM")


def db_size_mb() -> float:
    if DB_PATH.exists():
        return DB_PATH.stat().st_size / 1_048_576
    return 0.0
