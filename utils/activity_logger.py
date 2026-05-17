import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/opt/logistique-pro")
DB_PATH = BASE_DIR / "data" / "demandes.db"


def init_activity_log():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            utilisateur TEXT,
            role TEXT,
            action TEXT,
            module TEXT,
            details TEXT,
            ip TEXT
        )
    """)

    conn.commit()
    conn.close()


def log_activity(user=None, action="", module="", details="", ip=""):
    try:
        init_activity_log()

        utilisateur = "inconnu"
        role = "inconnu"

        if user:
            utilisateur = user.get("email") or user.get("username") or "inconnu"
            role = user.get("role") or "inconnu"

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO activity_logs (
                created_at, utilisateur, role, action, module, details, ip
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            utilisateur,
            role,
            action,
            module,
            details,
            ip,
        ))

        conn.commit()
        conn.close()

    except Exception:
        pass
