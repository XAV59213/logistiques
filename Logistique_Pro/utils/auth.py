import streamlit as st
import bcrypt
from config import Config
from utils.database import get_connection, init_db

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

def ensure_default_admin():
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    if count == 0:
        cur.execute(
            "INSERT INTO users (email, password, role) VALUES (?, ?, ?)",
            (Config.DEFAULT_ADMIN_EMAIL, hash_password(Config.DEFAULT_ADMIN_PASSWORD), "Admin"),
        )
        conn.commit()
    conn.close()

def get_current_user():
    ensure_default_admin()
    return st.session_state.get("user")

def login_page():
    ensure_default_admin()
    st.title("Connexion")
    email = st.text_input("Email")
    password = st.text_input("Mot de passe", type="password")

    if st.button("Se connecter"):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, email, password, role FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        conn.close()

        if row and verify_password(password, row[2]):
            st.session_state["user"] = {"id": row[0], "email": row[1], "role": row[3]}
            st.success("Connexion réussie")
            st.rerun()
        else:
            st.error("Identifiants invalides")
