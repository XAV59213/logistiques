import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/opt/logistique-pro")
DEMANDES_DB = BASE_DIR / "data" / "demandes.db"


def connect():
    conn = sqlite3.connect(DEMANDES_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_devis_columns():
    conn = connect()
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(demandes)")
    cols = [r["name"] for r in cur.fetchall()]

    needed = {
        "devis_valide": "INTEGER DEFAULT 0",
        "devis_valide_at": "TEXT",
        "devis_signe_path": "TEXT",
        "devis_signe_uploaded_at": "TEXT",
        "devis_signe_valide": "INTEGER DEFAULT 0",
        "devis_signe_valide_at": "TEXT",
        "devis_commentaire": "TEXT",
        "facture_lue": "INTEGER DEFAULT 0",
        "facture_lue_at": "TEXT",
    }

    for col, typ in needed.items():
        if col not in cols:
            cur.execute(f"ALTER TABLE demandes ADD COLUMN {col} {typ}")

    conn.commit()
    conn.close()


def set_devis_validated(demande_id, commentaire, admin_email):
    ensure_devis_columns()
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        UPDATE demandes
        SET statut = 'Devis à signer',
            devis_valide = 1,
            devis_valide_at = ?,
            devis_commentaire = ?,
            commentaire_admin = ?,
            decide_par = ?,
            date_decision = ?
        WHERE id = ?
    """, (
        now,
        commentaire,
        commentaire,
        admin_email,
        now,
        int(demande_id),
    ))

    conn.commit()
    conn.close()


def set_devis_uploaded(demande_id, path):
    ensure_devis_columns()
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        UPDATE demandes
        SET statut = 'Devis signé reçu',
            devis_signe_path = ?,
            devis_signe_uploaded_at = ?
        WHERE id = ?
    """, (
        path,
        now,
        int(demande_id),
    ))

    conn.commit()
    conn.close()


def set_devis_signed_validated(demande_id, admin_email):
    ensure_devis_columns()
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        UPDATE demandes
        SET statut = 'Validée',
            devis_signe_valide = 1,
            devis_signe_valide_at = ?,
            decide_par = ?,
            date_decision = ?
        WHERE id = ?
    """, (
        now,
        admin_email,
        now,
        int(demande_id),
    ))

    conn.commit()
    conn.close()
