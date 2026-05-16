from pathlib import Path
import sqlite3
import importlib.util
import streamlit as st

try:
    import bcrypt
except Exception:
    bcrypt = None


APP = Path("/opt/logistique-pro")
DATA_DIR = APP / "data"
PAGES_DIR = APP / "pages"

USERS_DB = DATA_DIR / "logistique_marly.db"
SETTINGS_DB = DATA_DIR / "settings.db"
CATALOGUE_DB = DATA_DIR / "catalogue_articles.db"


def connect_db(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    if bcrypt:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    import hashlib
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_columns(cur, table):
    return [r["name"] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]


def add_column_if_missing(cur, table, column, sql_type):
    if column not in get_columns(cur, table):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}")


def ensure_users_table():
    conn = connect_db(USERS_DB)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'particulier',
            categorie TEXT,
            status TEXT DEFAULT 'pending',
            photo_profil TEXT,
            logo_perso TEXT,
            telephone TEXT,
            theme_prefere TEXT DEFAULT 'Municipal Bleu',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            validated_at TEXT
        )
    """)

    required = {
        "first_name": "TEXT",
        "last_name": "TEXT",
        "categorie": "TEXT",
        "status": "TEXT DEFAULT 'pending'",
        "photo_profil": "TEXT",
        "logo_perso": "TEXT",
        "telephone": "TEXT",
        "theme_prefere": "TEXT DEFAULT 'Municipal Bleu'",
        "validated_at": "TEXT",
        "phone": "TEXT",
        "address": "TEXT",
        "postal_code": "TEXT",
        "city": "TEXT",
        "service": "TEXT",
        "organisation": "TEXT",
        "account_type": "TEXT",
    }

    for col, typ in required.items():
        add_column_if_missing(cur, "users", col, typ)

    conn.commit()
    conn.close()


def get_setting(key, default=""):
    conn = connect_db(SETTINGS_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()

    row = conn.execute(
        "SELECT value FROM settings WHERE key=?",
        (key,),
    ).fetchone()

    conn.close()

    if row:
        return row["value"]

    return default


def set_setting(key, value):
    conn = connect_db(SETTINGS_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, str(value or "")),
    )
    conn.commit()
    conn.close()


def render_external_page(module_name, fallback="Module non disponible."):
    page_path = PAGES_DIR / f"{module_name}.py"

    if not page_path.exists():
        st.warning(fallback)
        return

    try:
        safe_name = "admin_external_" + module_name.replace(" ", "_").replace("-", "_")
        spec = importlib.util.spec_from_file_location(safe_name, page_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if hasattr(module, "show") and callable(module.show):
            module.show()
        else:
            st.warning(f"La page {module_name} ne contient pas de fonction show().")

    except Exception as e:
        st.error(f"Erreur lors du chargement de {module_name} : {e}")
