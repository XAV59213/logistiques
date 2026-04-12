import sqlite3
from pathlib import Path
from config import Config

def get_connection():
    Path(Config.DATA_DIR).mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(Config.DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Admin'
        )
    """)
    conn.commit()
    conn.close()
