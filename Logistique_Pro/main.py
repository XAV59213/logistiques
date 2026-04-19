# main.py
import importlib
from pathlib import Path
from typing import Optional, Dict, List

import streamlit as st
from streamlit_option_menu import option_menu

import utils.database as db
import utils.style as style
from config import DEFAULT_CONFIG


db.init_database()
VISUAL_SETTINGS = style.get_visual_settings()

st.set_page_config(
    page_title=VISUAL_SETTINGS["site_title"],
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "user" not in st.session_state:
    st.session_state.user = None

if "theme" not in st.session_state:
    st.session_state.theme = DEFAULT_CONFIG["default_theme"]


def load_page(module_name: str) -> None:
    try:
        module = importlib.import_module(module_name)
        if hasattr(module, "show"):
            module.show()
        else:
            st.error(f"La page '{module_name}' ne contient pas de fonction show().")
    except ModuleNotFoundError:
        st.error(f"Module introuvable : {module_name}")
    except Exception as e:
        st.error(f"Erreur lors du chargement de la page '{module_name}' : {e}")


def logout() -> None:
    st.session_state.user = None
    st.session_state.theme = DEFAULT_CONFIG["default_theme"]
    st.rerun()


def get_menu_options(user: Optional[Dict]) -> List[str]:
    if not user:
        return ["Connexion", "Créer un compte"]

    role = user.get("role")
    status = user.get("status", "pending")

    if status == "pending":
        return ["Compte en attente", "Mon Profil", "Se déconnecter"]

    if role == "admin":
        return [
            "Tableau de Bord",
            "Validation Comptes",
            "Validation Demandes",
            "Catalogue Articles",
            "Inventaire",
            "Planning Équipes",
            "Messages",
            "Mon Profil",
            "Administration Site",
            "Administration Système",
            "Exports & Backups",
            "Se déconnecter",
        ]

    if role == "equipe_interne":
        return [
            "Mon Tableau de Bord",
            "Catalogue Articles",
            "Inventaire",
            "Planning Équipes",
            "Messages",
            "Mon Profil",
            "Se déconnecter",
        ]

    if role in ["interne", "association", "externe", "client"]:
        return [
            "Tableau de Bord",
            "Mes Demandes",
            "Catalogue Articles",
            "Messages",
            "Mon Profil",
            "Se déconnecter",
        ]

    return [
        "Tableau de Bord",
        "Catalogue Articles",
        "Mon Profil",
        "Se déconnecter",
    ]


def get_icon_map() -> Dict[str, str]:
    return {
        "Connexion": "box-arrow-in-right",
        "Créer un compte": "person-plus",
        "Compte en attente": "hourglass-split",
        "Tableau de Bord": "house",
        "Mon Tableau de Bord": "house",
        "Validation Comptes": "person-check",
        "Validation Demandes": "clipboard-check",
        "Catalogue Articles": "box-seam",
        "Inventaire": "boxes",
        "Planning Équipes": "calendar-week",
        "Messages": "envelope",
        "Mon Profil": "person-circle",
        "Administration Site": "palette",
        "Administration Système": "gear",
        "Exports & Backups": "download",
        "Mes Demandes": "file-earmark-text",
        "Se déconnecter": "box-arrow-right",
    }


def render_pending_account_page() -> None:
    st.title("⏳ Compte en attente de validation")
    st.info(
        """
Votre compte est actuellement en attente de validation par un administrateur.

Vous recevrez une notification dès que votre compte sera activé.
Merci de votre patience.
        """
    )

    if st.button("Se déconnecter", type="primary"):
        logout()


if st.session_state.user:
    st.session_state.theme = st.session_state.user.get(
        "theme_prefere",
        DEFAULT_CONFIG["default_theme"],
    )

CURRENT_VISUAL = style.get_visual_settings()
style.apply_global_style()

with st.sidebar:
    logo_path = Path("assets/logo/logo.png")

    if logo_path.exists():
        st.image(str(logo_path), width=220)
    else:
        st.markdown(
            f"""
            <h2 style="color:{CURRENT_VISUAL['primary_color']}; text-align:center; margin-bottom:0;">
                🚛 {CURRENT_VISUAL['site_title']}
            </h2>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(f"**{CURRENT_VISUAL['site_title']}**")
    st.caption(CURRENT_VISUAL["site_subtitle"])

    if st.session_state.user:
        username = st.session_state.user.get("username", "Utilisateur")
        role = st.session_state.user.get("role", "N/A")
        status = st.session_state.user.get("status", "pending")

        st.markdown("---")
        st.markdown(f"**Connecté :** {username}")
        st.caption(f"Rôle : {role} | Statut : {status}")

    menu_options = get_menu_options(st.session_state.user)
    icon_map = get_icon_map()
    icons = [icon_map.get(item, "circle") for item in menu_options]

    st.markdown("---")

    selected = option_menu(
        menu_title=None,
        options=menu_options,
        icons=icons,
        menu_icon="truck",
        default_index=0,
        styles={
            "container": {"padding": "6px"},
            "icon": {"font-size": "16px"},
            "nav-link": {
                "font-size": "15px",
                "padding": "10px 12px",
                "margin": "2px 0",
                "border-radius": "8px",
            },
            "nav-link-selected": {
                "background-color": CURRENT_VISUAL["primary_color"],
                "color": "white",
            },
        },
    )

    st.markdown("---")

    theme_options = ["Municipal Bleu", "Mode Clair", "Mode Sombre"]
    current_theme = st.session_state.get("theme", DEFAULT_CONFIG["default_theme"])

    if current_theme not in theme_options:
        current_theme = DEFAULT_CONFIG["default_theme"]

    theme_choice = st.selectbox(
        "🎨 Thème",
        options=theme_options,
        index=theme_options.index(current_theme),
        key="theme_selector",
    )

    if theme_choice != st.session_state.theme:
        st.session_state.theme = theme_choice

        if st.session_state.user:
            try:
                db.execute_query(
                    "UPDATE users SET theme_prefere = ? WHERE id = ?",
                    (theme_choice, st.session_state.user["id"]),
                )
                st.session_state.user["theme_prefere"] = theme_choice
            except Exception:
                pass

        st.rerun()


user = st.session_state.user

if user is None:
    if selected == "Connexion":
        load_page("pages.00_Connexion")
    elif selected == "Créer un compte":
        load_page("pages.01_Creation_Compte")
    else:
        st.warning("Veuillez vous connecter ou créer un compte.")

else:
    user_status = user.get("status", "pending")
    user_role = user.get("role")

    if selected == "Se déconnecter":
        logout()

    elif user_status == "pending":
        if selected == "Mon Profil":
            load_page("pages.12_Mon_Profil")
        else:
            render_pending_account_page()

    else:
        if selected in ["Tableau de Bord", "Mon Tableau de Bord"]:
            load_page("pages.03_Tableau_de_bord")

        elif selected == "Validation Comptes" and user_role == "admin":
            load_page("pages.02_Validation_Comptes")

        elif selected == "Validation Demandes" and user_role == "admin":
            load_page("pages.06_Validation_Demandes")

        elif selected == "Catalogue Articles":
            load_page("pages.04_Catalogue_Articles")

        elif selected == "Inventaire":
            load_page("pages.13_Inventaire")

        elif selected == "Planning Équipes":
            load_page("pages.08_Planning_Equipes")

        elif selected == "Messages":
            load_page("pages.11_Messages")

        elif selected == "Mes Demandes":
            load_page("pages.05_Mes_Demandes")

        elif selected == "Mon Profil":
            load_page("pages.12_Mon_Profil")

        elif selected == "Administration Site" and user_role == "admin":
            load_page("pages.09_Administration")

        elif selected == "Administration Système" and user_role == "admin":
            load_page("pages.10_Administration_Systeme")

        elif selected == "Exports & Backups" and user_role == "admin":
            load_page("pages.19_Exports_Backups")

        else:
            st.info("🚧 Page en cours de développement...")

st.markdown(
    """
    <div class="custom-footer">
        © 2026 Ville de Marly - Développé par xavier59213
    </div>
    """,
    unsafe_allow_html=True,
)
