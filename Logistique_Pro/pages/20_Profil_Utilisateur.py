# pages/20_Profil_Utilisateur.py
import bcrypt
import streamlit as st

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
    SELECT id, username, email, role, categorie, telephone
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
    username = st.text_input("Nom d'utilisateur", value=row["username"] or "")
    email = st.text_input("Email", value=row["email"], disabled=True)
    role = st.text_input("Rôle", value=row["role"], disabled=True)
    categorie = st.text_input("Catégorie", value=row["categorie"] or "", disabled=True)
    phone = st.text_input("Téléphone", value=row["telephone"] or "")

    submitted = st.form_submit_button("Enregistrer les modifications")

    if submitted:
        if not username.strip():
            st.error("Le nom d'utilisateur est obligatoire.")
        else:
            try:
                cur.execute(
                    """
                    UPDATE users
                    SET username = ?, telephone = ?
                    WHERE id = ?
                    """,
                    (username.strip(), phone.strip(), row["id"])
                )
                conn.commit()

                st.session_state["user"]["username"] = username.strip()
                st.session_state["user"]["telephone"] = phone.strip()

                st.success("Profil mis à jour.")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur lors de la mise à jour du profil : {e}")

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
            hashed = bcrypt.hashpw(
                new_password.encode("utf-8"),
                bcrypt.gensalt()
            ).decode("utf-8")

            cur.execute(
                """
                UPDATE users
                SET password_hash = ?
                WHERE id = ?
                """,
                (hashed, row["id"])
            )
            conn.commit()
            st.success("Mot de passe mis à jour avec succès.")

conn.close()
