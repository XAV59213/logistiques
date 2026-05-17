# -*- coding: utf-8 -*-
from __future__ import annotations

import sqlite3
from datetime import date

import pandas as pd
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


def ensure_entretiens_schema() -> None:
    """
    Corrige les anciennes bases où vehicule_entretiens existe
    mais n'a pas toutes les colonnes nécessaires.
    """
    init_db()

    conn = connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vehicule_entretiens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicule_id INTEGER,
                type_entretien TEXT,
                date_entretien TEXT,
                date_prochain TEXT,
                km_entretien INTEGER,
                km_prochain INTEGER,
                fournisseur TEXT,
                montant REAL,
                statut TEXT DEFAULT 'Planifié',
                commentaire TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicule_id) REFERENCES vehicules(id)
            )
            """
        )

        required = {
            "vehicule_id": "vehicule_id INTEGER",
            "type_entretien": "type_entretien TEXT",
            "date_entretien": "date_entretien TEXT",
            "date_prochain": "date_prochain TEXT",
            "km_entretien": "km_entretien INTEGER DEFAULT 0",
            "km_prochain": "km_prochain INTEGER DEFAULT 0",
            "fournisseur": "fournisseur TEXT",
            "montant": "montant REAL DEFAULT 0",
            "statut": "statut TEXT DEFAULT 'Planifié'",
            "commentaire": "commentaire TEXT",
            "created_at": "created_at TEXT DEFAULT CURRENT_TIMESTAMP",
        }

        for col, sql in required.items():
            _add_column_if_missing(conn, "vehicule_entretiens", col, sql)

        conn.execute("UPDATE vehicule_entretiens SET statut='Planifié' WHERE statut IS NULL OR statut=''")
        conn.execute("UPDATE vehicule_entretiens SET montant=0 WHERE montant IS NULL")
        conn.execute("UPDATE vehicule_entretiens SET km_entretien=0 WHERE km_entretien IS NULL")
        conn.execute("UPDATE vehicule_entretiens SET km_prochain=0 WHERE km_prochain IS NULL")
        conn.commit()
    finally:
        conn.close()


def add_entretien(data: dict) -> None:
    ensure_entretiens_schema()

    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO vehicule_entretiens (
                vehicule_id,
                type_entretien,
                date_entretien,
                date_prochain,
                km_entretien,
                km_prochain,
                fournisseur,
                montant,
                statut,
                commentaire
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(data.get("vehicule_id")),
                data.get("type_entretien"),
                data.get("date_entretien"),
                data.get("date_prochain"),
                int(data.get("km_entretien") or 0),
                int(data.get("km_prochain") or 0),
                data.get("fournisseur"),
                float(data.get("montant") or 0),
                data.get("statut"),
                data.get("commentaire"),
            ),
        )

        if int(data.get("km_entretien") or 0) > 0:
            conn.execute(
                """
                UPDATE vehicules
                SET kilometrage_actuel=MAX(COALESCE(kilometrage_actuel, 0), ?),
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (
                    int(data.get("km_entretien") or 0),
                    int(data.get("vehicule_id")),
                ),
            )

        conn.commit()
    finally:
        conn.close()


def update_entretien_status(entretien_id: int, statut: str) -> None:
    ensure_entretiens_schema()

    conn = connect()
    try:
        conn.execute(
            "UPDATE vehicule_entretiens SET statut=? WHERE id=?",
            (statut, int(entretien_id)),
        )
        conn.commit()
    finally:
        conn.close()


def delete_entretien(entretien_id: int) -> None:
    ensure_entretiens_schema()

    conn = connect()
    try:
        conn.execute("DELETE FROM vehicule_entretiens WHERE id=?", (int(entretien_id),))
        conn.commit()
    finally:
        conn.close()


def _load_entretiens_with_vehicles() -> pd.DataFrame:
    ensure_entretiens_schema()

    df = load_table("vehicule_entretiens")

    if df.empty:
        return df

    veh_df = pd.DataFrame(load_vehicules(include_inactive=True))

    if not veh_df.empty:
        veh_df = veh_df[["id", "immatriculation", "marque", "modele"]].rename(columns={"id": "vehicule_id"})
        df = df.merge(veh_df, on="vehicule_id", how="left")

    df["vehicule"] = (
        df.get("immatriculation", "").fillna("").astype(str)
        + " — "
        + df.get("marque", "").fillna("").astype(str)
        + " "
        + df.get("modele", "").fillna("").astype(str)
    )

    return df


def render_entretiens() -> None:
    ensure_entretiens_schema()

    st.markdown("### 🛠️ Entretiens véhicules")

    vehicules = load_vehicules()

    if not vehicules:
        st.info("Ajoute d'abord un véhicule.")
        return

    options = {
        f"{v.get('immatriculation') or 'Sans immat'} — {v.get('marque') or ''} {v.get('modele') or ''}": v["id"]
        for v in vehicules
    }

    with st.expander("➕ Ajouter un entretien", expanded=False):
        with st.form("garage_entretien_add_form"):
            c1, c2 = st.columns(2)

            with c1:
                selected = st.selectbox("Véhicule", list(options.keys()))
                type_entretien = st.selectbox(
                    "Type entretien",
                    [
                        "",
                        "Vidange",
                        "Contrôle technique",
                        "Pneus",
                        "Freins",
                        "Distribution",
                        "Révision",
                        "Réparation",
                        "Nettoyage",
                        "Autre",
                    ],
                )
                date_entretien = st.date_input("Date entretien", value=date.today())
                date_prochain = st.date_input("Date prochain entretien", value=None)

            with c2:
                km_entretien = st.number_input("Km entretien", min_value=0, step=100)
                km_prochain = st.number_input("Km prochain entretien", min_value=0, step=100)
                fournisseur = st.text_input("Fournisseur / garage")
                montant = st.number_input("Montant", min_value=0.0, step=10.0, format="%.2f")
                statut = st.selectbox("Statut", ["Planifié", "Réalisé", "À surveiller", "Annulé"])

            commentaire = st.text_area("Commentaire")

            submitted = st.form_submit_button("💾 Enregistrer l'entretien", width="stretch")

        if submitted:
            try:
                add_entretien(
                    {
                        "vehicule_id": options[selected],
                        "type_entretien": type_entretien,
                        "date_entretien": date_entretien.isoformat() if date_entretien else "",
                        "date_prochain": date_prochain.isoformat() if date_prochain else "",
                        "km_entretien": int(km_entretien),
                        "km_prochain": int(km_prochain),
                        "fournisseur": fournisseur,
                        "montant": float(montant),
                        "statut": statut,
                        "commentaire": commentaire,
                    }
                )
                st.success("Entretien ajouté.")
                st.rerun()
            except Exception as exc:
                st.error("Erreur pendant l'ajout de l'entretien.")
                st.exception(exc)

    st.divider()

    df = _load_entretiens_with_vehicles()

    if df.empty:
        st.warning("Aucun entretien enregistré.")
        return

    c1, c2, c3, c4 = st.columns(4)

    total = len(df)
    realises = int((df["statut"] == "Réalisé").sum()) if "statut" in df else 0
    planifies = int((df["statut"] == "Planifié").sum()) if "statut" in df else 0
    montant_total = float(df["montant"].fillna(0).sum()) if "montant" in df else 0

    c1.metric("Entretiens", total)
    c2.metric("Réalisés", realises)
    c3.metric("Planifiés", planifies)
    c4.metric("Montant total", f"{montant_total:.2f} €")

    display_cols = [
        "id",
        "vehicule",
        "type_entretien",
        "date_entretien",
        "date_prochain",
        "km_entretien",
        "km_prochain",
        "fournisseur",
        "montant",
        "statut",
        "commentaire",
    ]
    display_cols = [c for c in display_cols if c in df.columns]

    st.dataframe(
        df.sort_values("id", ascending=False)[display_cols],
        width="stretch",
        hide_index=True,
    )

    with st.expander("✏️ Modifier le statut / supprimer", expanded=False):
        ids = df.sort_values("id", ascending=False)["id"].tolist()
        selected_id = st.selectbox("ID entretien", ids)

        c_status, c_delete = st.columns(2)

        with c_status:
            new_status = st.selectbox("Nouveau statut", ["Planifié", "Réalisé", "À surveiller", "Annulé"])
            if st.button("Mettre à jour le statut", width="stretch"):
                update_entretien_status(int(selected_id), new_status)
                st.success("Statut mis à jour.")
                st.rerun()

        with c_delete:
            confirm = st.checkbox("Je confirme la suppression")
            if st.button("Supprimer l'entretien", disabled=not confirm, width="stretch"):
                delete_entretien(int(selected_id))
                st.success("Entretien supprimé.")
                st.rerun()

# ============================================================
# Compatibilité navigation Streamlit
# Patch 104
# Le routeur peut appeler render() ou show()
# ============================================================

def render(*args, **kwargs):
    """
    Point d'entrée standard attendu par le routeur Garage.
    """
    return render_entretiens()

def show(*args, **kwargs):
    """
    Alias de compatibilité pour les anciens routeurs.
    """
    return render(*args, **kwargs)

