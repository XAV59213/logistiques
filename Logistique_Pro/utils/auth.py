import streamlit as st
import bcrypt
from config import Config
from utils.database import get_connection, init_db


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def ensure_default_admin():
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]

    if count == 0:
        cur.execute(
            """
            INSERT INTO users (
                email, password, role, first_name, last_name, is_active
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                Config.DEFAULT_ADMIN_EMAIL,
                hash_password(Config.DEFAULT_ADMIN_PASSWORD),
                "Admin",
                "Admin",
                "Principal",
                1,
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
            SELECT id, email, password, role, first_name, last_name, is_active
            FROM users
            WHERE email = ?
            """,
            (email,),
        )
        row = cur.fetchone()
        conn.close()

        if not row:
            st.error("Utilisateur introuvable.")
            return

        if row["is_active"] != 1:
            st.error("Compte désactivé.")
            return

        if verify_password(password, row["password"]):
            st.session_state["user"] = {
                "id": row["id"],
                "email": row["email"],
                "role": row["role"],
                "first_name": row["first_name"],
                "last_name": row["last_name"],
            }
            st.success("Connexion réussie")
            st.rerun()
        else:
            st.error("Identifiants invalides.")
