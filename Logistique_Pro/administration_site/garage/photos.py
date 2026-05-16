# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .db import PHOTO_DIR


def save_photo(uploaded_file: Any, name: str) -> str:
    if uploaded_file is None:
        return ""

    PHOTO_DIR.mkdir(parents=True, exist_ok=True)

    safe_name = "".join(c if c.isalnum() else "_" for c in str(name).lower()).strip("_")
    safe_name = safe_name or "vehicule"

    extension = Path(uploaded_file.name).suffix.lower() or ".jpg"
    filename = f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{extension}"
    target = PHOTO_DIR / filename

    with open(target, "wb") as file:
        file.write(uploaded_file.getbuffer())

    return str(target)

# ============================================================
# Compatibilité navigation Streamlit
# Patch 104
# ============================================================

def render(*args, **kwargs):
    """
    Page Photos Garage.
    Le module photos.py sert surtout de helper pour enregistrer les photos.
    Cette page évite l'erreur render/show si elle est appelée depuis le menu.
    """
    import streamlit as st

    st.markdown("### 📸 Photos véhicules")
    st.info(
        "La gestion des photos est intégrée dans les fiches véhicules. "
        "Utilise l'ajout ou la modification d'un véhicule pour changer une photo."
    )

def show(*args, **kwargs):
    """
    Alias de compatibilité.
    """
    return render(*args, **kwargs)

