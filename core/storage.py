"""
SQLite persistence and CSV export for extracted transaction data.
"""
import csv
import io
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

DB_PATH = Path(__file__).parent.parent / "ocr_master.db"


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    """Create tables if they don't exist."""
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS transactions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file      TEXT,
                template_name    TEXT,
                account_number   TEXT,
                statement_period TEXT,
                transaction_date TEXT,
                post_date        TEXT,
                description      TEXT,
                amount           REAL,
                balance          REAL,
                category         TEXT,
                imported_at      TEXT
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


def insert_transactions(
    rows: list[dict],
    source_file: str,
    template_name: str,
    field_map: Optional[dict] = None,
) -> int:
    """
    Insert extracted rows into the transactions table.

    field_map: optional {template_field_name: db_column_name} override.
    Returns number of rows inserted.
    """
    init_db()
    now = datetime.now().isoformat()

    DB_COLS = {
        "transaction_date", "post_date", "description",
        "amount", "balance", "category", "account_number", "statement_period"
    }

    inserted = 0
    with _conn() as con:
        for row in rows:
            mapped = {"source_file": source_file, "template_name": template_name, "imported_at": now}
            for k, v in row.items():
                if k.startswith("_"):
                    continue
                col = (field_map or {}).get(k, k)
                if col in DB_COLS:
                    mapped[col] = v
            cols = ", ".join(mapped.keys())
            placeholders = ", ".join("?" * len(mapped))
            con.execute(f"INSERT INTO transactions ({cols}) VALUES ({placeholders})", list(mapped.values()))
            inserted += 1

    log_import(source_file, template_name, rows_found=inserted)
    return inserted


def log_import(filename: str, template_name: str, pages: int = 0, rows_found: int = 0, status: str = "ok"):
    init_db()
    with _conn() as con:
        con.execute(
            "INSERT INTO import_log (filename, template_name, pages, rows_found, imported_at, status) VALUES (?,?,?,?,?,?)",
            (filename, template_name, pages, rows_found, datetime.now().isoformat(), status),
        )


def query_transactions(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    template_name: Optional[str] = None,
    source_file: Optional[str] = None,
    limit: int = 5000,
) -> pd.DataFrame:
    init_db()
    clauses = []
    params = []
    if date_from:
        clauses.append("transaction_date >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("transaction_date <= ?")
        params.append(date_to)
    if template_name:
        clauses.append("template_name = ?")
        params.append(template_name)
    if source_file:
        clauses.append("source_file = ?")
        params.append(source_file)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT * FROM transactions {where} ORDER BY transaction_date DESC, id DESC LIMIT ?"
    params.append(limit)

    with _conn() as con:
        return pd.read_sql_query(sql, con, params=params)


def query_import_log() -> pd.DataFrame:
    init_db()
    with _conn() as con:
        return pd.read_sql_query("SELECT * FROM import_log ORDER BY id DESC", con)


def delete_by_source(source_file: str) -> int:
    init_db()
    with _conn() as con:
        cur = con.execute("DELETE FROM transactions WHERE source_file = ?", (source_file,))
        return cur.rowcount


def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def vacuum_db():
    with _conn() as con:
        con.execute("VACUUM")


def db_size_mb() -> float:
    if DB_PATH.exists():
        return DB_PATH.stat().st_size / 1_048_576
    return 0.0
