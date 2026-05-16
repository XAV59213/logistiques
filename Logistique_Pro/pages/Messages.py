# pages/Messages.py

import sqlite3
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st


BASE_DIR = Path("/opt/logistique-pro")
DB_PATH = BASE_DIR / "data" / "demandes.db"


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_messages():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            destinataire TEXT,
            expediteur TEXT,
            sujet TEXT,
            message TEXT,
            lu INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def load_messages(email, role):
    conn = connect()

    if role == "admin":
        df = pd.read_sql_query("""
            SELECT *
            FROM messages
            ORDER BY created_at DESC
        """, conn)
    else:
        df = pd.read_sql_query("""
            SELECT *
            FROM messages
            WHERE destinataire = ?
               OR destinataire = 'Tous'
            ORDER BY created_at DESC
        """, conn, params=[email])

    conn.close()
    return df


def mark_read(message_id):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        UPDATE messages
        SET lu = 1
        WHERE id = ?
    """, (int(message_id),))

    conn.commit()
    conn.close()


def delete_message(message_id):
    conn = connect()
    cur = conn.cursor()

    cur.execute("DELETE FROM messages WHERE id = ?", (int(message_id),))

    conn.commit()
    conn.close()


def send_message(destinataire, sujet, message, expediteur):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO messages (
            destinataire, expediteur, sujet, message, lu, created_at
        )
        VALUES (?, ?, ?, ?, 0, ?)
    """, (
        destinataire,
        expediteur,
        sujet,
        message,
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    ))

    conn.commit()
    conn.close()


def show():
    init_messages()

    st.title("✉️ Messages")
    st.caption("Messagerie interne Logistique Pro")

    user = st.session_state.get("user")

    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    email = user.get("email", "")
    username = user.get("username", email)
    role = str(user.get("role", "")).lower()

    df = load_messages(email, role)

    unread_count = 0
    if not df.empty:
        unread_count = int((df["lu"].fillna(0).astype(int) == 0).sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("Messages", len(df))
    c2.metric("Non lus", unread_count)
    c3.metric("Lus", len(df) - unread_count)

    if role == "admin":
        st.divider()
        st.subheader("📨 Envoyer un message")

        with st.form("send_message_form"):
            destinataire = st.text_input(
                "Destinataire",
                value="Tous",
                help="Mettre une adresse email ou Tous"
            )

            sujet = st.text_input("Sujet")
            message = st.text_area("Message")

            submitted = st.form_submit_button("Envoyer le message", width="stretch")

            if submitted:
                if not destinataire.strip() or not sujet.strip() or not message.strip():
                    st.error("Destinataire, sujet et message sont obligatoires.")
                else:
                    send_message(
                        destinataire.strip(),
                        sujet.strip(),
                        message.strip(),
                        username,
                    )
                    st.success("Message envoyé.")
                    st.rerun()

    st.divider()
    st.subheader("📥 Boîte de réception")

    if df.empty:
        st.info("Aucun message.")
        return

    statut = st.selectbox(
        "Filtrer",
        ["Tous", "Non lus", "Lus"],
        key="messages_filter"
    )

    filtered = df.copy()

    if statut == "Non lus":
        filtered = filtered[filtered["lu"].fillna(0).astype(int) == 0]
    elif statut == "Lus":
        filtered = filtered[filtered["lu"].fillna(0).astype(int) == 1]

    if filtered.empty:
        st.info("Aucun message avec ce filtre.")
        return

    for _, msg in filtered.iterrows():
        is_unread = int(msg["lu"] or 0) == 0

        with st.container(border=True):
            titre = "🔴 " if is_unread else "✅ "
            st.markdown(f"### {titre}{msg['sujet']}")
            st.caption(
                f"De : {msg['expediteur'] or '-'} | "
                f"Pour : {msg['destinataire'] or '-'} | "
                f"Date : {msg['created_at'] or '-'}"
            )

            st.write(msg["message"] or "")

            col1, col2 = st.columns(2)

            with col1:
                if is_unread:
                    if st.button("✅ Marquer comme lu", key=f"read_{msg['id']}", width="stretch"):
                        mark_read(msg["id"])
                        st.success("Message marqué comme lu.")
                        st.rerun()

            with col2:
                if role == "admin":
                    if st.button("🗑️ Supprimer", key=f"delete_{msg['id']}", width="stretch"):
                        delete_message(msg["id"])
                        st.warning("Message supprimé.")
                        st.rerun()
