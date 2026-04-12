import streamlit as st
import bcrypt

from utils.helpers import page_header
from utils.auth import get_current_user
from utils.database import get_connection

page_header(
    "Profil utilisateur",
    "Gestion de votre compte",
    "assets/icons/user.png"
)

user = get_current_user()

if not user:
    st.error("Aucun utilisateur connecté.")
    st.stop()

conn = get_connection()
cur = conn.cursor()

cur.execute(
    """
    SELECT id, email, role, first_name, last_name, phone
    FROM users
    WHERE id = ?
    """,
    (user["id"],)
)
row = cur.fetchone()

if not row:
    st.error("Utilisateur introuvable.")
    conn.close()
    st.stop()

st.subheader("Informations du compte")

with st.form("profile_form"):
    email = st.text_input("Email", value=row["email"], disabled=True)
    role = st.text_input("Rôle", value=row["role"], disabled=True)
    first_name = st.text_input("Prénom", value=row["first_name"] or "")
    last_name = st.text_input("Nom", value=row["last_name"] or "")
    phone = st.text_input("Téléphone", value=row["phone"] or "")

    submitted = st.form_submit_button("Enregistrer les modifications")

    if submitted:
        cur.execute(
            """
            UPDATE users
            SET first_name = ?, last_name = ?, phone = ?
            WHERE id = ?
            """,
            (first_name.strip(), last_name.strip(), phone.strip(), row["id"])
        )
        conn.commit()

        # Mise à jour session
        st.session_state["user"]["first_name"] = first_name.strip()
        st.session_state["user"]["last_name"] = last_name.strip()

        st.success("Profil mis à jour.")
        st.rerun()

st.divider()
st.subheader("Changer le mot de passe")

with st.form("password_form"):
    new_password = st.text_input("Nouveau mot de passe", type="password")
    confirm_password = st.text_input("Confirmer le mot de passe", type="password")

    pwd_submitted = st.form_submit_button("Mettre à jour le mot de passe")

    if pwd_submitted:
        if not new_password:
            st.error("Le mot de passe ne peut pas être vide.")
        elif len(new_password) < 8:
            st.error("Le mot de passe doit contenir au moins 8 caractères.")
        elif new_password != confirm_password:
            st.error("Les mots de passe ne correspondent pas.")
        else:
            hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

            cur.execute(
                """
                UPDATE users
                SET password = ?
                WHERE id = ?
                """,
                (hashed, row["id"])
            )
            conn.commit()
            st.success("Mot de passe mis à jour avec succès.")

conn.close()
