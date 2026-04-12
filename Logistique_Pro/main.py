import streamlit as st
from config import Config
from utils.database import init_db
from utils.auth import get_current_user, login_page

st.set_page_config(
    page_title=Config.APP_NAME,
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

user = get_current_user()
if not user:
    login_page()
    st.stop()

st.title(Config.APP_NAME)
st.caption("Base GitHub structurée et exécutable")
st.success(f"Bienvenue {user['email']} ({user['role']})")
st.info("Utilise la navigation Streamlit pour ouvrir les pages du dossier pages/.")
