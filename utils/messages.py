import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/opt/logistique-pro")
DB_PATH = BASE_DIR / "data" / "demandes.db"


def init_messages():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            destinataire TEXT,
            expediteur TEXT,
            sujet TEXT,
            message TEXT,
            lu INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def send_message(destinataire, sujet, message, expediteur="Logistique Pro - Ville de Marly"):
    init_messages()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO messages (
            destinataire, expediteur, sujet, message, lu, created_at
        )
        VALUES (?, ?, ?, ?, 0, ?)
    """, (
        destinataire,
        expediteur,
        sujet,
        message,
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    ))

    conn.commit()
    conn.close()
