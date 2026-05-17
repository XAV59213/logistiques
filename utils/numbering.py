import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/opt/logistique-pro")
DB_PATH = BASE_DIR / "data" / "settings.db"


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_numbering():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS counters (
            name TEXT PRIMARY KEY,
            year INTEGER,
            value INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


def next_number(prefix):
    init_numbering()

    year = datetime.now().year
    name = f"{prefix}_{year}"

    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT value FROM counters WHERE name = ? AND year = ?", (name, year))
    row = cur.fetchone()

    if row:
        value = int(row["value"]) + 1
        cur.execute("UPDATE counters SET value = ? WHERE name = ? AND year = ?", (value, name, year))
    else:
        value = 1
        cur.execute("INSERT INTO counters (name, year, value) VALUES (?, ?, ?)", (name, year, value))

    conn.commit()
    conn.close()

    return f"{prefix}-{year}-{value:06d}"
