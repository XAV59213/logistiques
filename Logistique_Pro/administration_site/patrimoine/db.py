# -*- coding: utf-8 -*-
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path("/opt/logistique-pro")
DATA_DIR = PROJECT_DIR / "data"
CONFIG_FILE = DATA_DIR / "patrimoine_db_path.txt"

DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_db_path() -> Path:
    if CONFIG_FILE.exists():
        path = Path(CONFIG_FILE.read_text(encoding="utf-8").strip())
        if path.exists():
            return path

    default = DATA_DIR / "patrimoine_bati.db"
    CONFIG_FILE.write_text(str(default), encoding="utf-8")
    return default


def set_db_path(path: str | Path) -> Path:
    path = Path(path)
    CONFIG_FILE.write_text(str(path), encoding="utf-8")
    return path


def connect() -> sqlite3.Connection:
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def get_tables() -> list[str]:
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        return [row["name"] for row in rows]
    finally:
        conn.close()


def table_exists(table_name: str) -> bool:
    return table_name in get_tables()


def count_table(table_name: str) -> int:
    conn = connect()
    try:
        return int(conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0])
    except Exception:
        return 0
    finally:
        conn.close()


def table_columns(table_name: str) -> list[str]:
    conn = connect()
    try:
        rows = conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
        return [row["name"] for row in rows]
    except Exception:
        return []
    finally:
        conn.close()


def read_table(table_name: str) -> pd.DataFrame:
    conn = connect()
    try:
        return pd.read_sql_query(f'SELECT * FROM "{table_name}"', conn)
    finally:
        conn.close()


def find_table(candidates: list[str], prefer_non_empty: bool = True) -> str | None:
    tables = get_tables()
    lower_map = {table.lower(): table for table in tables}

    found: list[str] = []

    for candidate in candidates:
        if candidate.lower() in lower_map:
            found.append(lower_map[candidate.lower()])

    if not found:
        for table in tables:
            table_lower = table.lower()
            for candidate in candidates:
                if candidate.lower() in table_lower:
                    found.append(table)

    if not found:
        return None

    if prefer_non_empty:
        non_empty = [table for table in found if count_table(table) > 0]
        if non_empty:
            return non_empty[0]

    return found[0]


def add_column_if_missing(table_name: str, column_name: str, column_sql: str) -> None:
    if column_name in table_columns(table_name):
        return

    conn = connect()
    try:
        conn.execute(f'ALTER TABLE "{table_name}" ADD COLUMN {column_sql}')
        conn.commit()
    finally:
        conn.close()


def diagnostics() -> list[dict]:
    rows = []

    for table in get_tables():
        rows.append(
            {
                "table": table,
                "lignes": count_table(table),
                "colonnes": ", ".join(table_columns(table)[:30]),
            }
        )

    return rows
