# pages/Equipe_Batiment.py

import importlib.util
from pathlib import Path

import streamlit as st


ALLOWED_ROLES = ["admin", "equipe_batiment", "batiment", "agent_batiment"]


def show():
    user = st.session_state.get("user") or {}
    role = str(user.get("role", "")).lower()

    if role not in ALLOWED_ROLES:
        st.error("Accès réservé à l’administration ou à l’équipe bâtiment.")
        st.stop()

    st.title("🏗️ Équipe Bâtiment")
    st.caption("Gestion du stock bâtiment.")

    st.info(
        "Cette page utilise pour l’instant la page Gestion Stock existante. "
        "Le prochain patch pourra spécialiser la déduction automatique des articles catégorie Bâtiment."
    )

    page_path = Path("/opt/logistique-pro/pages/02_Gestion_Stock.py")

    if not page_path.exists():
        st.error("Page Gestion Stock introuvable.")
        return

    spec = importlib.util.spec_from_file_location("gestion_stock_batiment", page_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if hasattr(module, "show"):
        module.show()
    elif hasattr(module, "main"):
        module.main()
    else:
        st.error("La page Gestion Stock ne contient pas de fonction show() ou main().")
