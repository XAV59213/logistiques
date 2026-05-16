
import os
import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(os.environ.get("LOGISTIQUE_PRO_BASE_DIR", "/opt/logistique-pro"))
DB_PATH = BASE_DIR / "data" / "catalogue_articles.db"

CATEGORY_TABLE = "article_categories"
SUBCATEGORY_TABLE = "article_sous_categories"

DEFAULT_CATEGORIES = ["Mobilier", "Structures", "Technique", "Vaisselle", "Divers"]
DEFAULT_SOUS_CATEGORIES = ["Standard", "Événement", "Transport", "Maintenance", "Sécurité", "Interne"]


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def clean_name(value):
    return " ".join(str(value or "").strip().split())


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _table_exists(cur, table):
    row = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def _ensure_table(cur, table):
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            actif INTEGER DEFAULT 1,
            ordre INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        )
    """)

    cur.execute(f"PRAGMA table_info({table})")
    cols = [r["name"] for r in cur.fetchall()]

    needed = {
        "actif": "INTEGER DEFAULT 1",
        "ordre": "INTEGER DEFAULT 0",
        "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
        "updated_at": "TEXT",
    }

    for col, typ in needed.items():
        if col not in cols:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")


def _insert_if_missing(cur, table, name, ordre=0):
    name = clean_name(name)
    if not name:
        return

    exists = cur.execute(
        f"SELECT id FROM {table} WHERE LOWER(nom)=LOWER(?)",
        (name,),
    ).fetchone()

    if exists:
        return

    cur.execute(
        f"INSERT INTO {table} (nom, actif, ordre, created_at) VALUES (?, 1, ?, ?)",
        (name, ordre, _now()),
    )


def _seed_defaults(cur, table, values):
    row = cur.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
    if int(row["c"] or 0) > 0:
        return

    for i, name in enumerate(values, start=1):
        _insert_if_missing(cur, table, name, i * 10)


def _seed_from_articles(cur):
    if not _table_exists(cur, "catalogue_articles"):
        return

    mapping = [
        ("categorie", CATEGORY_TABLE),
        ("sous_categorie", SUBCATEGORY_TABLE),
    ]

    for field, table in mapping:
        try:
            rows = cur.execute(f"""
                SELECT DISTINCT TRIM(COALESCE({field}, '')) AS nom
                FROM catalogue_articles
                WHERE TRIM(COALESCE({field}, '')) <> ''
                ORDER BY nom
            """).fetchall()
        except Exception:
            continue

        for row in rows:
            _insert_if_missing(cur, table, row["nom"], 999)


def ensure_catalogue_settings():
    conn = _connect()
    cur = conn.cursor()

    _ensure_table(cur, CATEGORY_TABLE)
    _ensure_table(cur, SUBCATEGORY_TABLE)

    _seed_defaults(cur, CATEGORY_TABLE, DEFAULT_CATEGORIES)
    _seed_defaults(cur, SUBCATEGORY_TABLE, DEFAULT_SOUS_CATEGORIES)

    _seed_from_articles(cur)

    conn.commit()
    conn.close()


def _load(table, defaults):
    ensure_catalogue_settings()
    conn = _connect()
    cur = conn.cursor()

    rows = cur.execute(f"""
        SELECT nom
        FROM {table}
        WHERE COALESCE(actif, 1)=1
        ORDER BY COALESCE(ordre, 999), nom COLLATE NOCASE
    """).fetchall()

    conn.close()

    names = [r["nom"] for r in rows if clean_name(r["nom"])]
    return names or list(defaults)


def load_categories():
    return _load(CATEGORY_TABLE, DEFAULT_CATEGORIES)


def load_sous_categories():
    return _load(SUBCATEGORY_TABLE, DEFAULT_SOUS_CATEGORIES)


def _usage(field):
    ensure_catalogue_settings()
    conn = _connect()
    cur = conn.cursor()
    result = {}

    if _table_exists(cur, "catalogue_articles"):
        rows = cur.execute(f"""
            SELECT TRIM(COALESCE({field}, '')) AS nom, COUNT(*) AS total
            FROM catalogue_articles
            WHERE TRIM(COALESCE({field}, '')) <> ''
            GROUP BY TRIM(COALESCE({field}, ''))
        """).fetchall()

        result = {r["nom"]: int(r["total"] or 0) for r in rows}

    conn.close()
    return result


def get_category_usage():
    return _usage("categorie")


def get_sous_category_usage():
    return _usage("sous_categorie")


def _add(table, name):
    name = clean_name(name)
    if not name:
        return False, "Le nom est obligatoire."

    ensure_catalogue_settings()
    conn = _connect()
    cur = conn.cursor()

    exists = cur.execute(
        f"SELECT id FROM {table} WHERE LOWER(nom)=LOWER(?)",
        (name,),
    ).fetchone()

    if exists:
        conn.close()
        return False, f"'{name}' existe déjà."

    row = cur.execute(f"SELECT COALESCE(MAX(ordre), 0) + 10 AS ordre FROM {table}").fetchone()
    ordre = int(row["ordre"] or 10)

    cur.execute(
        f"INSERT INTO {table} (nom, actif, ordre, created_at) VALUES (?, 1, ?, ?)",
        (name, ordre, _now()),
    )

    conn.commit()
    conn.close()

    return True, f"'{name}' a été ajouté."


def add_category(name):
    return _add(CATEGORY_TABLE, name)


def add_sous_category(name):
    return _add(SUBCATEGORY_TABLE, name)


def _rename(table, article_field, old_name, new_name, update_articles=True):
    old_name = clean_name(old_name)
    new_name = clean_name(new_name)

    if not old_name or not new_name:
        return False, "Ancien et nouveau nom obligatoires."

    if old_name.lower() == new_name.lower():
        return False, "Aucune modification à effectuer."

    ensure_catalogue_settings()
    conn = _connect()
    cur = conn.cursor()

    duplicate = cur.execute(
        f"SELECT id FROM {table} WHERE LOWER(nom)=LOWER(?) AND LOWER(nom)<>LOWER(?)",
        (new_name, old_name),
    ).fetchone()

    if duplicate:
        conn.close()
        return False, f"'{new_name}' existe déjà."

    cur.execute(
        f"UPDATE {table} SET nom=?, updated_at=? WHERE LOWER(nom)=LOWER(?)",
        (new_name, _now(), old_name),
    )

    if cur.rowcount == 0:
        conn.close()
        return False, f"'{old_name}' est introuvable."

    updated = 0

    if update_articles and _table_exists(cur, "catalogue_articles"):
        cur.execute(
            f"""
            UPDATE catalogue_articles
            SET {article_field}=?
            WHERE LOWER(TRIM(COALESCE({article_field}, '')))=LOWER(?)
            """,
            (new_name, old_name),
        )
        updated = cur.rowcount

    conn.commit()
    conn.close()

    return True, f"Renommé en '{new_name}'. Articles mis à jour : {updated}."


def rename_category(old_name, new_name, update_articles=True):
    return _rename(CATEGORY_TABLE, "categorie", old_name, new_name, update_articles)


def rename_sous_category(old_name, new_name, update_articles=True):
    return _rename(SUBCATEGORY_TABLE, "sous_categorie", old_name, new_name, update_articles)


def _delete(table, article_field, name, replacement=None):
    name = clean_name(name)
    replacement = clean_name(replacement)

    if not name:
        return False, "Le nom est obligatoire."

    if replacement and replacement.lower() == name.lower():
        return False, "La valeur de remplacement doit être différente."

    ensure_catalogue_settings()
    conn = _connect()
    cur = conn.cursor()

    used = 0

    if _table_exists(cur, "catalogue_articles"):
        row = cur.execute(f"""
            SELECT COUNT(*) AS c
            FROM catalogue_articles
            WHERE LOWER(TRIM(COALESCE({article_field}, '')))=LOWER(?)
        """, (name,)).fetchone()

        used = int(row["c"] or 0)

    if used > 0 and not replacement:
        conn.close()
        return False, f"Impossible de supprimer : {used} article(s) utilisent encore '{name}'."

    if used > 0:
        exists = cur.execute(
            f"SELECT id FROM {table} WHERE LOWER(nom)=LOWER(?)",
            (replacement,),
        ).fetchone()

        if not exists:
            conn.close()
            return False, f"La valeur de remplacement '{replacement}' n'existe pas."

        cur.execute(
            f"""
            UPDATE catalogue_articles
            SET {article_field}=?
            WHERE LOWER(TRIM(COALESCE({article_field}, '')))=LOWER(?)
            """,
            (replacement, name),
        )

    cur.execute(
        f"DELETE FROM {table} WHERE LOWER(nom)=LOWER(?)",
        (name,),
    )

    if cur.rowcount == 0:
        conn.close()
        return False, f"'{name}' est introuvable."

    conn.commit()
    conn.close()

    if used > 0:
        return True, f"'{name}' supprimé. {used} article(s) déplacé(s) vers '{replacement}'."

    return True, f"'{name}' supprimé."


def delete_category(name, replacement=None):
    return _delete(CATEGORY_TABLE, "categorie", name, replacement)


def delete_sous_category(name, replacement=None):
    return _delete(SUBCATEGORY_TABLE, "sous_categorie", name, replacement)
