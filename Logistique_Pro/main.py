# main.py
import importlib
from pathlib import Path
from typing import Optional, Dict

import streamlit as st
from streamlit_option_menu import option_menu

import utils.database as db
import utils.style as style
from config import DEFAULT_CONFIG

st.set_page_config(
    page_title=DEFAULT_CONFIG["site_title"],
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

db.init_database()

if "user" not in st.session_state:
    st.session_state.user = None

if "theme" not in st.session_state:
    st.session_state.theme = DEFAULT_CONFIG["default_theme"]


def load_page(module_name: str):
    module = importlib.import_module(module_name)
    if hasattr(module, "show"):
        module.show()
    else:
        st.error(f"La page {module_name} ne contient pas de fonction show().")


style.apply_global_style()


def get_menu_options(user: Optional[Dict]) -> list:
    if not user:
        return ["Connexion", "Créer un compte"]

    role = user["role"]
    status = user.get("status", "pending")

    if status == "pending":
        return ["Compte en attente"]

    if role == "admin":
        return [
            "Tableau de Bord",
            "Validation Demandes",
            "Catalogue Articles",
            "Inventaire",
            "Planning Équipes",
            "Messages",
            "Administration Site",
            "Administration Système",
        ]
    elif role == "equipe_interne":
        return ["Mon Tableau de Bord", "Messages", "Planning Équipes", "Inventaire", "Catalogue Articles"]
    elif role in ["interne", "association", "externe", "client"]:
        return ["Tableau de Bord", "Mes Demandes", "Catalogue Articles", "Messages"]
    else:
        return ["Tableau de Bord", "Catalogue Articles"]


with st.sidebar:
    logo_path = "assets/logo/logo.png"
    if Path(logo_path).exists():
        st.image(logo_path, width=220)
    else:
        st.markdown(
            f"<h2 style='color:{DEFAULT_CONFIG['primary_color']}; text-align:center;'>🚛 Logistique Pro</h2>",
            unsafe_allow_html=True
        )

    st.markdown("**Ville de Marly**")
    st.caption("Service Logistique & Événements")

    menu_options = get_menu_options(st.session_state.user)

    icon_map = {
        "Connexion": "box-arrow-in-right",
        "Créer un compte": "person-plus",
        "Compte en attente": "hourglass-split",
        "Tableau de Bord": "house",
        "Mon Tableau de Bord": "house",
        "Validation Demandes": "clipboard-check",
        "Catalogue Articles": "box-seam",
        "Inventaire": "boxes",
        "Planning Équipes": "calendar",
        "Messages": "envelope",
        "Administration Site": "palette",
        "Administration Système": "gear",
        "Mes Demandes": "file-earmark-text",
    }

    icons = [icon_map.get(item, "circle") for item in menu_options]

    selected = option_menu(
        menu_title=None,
        options=menu_options,
        icons=icons,
        menu_icon="truck",
        default_index=0,
        styles={
            "container": {"padding": "10px"},
            "nav-link": {"font-size": "16px", "padding": "12px 10px"},
            "nav-link-selected": {"background-color": DEFAULT_CONFIG["primary_color"]},
        }
    )

    st.markdown("---")
    theme_choice = st.selectbox(
        "🎨 Thème",
        options=["Municipal Bleu", "Mode Clair", "Mode Sombre"],
        index=["Municipal Bleu", "Mode Clair", "Mode Sombre"].index(st.session_state.theme),
        key="theme_selector"
    )
    if theme_choice != st.session_state.theme:
        st.session_state.theme = theme_choice
        st.rerun()


if st.session_state.user is None:
    if selected == "Connexion":
        load_page("pages.00_Connexion")
    elif selected == "Créer un compte":
        load_page("pages.01_Creation_Compte")
    else:
        st.warning("Veuillez vous connecter ou créer un compte.")

elif st.session_state.user.get("status") == "pending":
    st.title("⏳ Compte en attente de validation")
    st.info("""
Votre compte est actuellement en attente de validation par un administrateur.

Vous recevrez une notification dès que votre compte sera activé.
Merci de votre patience.
    """)
    if st.button("Se déconnecter"):
        st.session_state.user = None
        st.rerun()

else:
    role = st.session_state.user["role"]

    if selected in ["Tableau de Bord", "Mon Tableau de Bord"]:
        load_page("pages.03_Tableau_de_bord")
    elif selected == "Validation Demandes" and role == "admin":
        load_page("pages.06_Validation_Demandes")
    elif selected == "Catalogue Articles":
        load_page("pages.04_Catalogue_Articles")
    elif selected == "Inventaire":
        load_page("pages.13_Inventaire")
    elif selected == "Planning Équipes":
        st.info("🚧 La page Planning Équipes doit être refaite car le fichier actuel est binaire/inexploitable.")
    elif selected == "Messages":
        load_page("pages.11_Messages")
    elif selected == "Administration Site" and role == "admin":
        load_page("pages.09_Administration")
    elif selected == "Administration Système" and role == "admin":
        st.info("🚧 La page Administration Système doit être refaite car le fichier actuel est binaire/inexploitable.")
    elif selected == "Mes Demandes":
        load_page("pages.05_Mes_Demandes")
    else:
        st.info("🚧 Page en cours de développement...")

st.markdown("""
<div class="custom-footer">
    © 2026 Ville de Marly - Développé par xavier59213
</div>
""", unsafe_allow_html=True)
