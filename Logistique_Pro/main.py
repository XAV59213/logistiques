import streamlit as st
from pathlib import Path

from config import Config
from utils.database import init_db
from utils.auth import get_current_user, login_page, logout
from utils.system_manager import ensure_directories


def load_css():
    css_file = Path("assets/css/theme.css")
    if css_file.exists():
        with open(css_file, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


st.set_page_config(
    page_title=Config.APP_NAME,
    layout="wide",
    initial_sidebar_state="expanded",
)

load_css()
ensure_directories()
init_db()

user = get_current_user()

if not user:
    login_page()
    st.stop()

with st.sidebar:
    st.markdown(f"## {Config.APP_NAME}")
    st.caption("Ville de Marly")

    st.divider()
    st.write(f"**Utilisateur :** {user['email']}")
    st.write(f"**Rôle :** {user['role']}")

    if st.button("Se déconnecter", width="stretch"):
        logout()

st.title(Config.APP_NAME)
st.caption("Base GitHub structurée et exécutable")

st.success(f"Bienvenue {user['email']} ({user['role']})")
st.info("Utilise la navigation Streamlit pour ouvrir les pages du dossier pages/.")
