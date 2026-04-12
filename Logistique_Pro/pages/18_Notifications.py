import streamlit as st
import pandas as pd

from utils.helpers import page_header, empty_state
from utils.database import get_connection

page_header(
    "Notifications",
    "Centre de notifications internes",
    "assets/icons/settings.png"
)

conn = get_connection()
cur = conn.cursor()

# Sécurité : création de table si absente
cur.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        level TEXT DEFAULT 'info',
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()

st.subheader("Créer une notification")

with st.form("add_notification_form"):
    title = st.text_input("Titre")
    message = st.text_area("Message")
    level = st.selectbox("Niveau", ["info", "success", "warning", "error"])

    submitted = st.form_submit_button("Ajouter la notification")

    if submitted:
        if not title.strip() or not message.strip():
            st.error("Le titre et le message sont obligatoires.")
        else:
            cur.execute(
                """
                INSERT INTO notifications (title, message, level)
                VALUES (?, ?, ?)
                """,
                (title.strip(), message.strip(), level)
            )
            conn.commit()
            st.success("Notification ajoutée.")
            st.rerun()

st.divider()
st.subheader("Liste des notifications")

df = pd.read_sql_query("""
    SELECT id, title, message, level, is_read, created_at
    FROM notifications
    ORDER BY created_at DESC
""", conn)

if df.empty:
    empty_state("Aucune notification disponible.")
else:
    for _, row in df.iterrows():
        with st.container(border=True):
            c1, c2 = st.columns([5, 1])

            with c1:
                st.markdown(f"### {row['title']}")
                st.caption(f"{row['created_at']} • Niveau : {row['level']}")

                if row["level"] == "success":
                    st.success(row["message"])
                elif row["level"] == "warning":
                    st.warning(row["message"])
                elif row["level"] == "error":
                    st.error(row["message"])
                else:
                    st.info(row["message"])

                st.write(f"**Statut :** {'Lue' if int(row['is_read']) == 1 else 'Non lue'}")

            with c2:
                if int(row["is_read"]) == 0:
                    if st.button("Marquer lue", key=f"read_{row['id']}", width="stretch"):
                        cur.execute(
                            "UPDATE notifications SET is_read = 1 WHERE id = ?",
                            (int(row["id"]),)
                        )
                        conn.commit()
                        st.rerun()
                else:
                    if st.button("Remettre non lue", key=f"unread_{row['id']}", width="stretch"):
                        cur.execute(
                            "UPDATE notifications SET is_read = 0 WHERE id = ?",
                            (int(row["id"]),)
                        )
                        conn.commit()
                        st.rerun()

conn.close()
