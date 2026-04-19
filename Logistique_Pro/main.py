# main.py
import streamlit as st
from streamlit_option_menu import option_menu
from pathlib import Path
from typing import Optional, Dict

import utils.database as db
import utils.style as style
from config import DEFAULT_CONFIG

# ====================== CONFIGURATION DE LA PAGE ======================
st.set_page_config(
    page_title=DEFAULT_CONFIG["site_title"],
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================== INITIALISATION ======================
db.init_database()

# Initialisation session_state
if "user" not in st.session_state:
    st.session_state.user = None

if "theme" not in st.session_state:
    st.session_state.theme = DEFAULT_CONFIG["default_theme"]

# Application du style global
style.apply_global_style()

# ====================== FONCTIONS UTILITAIRES ======================
def get_menu_options(user: Optional[Dict]) -> list:
    """Retourne les options du menu selon le rôle et le statut de l'utilisateur."""
    if not user:
        return ["Connexion", "Créer un compte"]

    role = user["role"]
    status = user.get("status", "pending")

    if status == "pending":
        return ["Compte en attente"]

    if role == "admin":
        return [
            "Tableau de Bord", "Validation Demandes", "Catalogue Articles",
            "Inventaire", "Planning Équipes", "Messages", "Administration Site",
            "Administration Système"
        ]
    elif role == "equipe_interne":
        return ["Mon Tableau de Bord", "Messages", "Planning Équipes", "Inventaire", "Catalogue Articles"]
    elif role in ["interne", "association", "externe", "client"]:
        return ["Tableau de Bord", "Mes Demandes", "Catalogue Articles", "Messages"]
    else:
        return ["Tableau de Bord", "Catalogue Articles"]


# ====================== SIDEBAR ======================
with st.sidebar:
    # Logo
    logo_path = "assets/logo/logo.png"
    if Path(logo_path).exists():
        st.image(logo_path, width=220)
    else:
        st.markdown(f"<h2 style='color:{DEFAULT_CONFIG['primary_color']}; text-align:center;'>🚛 Logistique Pro</h2>", unsafe_allow_html=True)

    st.markdown("**Ville de Marly**")
    st.caption("Service Logistique & Événements")

    # Menu principal
    selected = option_menu(
        menu_title=None,
        options=get_menu_options(st.session_state.user),
        icons=["house", "clipboard-check", "box-seam", "boxes", "calendar", "envelope", "gear"],
        menu_icon="truck",
        default_index=0,
        styles={
            "container": {"padding": "10px"},
            "nav-link": {"font-size": "16px", "padding": "12px 10px"},
            "nav-link-selected": {"background-color": DEFAULT_CONFIG["primary_color"]},
        }
    )

    # Sélecteur de thème (disponible pour tous)
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

# ====================== ROUTING CENTRALISÉ ======================
if st.session_state.user is None:
    if selected == "Connexion":
        import pages["00_Connexion"] as page
        page.show()
    elif selected == "Créer un compte":
        import pages["01_Creation_Compte"] as page
        page.show()
    else:
        st.warning("Veuillez vous connecter ou créer un compte.")

elif st.session_state.user.get("status") == "pending":
    # Page d'attente pour les comptes non validés
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
    # Utilisateur connecté et validé
    role = st.session_state.user["role"]

    if selected == "Tableau de Bord" or selected == "Mon Tableau de Bord":
        import pages["03_Tableau_de_bord"] as page
        page.show()
    elif selected == "Validation Demandes" and role == "admin":
        import pages["06_Validation_Demandes"] as page
        page.show()
    elif selected == "Catalogue Articles":
        import pages["04_Catalogue_Articles"] as page
        page.show()
    elif selected == "Inventaire":
        import pages["13_Inventaire"] as page
        page.show()
    elif selected == "Planning Équipes":
        import pages["08_Planning_Equipes"] as page
        page.show()
    elif selected == "Messages":
        import pages["11_Messages"] as page
        page.show()
    elif selected == "Administration Site" and role == "admin":
        import pages["09_Administration"] as page
        page.show()
    elif selected == "Administration Système" and role == "admin":
        import pages["10_Administration_Systeme"] as page
        page.show()
    elif selected == "Mes Demandes":
        import pages["05_Mes_Demandes"] as page
        page.show()
    else:
        st.info("🚧 Page en cours de développement...")

# ====================== FOOTER ======================
st.markdown("""
    <div class="custom-footer">
        © 2026 Ville de Marly - Développé par xavier59213
    </div>
""", unsafe_allow_html=True)
