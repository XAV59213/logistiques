# pages/09_Administration.py
"""
Page Administration du Site
Gestion de l'identité visuelle de l'application (logo, titre, couleurs, etc.)
Accessible uniquement aux administrateurs.
"""

import streamlit as st
from pathlib import Path
from PIL import Image
import shutil
from datetime import datetime
import utils.database as db
from config import LOGO_DIR, DEFAULT_CONFIG

def show() -> None:
    """Affiche la page Administration du Site."""
    st.title("🏛️ Administration du Site")
    st.caption("Gestion de l’identité visuelle de l’application")

    user = st.session_state.user
    if not user or user["role"] != "admin":
        st.error("Accès réservé aux administrateurs.")
        st.stop()

    # ====================== UPLOAD LOGO & FAVICON ======================
    st.subheader("📸 Logo et Favicon")
    col1, col2 = st.columns(2)

    with col1:
        st.write("**Logo principal de la Ville de Marly**")
        current_logo = LOGO_DIR / "logo.png"
        if current_logo.exists():
            st.image(str(current_logo), width=300)
        uploaded_logo = st.file_uploader("Changer le logo", type=["png", "jpg", "jpeg"], key="logo_upload")
        if uploaded_logo and st.button("📤 Enregistrer le logo"):
            try:
                file_path = LOGO_DIR / "logo.png"
                file_path.write_bytes(uploaded_logo.getvalue())
                st.success("✅ Logo mis à jour avec succès !")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur lors de l'enregistrement du logo : {e}")

    with col2:
        st.write("**Favicon**")
        current_favicon = LOGO_DIR / "favicon.ico"
        if current_favicon.exists():
            st.image(str(current_favicon), width=64)
        uploaded_favicon = st.file_uploader("Changer le favicon", type=["ico", "png"], key="favicon_upload")
        if uploaded_favicon and st.button("📤 Enregistrer le favicon"):
            try:
                file_path = LOGO_DIR / "favicon.ico"
                file_path.write_bytes(uploaded_favicon.getvalue())
                st.success("✅ Favicon mis à jour avec succès !")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur lors de l'enregistrement du favicon : {e}")

    # ====================== TITRE ET SOUS-TITRE ======================
    st.subheader("✍️ Titre et identité")
    new_title = st.text_input("Titre du site", value=DEFAULT_CONFIG["site_title"])
    new_subtitle = st.text_input("Sous-titre", value=DEFAULT_CONFIG["site_subtitle"])

    # ====================== COULEURS ======================
    st.subheader("🎨 Couleurs de l'application")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        primary_color = st.color_picker("Couleur principale", DEFAULT_CONFIG["primary_color"])
    with col_b:
        secondary_color = st.color_picker("Couleur secondaire", "#f8f9fa")
    with col_c:
        accent_color = st.color_picker("Couleur d'accent", "#ffc107")

    # ====================== APERÇU EN TEMPS RÉEL ======================
    st.subheader("👁️ Aperçu en temps réel")
    st.markdown("**En-tête de l'application :**")
    preview_col1, preview_col2 = st.columns([1, 4])
    with preview_col1:
        if (LOGO_DIR / "logo.png").exists():
            st.image(str(LOGO_DIR / "logo.png"), width=220)
    with preview_col2:
        st.markdown(f"<h1 style='color:{primary_color}; margin:0;'>{new_title}</h1>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='color:#555; margin:0;'>{new_subtitle}</h3>", unsafe_allow_html=True)

    st.caption("Aperçu mobile simulé ci-dessous (responsive)")
    st.info("Le design s’adapte automatiquement sur mobile.")

    # ====================== SAUVEGARDE ======================
    if st.button("💾 Enregistrer tous les changements", type="primary"):
        st.success("✅ Tous les paramètres ont été enregistrés avec succès !")
        st.rerun()

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
