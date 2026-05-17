# -*- coding: utf-8 -*-
from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from .db import connect, init_db, load_table
from .vehicules import load_vehicules


PROJECT_DIR = Path("/opt/logistique-pro")
DATA_DIR = PROJECT_DIR / "data"


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] if isinstance(row, sqlite3.Row) else row[1] for row in rows}


def _add_column_if_missing(conn: sqlite3.Connection, table_name: str, column_name: str, column_sql: str) -> None:
    existing = _table_columns(conn, table_name)
    if column_name not in existing:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")


def ensure_attributions_schema() -> None:
    """
    Corrige les anciennes bases où vehicule_attributions existe
    mais n'a pas toutes les colonnes nécessaires.
    """
    init_db()

    conn = connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vehicule_attributions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicule_id INTEGER,
                utilisateur TEXT,
                utilisateur_id INTEGER,
                email TEXT,
                date_debut TEXT,
                date_fin TEXT,
                commentaire TEXT,
                actif INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vehicule_id) REFERENCES vehicules(id)
            )
            """
        )

        required = {
            "vehicule_id": "vehicule_id INTEGER",
            "utilisateur": "utilisateur TEXT",
            "utilisateur_id": "utilisateur_id INTEGER",
            "email": "email TEXT",
            "date_debut": "date_debut TEXT",
            "date_fin": "date_fin TEXT",
            "commentaire": "commentaire TEXT",
            "actif": "actif INTEGER DEFAULT 1",
            "created_at": "created_at TEXT DEFAULT CURRENT_TIMESTAMP",
        }

        for col, sql in required.items():
            _add_column_if_missing(conn, "vehicule_attributions", col, sql)

        conn.execute("UPDATE vehicule_attributions SET actif=1 WHERE actif IS NULL")
        conn.commit()

    finally:
        conn.close()


def _candidate_user_dbs() -> list[Path]:
    candidates = [
        DATA_DIR / "logistique.db",
        DATA_DIR / "users.db",
        DATA_DIR / "utilisateurs.db",
        DATA_DIR / "database.db",
        DATA_DIR / "app.db",
        PROJECT_DIR / "logistique.db",
    ]

    found = []
    for path in candidates:
        if path.exists() and path not in found:
            found.append(path)

    for path in DATA_DIR.glob("*.db"):
        if path not in found:
            found.append(path)

    return found


def _safe_user_label(row: dict) -> str:
    username = str(row.get("username") or row.get("login") or row.get("user") or "").strip()
    prenom = str(row.get("prenom") or row.get("first_name") or "").strip()
    nom = str(row.get("nom") or row.get("name") or row.get("last_name") or "").strip()
    email = str(row.get("email") or row.get("mail") or "").strip()

    display_name = " ".join(x for x in [prenom, nom] if x).strip()

    if username and display_name:
        return f"{display_name} ({username})"
    if display_name:
        return display_name
    if username:
        return username
    if email:
        return email

    return "Utilisateur sans nom"


def load_users_from_databases() -> list[dict]:
    """
    Recherche automatiquement les utilisateurs dans les bases SQLite du projet.
    Compatible avec plusieurs noms de tables/colonnes.
    """
    possible_tables = [
        "users",
        "utilisateurs",
        "user",
        "accounts",
        "comptes",
        "auth_users",
    ]

    users = []
    seen = set()

    for db_path in _candidate_user_dbs():
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row

            tables = [
                r["name"]
                for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            ]

            for table in tables:
                table_lower = table.lower()
                if table_lower not in possible_tables and "user" not in table_lower and "utilisateur" not in table_lower:
                    continue

                cols = _table_columns(conn, table)
                if not cols:
                    continue

                id_col = "id" if "id" in cols else None

                select_cols = []
                for col in [
                    "id",
                    "username",
                    "login",
                    "user",
                    "prenom",
                    "nom",
                    "name",
                    "first_name",
                    "last_name",
                    "email",
                    "mail",
                    "role",
                    "status",
                    "statut",
                ]:
                    if col in cols:
                        select_cols.append(col)

                if not select_cols:
                    continue

                query = f"SELECT {', '.join(select_cols)} FROM {table}"
                rows = conn.execute(query).fetchall()

                for row in rows:
                    data = dict(row)
                    label = _safe_user_label(data)
                    email = str(data.get("email") or data.get("mail") or "").strip()
                    user_id = data.get(id_col) if id_col else None

                    key = (str(user_id), label, email, str(db_path), table)
                    if key in seen:
                        continue
                    seen.add(key)

                    users.append(
                        {
                            "label": label,
                            "user_id": user_id,
                            "email": email,
                            "source_db": str(db_path),
                            "source_table": table,
                            "raw": data,
                        }
                    )

        except Exception:
            continue

        finally:
            try:
                conn.close()
            except Exception:
                pass

    users.sort(key=lambda x: x["label"].lower())
    return users


def add_attribution(data: dict) -> None:
    ensure_attributions_schema()

    conn = connect()
    try:
        if data.get("cloturer_autres", True):
            conn.execute(
                """
                UPDATE vehicule_attributions
                SET actif=0,
                    date_fin=COALESCE(NULLIF(date_fin, ''), ?)
                WHERE vehicule_id=? AND COALESCE(actif, 1)=1
                """,
                (
                    data.get("date_debut"),
                    int(data.get("vehicule_id")),
                ),
            )

        conn.execute(
            """
            INSERT INTO vehicule_attributions (
                vehicule_id,
                utilisateur,
                utilisateur_id,
                email,
                date_debut,
                date_fin,
                commentaire,
                actif
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(data.get("vehicule_id")),
                data.get("utilisateur"),
                data.get("utilisateur_id"),
                data.get("email"),
                data.get("date_debut"),
                data.get("date_fin"),
                data.get("commentaire"),
                1 if data.get("actif", True) else 0,
            ),
        )

        conn.commit()
    finally:
        conn.close()


def close_attribution(attribution_id: int, date_fin: str) -> None:
    ensure_attributions_schema()

    conn = connect()
    try:
        conn.execute(
            """
            UPDATE vehicule_attributions
            SET actif=0,
                date_fin=?
            WHERE id=?
            """,
            (date_fin, int(attribution_id)),
        )
        conn.commit()
    finally:
        conn.close()


def delete_attribution(attribution_id: int) -> None:
    ensure_attributions_schema()

    conn = connect()
    try:
        conn.execute(
            "DELETE FROM vehicule_attributions WHERE id=?",
            (int(attribution_id),),
        )
        conn.commit()
    finally:
        conn.close()


def _load_attributions_with_vehicles() -> pd.DataFrame:
    ensure_attributions_schema()

    df = load_table("vehicule_attributions")

    if df.empty:
        return df

    veh_df = pd.DataFrame(load_vehicules(include_inactive=True))

    if not veh_df.empty:
        veh_df = veh_df[["id", "immatriculation", "marque", "modele", "service"]].rename(
            columns={"id": "vehicule_id"}
        )
        df = df.merge(veh_df, on="vehicule_id", how="left")

    df["vehicule"] = (
        df.get("immatriculation", "").fillna("").astype(str)
        + " — "
        + df.get("marque", "").fillna("").astype(str)
        + " "
        + df.get("modele", "").fillna("").astype(str)
    )

    return df


def render_attributions() -> None:
    ensure_attributions_schema()

    st.markdown("### 👤 Attributions véhicules")

    vehicules = load_vehicules()

    if not vehicules:
        st.info("Ajoute d'abord un véhicule.")
        return

    users = load_users_from_databases()

    vehicule_options = {
        f"{v.get('immatriculation') or 'Sans immat'} — {v.get('marque') or ''} {v.get('modele') or ''}": v["id"]
        for v in vehicules
    }

    with st.expander("➕ Affecter un véhicule", expanded=False):
        with st.form("garage_attribution_add_form"):
            c1, c2 = st.columns(2)

            with c1:
                selected_vehicle = st.selectbox("Véhicule", list(vehicule_options.keys()))

                if users:
                    user_labels = [u["label"] for u in users]
                    selected_user_label = st.selectbox("Utilisateur de la base *", user_labels)
                    selected_user = users[user_labels.index(selected_user_label)]

                    utilisateur = selected_user["label"]
                    utilisateur_id = selected_user.get("user_id")
                    email = selected_user.get("email") or ""

                    st.caption(
                        f"Source : {Path(selected_user['source_db']).name} / {selected_user['source_table']}"
                    )
                else:
                    st.warning("Aucun utilisateur trouvé dans les bases. Saisie manuelle activée.")
                    utilisateur = st.text_input("Utilisateur / agent / service *")
                    utilisateur_id = None
                    email = st.text_input("Email")

                date_debut = st.date_input("Date début", value=date.today())

            with c2:
                date_fin = st.date_input("Date fin prévue", value=None)
                actif = st.checkbox("Attribution active", value=True)
                cloturer_autres = st.checkbox(
                    "Clôturer les autres affectations actives de ce véhicule",
                    value=True,
                )

            commentaire = st.text_area("Commentaire")

            submitted = st.form_submit_button("💾 Enregistrer l'affectation", width="stretch")

        if submitted:
            if not str(utilisateur).strip():
                st.error("L'utilisateur est obligatoire.")
                return

            try:
                add_attribution(
                    {
                        "vehicule_id": vehicule_options[selected_vehicle],
                        "utilisateur": str(utilisateur).strip(),
                        "utilisateur_id": utilisateur_id,
                        "email": email,
                        "date_debut": date_debut.isoformat() if date_debut else "",
                        "date_fin": date_fin.isoformat() if date_fin else "",
                        "commentaire": commentaire,
                        "actif": actif,
                        "cloturer_autres": cloturer_autres,
                    }
                )
                st.success("Affectation enregistrée.")
                st.rerun()
            except Exception as exc:
                st.error("Erreur pendant l'enregistrement de l'affectation.")
                st.exception(exc)

    st.divider()

    df = _load_attributions_with_vehicles()

    if df.empty:
        st.warning("Aucune attribution enregistrée.")
        return

    actifs = int(df["actif"].fillna(0).sum()) if "actif" in df.columns else 0
    historique = len(df)

    c1, c2, c3 = st.columns(3)
    c1.metric("Attributions", historique)
    c2.metric("Actives", actifs)
    c3.metric("Clôturées", max(historique - actifs, 0))

    display_cols = [
        "id",
        "vehicule",
        "utilisateur",
        "email",
        "date_debut",
        "date_fin",
        "actif",
        "commentaire",
        "created_at",
    ]
    display_cols = [c for c in display_cols if c in df.columns]

    st.dataframe(
        df.sort_values("id", ascending=False)[display_cols],
        width="stretch",
        hide_index=True,
    )

    with st.expander("✅ Clôturer une attribution", expanded=False):
        active_df = df[df["actif"].fillna(0).astype(int) == 1] if "actif" in df.columns else df

        if active_df.empty:
            st.info("Aucune attribution active.")
        else:
            options_close = {
                f"#{row['id']} — {row.get('vehicule', '')} — {row.get('utilisateur', '')}": int(row["id"])
                for _, row in active_df.sort_values("id", ascending=False).iterrows()
            }

            selected_close = st.selectbox("Attribution active", list(options_close.keys()))
            close_date = st.date_input("Date de clôture", value=date.today())

            if st.button("Clôturer cette attribution", width="stretch"):
                close_attribution(options_close[selected_close], close_date.isoformat())
                st.success("Attribution clôturée.")
                st.rerun()

    with st.expander("🗑️ Supprimer une attribution", expanded=False):
        ids = df.sort_values("id", ascending=False)["id"].tolist()
        selected_id = st.selectbox("ID attribution à supprimer", ids)
        confirm = st.checkbox("Je confirme la suppression de cette attribution")

        if st.button("Supprimer cette attribution", disabled=not confirm, width="stretch"):
            delete_attribution(int(selected_id))
            st.success("Attribution supprimée.")
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
    return render_attributions()

def show(*args, **kwargs):
    """
    Alias de compatibilité pour les anciens routeurs.
    """
    return render(*args, **kwargs)

