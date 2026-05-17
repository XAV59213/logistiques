# pages/20_Gestion_Utilisateurs.py

import streamlit as st
import pandas as pd
import utils.database as db


def format_date(value):
    if value is None:
        return "-"
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y %H:%M")
    return str(value)


def show():
    st.title("👥 Gestion des Utilisateurs")
    st.caption("Administration complète des comptes utilisateurs")

    user = st.session_state.get("user")

    if not user or user.get("role") != "admin":
        st.error("Accès réservé aux administrateurs.")
        st.stop()

    conn = db.get_connection()

    users = conn.execute("""
        SELECT id, username, email, role, categorie, status, created_at
        FROM users
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    if not users:
        st.info("Aucun utilisateur trouvé.")
        return

    st.subheader(f"Utilisateurs enregistrés : {len(users)}")

    data = []
    for u in users:
        data.append({
            "ID": u["id"],
            "Nom": u["username"],
            "Email": u["email"],
            "Rôle": u["role"],
            "Catégorie": u["categorie"],
            "Statut": u["status"],
            "Créé le": format_date(u["created_at"])
        })

    df = pd.DataFrame(data)
    st.dataframe(df, width="stretch", hide_index=True)

    st.divider()
    st.subheader("Action sur un utilisateur")

    ids = df["ID"].tolist()
    selected_id = st.selectbox("Sélectionner un utilisateur", ids)

    conn = db.get_connection()
    user_row = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (selected_id,)
    ).fetchone()
    conn.close()

    st.write(f"**Nom :** {user_row['username']}")
    st.write(f"**Email :** {user_row['email']}")
    st.write(f"**Statut :** {user_row['status']}")

    col1, col2, col3 = st.columns(3)

    with col1:
        new_role = st.selectbox(
            "Changer rôle",
            ["admin", "interne", "association", "particulier", "societe", "equipe_interne"]
        )

        if st.button("💾 Modifier rôle", width="stretch"):
            conn = db.get_connection()
            conn.execute(
                "UPDATE users SET role=? WHERE id=?",
                (new_role, selected_id)
            )
            conn.commit()
            conn.close()
            st.success("Rôle modifié.")
            st.rerun()

    with col2:
        if st.button("🔓 Activer", width="stretch"):
            conn = db.get_connection()
            conn.execute(
                "UPDATE users SET status='validated' WHERE id=?",
                (selected_id,)
            )
            conn.commit()
            conn.close()
            st.success("Utilisateur activé.")
            st.rerun()

        if st.button("⛔ Désactiver", width="stretch"):
            conn = db.get_connection()
            conn.execute(
                "UPDATE users SET status='disabled' WHERE id=?",
                (selected_id,)
            )
            conn.commit()
            conn.close()
            st.warning("Utilisateur désactivé.")
            st.rerun()

    with col3:
        if st.button("🗑️ Supprimer utilisateur", width="stretch"):
            conn = db.get_connection()
            conn.execute(
                "DELETE FROM users WHERE id=?",
                (selected_id,)
            )
            conn.commit()
            conn.close()
            st.error("Utilisateur supprimé.")
            st.rerun()

