import streamlit as st
from config import Config
from utils.database import init_db
from utils.auth import get_current_user, login_page, logout
from utils.system_manager import ensure_directories

st.set_page_config(
    page_title=Config.APP_NAME,
    layout="wide",
    initial_sidebar_state="expanded",
)

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
