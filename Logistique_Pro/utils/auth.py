# utils/auth.py
import bcrypt
import streamlit as st

from config import Config
from utils.database import get_connection, init_database


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def ensure_default_admin() -> None:
    init_database()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]

    if count == 0:
        cur.execute(
            """
            INSERT INTO users (
                username, email, password_hash, role, categorie, status
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "Administrateur",
                Config.DEFAULT_ADMIN_EMAIL,
                hash_password(Config.DEFAULT_ADMIN_PASSWORD),
                "admin",
                "Administration",
                "validated",
            ),
        )
        conn.commit()

    conn.close()


def get_current_user():
    ensure_default_admin()
    return st.session_state.get("user")


def logout():
    if "user" in st.session_state:
        del st.session_state["user"]
    st.rerun()


def login_page():
    ensure_default_admin()

    st.title("Connexion")
    st.caption("Accès sécurisé à Logistique Pro - Ville de Marly")

    email = st.text_input("Email")
    password = st.text_input("Mot de passe", type="password")

    if st.button("Se connecter", use_container_width=True):
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT id, username, email, password_hash, role, categorie, status,
                   photo_profil, logo_perso, telephone
            FROM users
            WHERE email = ?
            """,
            (email.strip().lower(),),
        )
        row = cur.fetchone()
        conn.close()

        if not row:
            st.error("Utilisateur introuvable.")
            return

        if row["status"] != "validated":
            st.error("Compte non validé.")
            return

        if verify_password(password, row["password_hash"]):
            st.session_state["user"] = {
                "id": row["id"],
                "username": row["username"],
                "email": row["email"],
                "role": row["role"],
                "categorie": row["categorie"],
                "status": row["status"],
                "photo_profil": row["photo_profil"],
                "logo_perso": row["logo_perso"],
                "telephone": row["telephone"],
            }
            st.success("Connexion réussie.")
            st.rerun()
        else:
            st.error("Identifiants invalides.")
