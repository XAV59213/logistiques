# utils/inventaire_manager.py

import sqlite3
from pathlib import Path
from datetime import datetime

try:
    from config import DB_PATH
except Exception:
    DB_PATH = "/opt/logistique-pro/database.db"


BASE_DIR = Path("/opt/logistique-pro")
MAIN_DB = Path(DB_PATH)
CATALOGUE_DB = BASE_DIR / "data" / "catalogue_articles.db"
TABLE = "inventaire_items"


def _connect():
    MAIN_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(MAIN_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def clean(value):
    return " ".join(str(value or "").strip().split())


def table_exists(cur, table):
    row = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def get_columns(cur, table):
    try:
        return [r["name"] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]
    except Exception:
        return []


def ensure_inventory_table():
    conn = _connect()
    cur = conn.cursor()

    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            type TEXT DEFAULT 'Article',
            categorie TEXT DEFAULT '',
            sous_categorie TEXT DEFAULT '',
            quantite INTEGER DEFAULT 0,
            stock_min INTEGER DEFAULT 0,
            etat TEXT DEFAULT 'Bon',
            emplacement TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            actif INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        )
    """)

    cols = get_columns(cur, TABLE)

    needed = {
        "nom": "TEXT",
        "type": "TEXT DEFAULT 'Article'",
        "categorie": "TEXT DEFAULT ''",
        "sous_categorie": "TEXT DEFAULT ''",
        "quantite": "INTEGER DEFAULT 0",
        "stock_min": "INTEGER DEFAULT 0",
        "etat": "TEXT DEFAULT 'Bon'",
        "emplacement": "TEXT DEFAULT ''",
        "notes": "TEXT DEFAULT ''",
        "actif": "INTEGER DEFAULT 1",
        "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
        "updated_at": "TEXT",
    }

    for col, sql_type in needed.items():
        if col not in cols:
            cur.execute(f"ALTER TABLE {TABLE} ADD COLUMN {col} {sql_type}")

    conn.commit()
    conn.close()


def _row_to_dict(row):
    return dict(row) if row else {}


def _compute_etat(item):
    qte = int(item.get("quantite") or 0)
    mini = int(item.get("stock_min") or 0)
    etat = clean(item.get("etat"))

    if qte <= 0:
        return "Rupture"

    if mini > 0 and qte <= mini:
        return "Stock bas"

    return etat or "Bon"


def _insert_if_missing(cur, item):
    nom = clean(item.get("nom"))

    if not nom:
        return False

    type_item = clean(item.get("type", "Article")) or "Article"

    exists = cur.execute(
        f"""
        SELECT id
        FROM {TABLE}
        WHERE LOWER(TRIM(nom)) = LOWER(?)
          AND LOWER(TRIM(COALESCE(type, ''))) = LOWER(?)
        """,
        (nom, type_item),
    ).fetchone()

    if exists:
        return False

    cur.execute(
        f"""
        INSERT INTO {TABLE}
        (
            nom, type, categorie, sous_categorie, quantite,
            stock_min, etat, emplacement, notes, actif,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        """,
        (
            nom,
            type_item,
            clean(item.get("categorie")),
            clean(item.get("sous_categorie")),
            int(item.get("quantite") or 0),
            int(item.get("stock_min") or 0),
            clean(item.get("etat", "Bon")) or "Bon",
            clean(item.get("emplacement")),
            clean(item.get("notes")),
            _now(),
            _now(),
        ),
    )

    return True


def import_from_catalogue_if_empty():
    ensure_inventory_table()

    conn = _connect()
    cur = conn.cursor()

    count = cur.execute(f"SELECT COUNT(*) AS c FROM {TABLE}").fetchone()["c"]

    if int(count or 0) > 0:
        conn.close()
        return 0

    if not CATALOGUE_DB.exists():
        conn.close()
        return 0

    cat_conn = sqlite3.connect(CATALOGUE_DB)
    cat_conn.row_factory = sqlite3.Row
    cat_cur = cat_conn.cursor()

    if not table_exists(cat_cur, "catalogue_articles"):
        cat_conn.close()
        conn.close()
        return 0

    cols = get_columns(cat_cur, "catalogue_articles")

    def first_col(candidates):
        for c in candidates:
            if c in cols:
                return c
        return None

    col_nom = first_col(["nom", "designation", "libelle", "article", "name"])
    col_cat = first_col(["categorie", "category"])
    col_sous = first_col(["sous_categorie", "sous_category", "subcategory"])
    col_qte = first_col(["quantite_stock", "stock", "quantite", "quantity"])
    col_min = first_col(["stock_minimum", "stock_min", "min_threshold"])
    col_etat = first_col(["etat", "etat_maintenance", "status"])
    col_desc = first_col(["description", "notes", "commentaire"])

    if not col_nom:
        cat_conn.close()
        conn.close()
        return 0

    select_parts = [
        f"{col_nom} AS nom",
        f"{col_cat} AS categorie" if col_cat else "'' AS categorie",
        f"{col_sous} AS sous_categorie" if col_sous else "'' AS sous_categorie",
        f"{col_qte} AS quantite" if col_qte else "0 AS quantite",
        f"{col_min} AS stock_min" if col_min else "0 AS stock_min",
        f"{col_etat} AS etat" if col_etat else "'Bon' AS etat",
        f"{col_desc} AS notes" if col_desc else "'' AS notes",
    ]

    try:
        rows = cat_cur.execute(
            f"""
            SELECT {", ".join(select_parts)}
            FROM catalogue_articles
            WHERE TRIM(COALESCE({col_nom}, '')) <> ''
            """
        ).fetchall()
    except Exception:
        rows = []

    added = 0

    for r in rows:
        item = {
            "nom": r["nom"],
            "type": "Article catalogue",
            "categorie": r["categorie"],
            "sous_categorie": r["sous_categorie"],
            "quantite": r["quantite"],
            "stock_min": r["stock_min"],
            "etat": r["etat"] or "Bon",
            "emplacement": "",
            "notes": r["notes"],
        }

        if _insert_if_missing(cur, item):
            added += 1

    conn.commit()
    cat_conn.close()
    conn.close()

    return added


def load_inventory(include_inactive=False):
    ensure_inventory_table()
    import_from_catalogue_if_empty()

    conn = _connect()
    cur = conn.cursor()

    where = "" if include_inactive else "WHERE COALESCE(actif, 1)=1"

    rows = cur.execute(
        f"""
        SELECT
            id,
            nom,
            type,
            categorie,
            sous_categorie,
            quantite,
            stock_min,
            etat,
            emplacement,
            notes,
            actif,
            created_at,
            updated_at
        FROM {TABLE}
        {where}
        ORDER BY type COLLATE NOCASE, categorie COLLATE NOCASE, nom COLLATE NOCASE
        """
    ).fetchall()

    conn.close()

    items = []

    for row in rows:
        item = _row_to_dict(row)
        item["quantite"] = int(item.get("quantite") or 0)
        item["stock_min"] = int(item.get("stock_min") or 0)
        item["actif"] = int(item.get("actif") or 0)
        item["etat_calcule"] = _compute_etat(item)
        items.append(item)

    return items


def add_item(nom, type_item, categorie, sous_categorie, quantite, stock_min, etat, emplacement, notes):
    ensure_inventory_table()

    nom = clean(nom)

    if not nom:
        return False, "Le nom est obligatoire."

    conn = _connect()
    cur = conn.cursor()

    cur.execute(
        f"""
        INSERT INTO {TABLE}
        (
            nom, type, categorie, sous_categorie, quantite,
            stock_min, etat, emplacement, notes, actif,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        """,
        (
            nom,
            clean(type_item) or "Article",
            clean(categorie),
            clean(sous_categorie),
            int(quantite or 0),
            int(stock_min or 0),
            clean(etat) or "Bon",
            clean(emplacement),
            clean(notes),
            _now(),
            _now(),
        ),
    )

    conn.commit()
    conn.close()

    return True, f"Élément ajouté : {nom}"


def update_item(item_id, nom, type_item, categorie, sous_categorie, quantite, stock_min, etat, emplacement, notes):
    ensure_inventory_table()

    nom = clean(nom)

    if not nom:
        return False, "Le nom est obligatoire."

    conn = _connect()
    cur = conn.cursor()

    cur.execute(
        f"""
        UPDATE {TABLE}
        SET
            nom=?,
            type=?,
            categorie=?,
            sous_categorie=?,
            quantite=?,
            stock_min=?,
            etat=?,
            emplacement=?,
            notes=?,
            updated_at=?
        WHERE id=?
        """,
        (
            nom,
            clean(type_item) or "Article",
            clean(categorie),
            clean(sous_categorie),
            int(quantite or 0),
            int(stock_min or 0),
            clean(etat) or "Bon",
            clean(emplacement),
            clean(notes),
            _now(),
            int(item_id),
        ),
    )

    if cur.rowcount == 0:
        conn.close()
        return False, "Élément introuvable."

    conn.commit()
    conn.close()

    return True, f"Élément modifié : {nom}"


def delete_item(item_id, hard_delete=False):
    ensure_inventory_table()

    conn = _connect()
    cur = conn.cursor()

    if hard_delete:
        cur.execute(f"DELETE FROM {TABLE} WHERE id=?", (int(item_id),))
    else:
        cur.execute(
            f"UPDATE {TABLE} SET actif=0, updated_at=? WHERE id=?",
            (_now(), int(item_id)),
        )

    if cur.rowcount == 0:
        conn.close()
        return False, "Élément introuvable."

    conn.commit()
    conn.close()

    return True, "Élément supprimé de l’inventaire."
