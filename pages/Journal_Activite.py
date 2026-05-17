# pages/Journal_Activite.py

import sqlite3
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st

BASE_DIR = Path("/opt/logistique-pro")
DB_PATH = BASE_DIR / "data" / "demandes.db"


def connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect()
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


def load_logs():
    conn = connect()

    df = pd.read_sql_query("""
        SELECT *
        FROM activity_logs
        ORDER BY id DESC
        LIMIT 1000
    """, conn)

    conn.close()
    return df


def show():
    init_db()

    st.title("📜 Journal d’activité")
    st.caption("Historique complet des actions utilisateurs")

    user = st.session_state.get("user")

    if not user or str(user.get("role","")).lower() != "admin":
        st.error("Accès réservé administrateur.")
        st.stop()

    df = load_logs()

    if df.empty:
        st.info("Aucune activité enregistrée.")
        return

    c1,c2,c3 = st.columns(3)

    with c1:
        filt_user = st.selectbox(
            "Utilisateur",
            ["Tous"] + sorted(df["utilisateur"].dropna().unique().tolist())
        )

    with c2:
        filt_action = st.selectbox(
            "Action",
            ["Toutes"] + sorted(df["action"].dropna().unique().tolist())
        )

    with c3:
        filt_module = st.selectbox(
            "Module",
            ["Tous"] + sorted(df["module"].dropna().unique().tolist())
        )

    if filt_user != "Tous":
        df = df[df["utilisateur"] == filt_user]

    if filt_action != "Toutes":
        df = df[df["action"] == filt_action]

    if filt_module != "Tous":
        df = df[df["module"] == filt_module]

    st.metric("Lignes affichées", len(df))

    st.dataframe(df, width="stretch", hide_index=True)

    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "⬇️ Export CSV",
        csv,
        "journal_activite.csv",
        "text/csv",
        width="stretch"
    )
