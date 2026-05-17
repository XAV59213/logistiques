# -*- coding: utf-8 -*-
from __future__ import annotations

import sqlite3
from datetime import date, datetime

import streamlit as st

from .db import connect, init_db, load_table
from .vehicules import load_vehicules


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] if isinstance(row, sqlite3.Row) else row[1] for row in rows}


def _add_column_if_missing(conn: sqlite3.Connection, table_name: str, column_name: str, column_sql: str) -> None:
    existing = _table_columns(conn, table_name)
    if column_name not in existing:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")


def ensure_kilometrage_schema() -> None:
    init_db()

    conn = connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vehicule_kilometrages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicule_id INTEGER,
                date_releve TEXT,
                kilometrage INTEGER,
                commentaire TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicule_id) REFERENCES vehicules(id)
            )
            """
        )

        required = {
            "vehicule_id": "vehicule_id INTEGER",
            "date_releve": "date_releve TEXT",
            "kilometrage": "kilometrage INTEGER DEFAULT 0",
            "commentaire": "commentaire TEXT",
            "created_at": "created_at TEXT DEFAULT CURRENT_TIMESTAMP",
        }

        for col, sql in required.items():
            _add_column_if_missing(conn, "vehicule_kilometrages", col, sql)

        conn.execute("UPDATE vehicule_kilometrages SET kilometrage=0 WHERE kilometrage IS NULL")
        conn.commit()
    finally:
        conn.close()


def update_kilometrage(vehicule_id: int, kilometrage: int, commentaire: str = "") -> None:
    ensure_kilometrage_schema()

    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO vehicule_kilometrages
            (vehicule_id, date_releve, kilometrage, commentaire)
            VALUES (?, ?, ?, ?)
            """,
            (
                int(vehicule_id),
                date.today().isoformat(),
                int(kilometrage),
                commentaire,
            ),
        )

        conn.execute(
            """
            UPDATE vehicules
            SET kilometrage_actuel=?,
                updated_at=?
            WHERE id=?
            """,
            (
                int(kilometrage),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                int(vehicule_id),
            ),
        )

        conn.commit()
    finally:
        conn.close()


def render_kilometrage() -> None:
    ensure_kilometrage_schema()

    st.markdown("### 📈 Kilométrage")

    vehicules = load_vehicules()

    if not vehicules:
        st.info("Ajoute d'abord un véhicule.")
        return

    options = {
        f"{vehicule.get('immatriculation')} — {vehicule.get('marque') or ''} {vehicule.get('modele') or ''}": vehicule["id"]
        for vehicule in vehicules
    }

    with st.form("garage_km_form"):
        selected = st.selectbox("Véhicule", list(options.keys()))
        km = st.number_input("Nouveau kilométrage", min_value=0, step=100)
        commentaire = st.text_input("Commentaire")
        submitted = st.form_submit_button("Mettre à jour")

    if submitted:
        update_kilometrage(options[selected], km, commentaire)
        st.success("Kilométrage mis à jour.")
        st.rerun()

    df = load_table("vehicule_kilometrages")

    if df.empty:
        st.info("Aucun relevé kilométrique.")
    else:
        st.dataframe(df.sort_values("id", ascending=False), width="stretch", hide_index=True)

# ============================================================
# Compatibilité navigation Streamlit
# Patch 104
# Le routeur peut appeler render() ou show()
# ============================================================

def render(*args, **kwargs):
    """
    Point d'entrée standard attendu par le routeur Garage.
    """
    return render_kilometrage()

def show(*args, **kwargs):
    """
    Alias de compatibilité pour les anciens routeurs.
    """
    return render(*args, **kwargs)

