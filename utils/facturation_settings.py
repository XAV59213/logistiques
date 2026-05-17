import sqlite3
from pathlib import Path

BASE_DIR = Path("/opt/logistique-pro")
DB_PATH = BASE_DIR / "data" / "settings.db"

DEFAULTS = {
    "mairie_nom": "Ville de Marly",
    "mairie_service": "Service Logistique & Événements",
    "mairie_adresse": "Place Gabriel Péri",
    "mairie_cp_ville": "59770 Marly",
    "mairie_email": "contact@marly.fr",
    "mairie_telephone": "03 27 23 99 00",
    "mairie_site": "www.marly.fr",
    "tva_rate": "20",
    "transport_default_ht": "50",
    "facture_prefix": "FACT",
    "facture_footer": "© 2026 Ville de Marly - Logistique Pro",
}

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_settings():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    for key, value in DEFAULTS.items():
        cur.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )

    conn.commit()
    conn.close()

def get_settings():
    init_settings()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM settings")
    rows = cur.fetchall()
    conn.close()

    data = DEFAULTS.copy()
    for row in rows:
        data[row["key"]] = row["value"]

    return data

def save_settings(data):
    init_settings()
    conn = get_connection()
    cur = conn.cursor()

    for key, value in data.items():
        cur.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value))
        )

    conn.commit()
    conn.close()

def get_tva_rate():
    s = get_settings()
    return float(s.get("tva_rate", "20") or 20) / 100

def get_transport_default_ht():
    s = get_settings()
    return float(s.get("transport_default_ht", "50") or 50)
