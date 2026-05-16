# pages/Calendrier_Evenements.py

import importlib.util
from pathlib import Path

import streamlit as st


def show():
    page_path = Path("/opt/logistique-pro/system/internal_pages/Evenement_Calendrier.py")

    if not page_path.exists():
        st.error("Page interne Événement Calendrier introuvable.")
        return

    spec = importlib.util.spec_from_file_location("evenement_calendrier_real", page_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if hasattr(module, "show"):
        module.show()
    else:
        st.error("La page interne Événement Calendrier ne contient pas de fonction show().")
