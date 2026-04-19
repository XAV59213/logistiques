# pages/09_Administration.py
"""
Page Administration du Site
Gestion réelle de l'identité visuelle de l'application :
- logo
- favicon
- titre
- sous-titre
- couleurs
Persistés dans la table settings.
"""

from pathlib import Path

import streamlit as st

import utils.database as db
from config import LOGO_DIR, DEFAULT_CONFIG


SETTING_KEYS = {
    "site_title": "site_title",
    "site_subtitle": "site_subtitle",
    "primary_color": "primary_color",
    "secondary_color": "secondary_color",
    "accent_color": "accent_color",
}


def _get_site_setting(key: str, default: str) -> str:
    try:
        return db.get_setting(key, default)
    except Exception:
        return default


def show() -> None:
    st.title("🏛️ Administration du Site")
    st.caption("Gestion de l’identité visuelle de l’application")

    user = st.session_state.get("user")
    if not user or user.get("role") != "admin":
        st.error("Accès réservé aux administrateurs.")
        st.stop()

    current_title = _get_site_setting(SETTING_KEYS["site_title"], DEFAULT_CONFIG["site_title"])
    current_subtitle = _get_site_setting(SETTING_KEYS["site_subtitle"], DEFAULT_CONFIG["site_subtitle"])
    current_primary = _get_site_setting(SETTING_KEYS["primary_color"], DEFAULT_CONFIG["primary_color"])
    current_secondary = _get_site_setting(SETTING_KEYS["secondary_color"], DEFAULT_CONFIG["secondary_color"])
    current_accent = _get_site_setting(SETTING_KEYS["accent_color"], DEFAULT_CONFIG["accent_color"])

    # ====================== LOGO & FAVICON ======================
    st.subheader("📸 Logo et Favicon")
    col1, col2 = st.columns(2)

    with col1:
        st.write("**Logo principal**")
        current_logo = LOGO_DIR / "logo.png"
        if current_logo.exists():
            st.image(str(current_logo), width=260)
        else:
            st.info("Aucun logo enregistré pour le moment.")

        uploaded_logo = st.file_uploader(
            "Changer le logo",
            type=["png", "jpg", "jpeg"],
            key="admin_logo_upload",
        )

        if uploaded_logo and st.button("📤 Enregistrer le logo", key="save_logo"):
            try:
                file_path = LOGO_DIR / "logo.png"
                file_path.write_bytes(uploaded_logo.getvalue())
                st.success("✅ Logo mis à jour avec succès.")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur lors de l'enregistrement du logo : {e}")

    with col2:
        st.write("**Favicon**")
        current_favicon = LOGO_DIR / "favicon.ico"
        if current_favicon.exists():
            st.image(str(current_favicon), width=64)
        else:
            st.info("Aucun favicon enregistré pour le moment.")

        uploaded_favicon = st.file_uploader(
            "Changer le favicon",
            type=["ico", "png"],
            key="admin_favicon_upload",
        )

        if uploaded_favicon and st.button("📤 Enregistrer le favicon", key="save_favicon"):
            try:
                file_path = LOGO_DIR / "favicon.ico"
                file_path.write_bytes(uploaded_favicon.getvalue())
                st.success("✅ Favicon mis à jour avec succès.")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur lors de l'enregistrement du favicon : {e}")

    # ====================== PARAMÈTRES VISUELS ======================
    st.subheader("✍️ Titre et identité")

    new_title = st.text_input("Titre du site", value=current_title).strip()
    new_subtitle = st.text_input("Sous-titre", value=current_subtitle).strip()

    st.subheader("🎨 Couleurs de l'application")
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        primary_color = st.color_picker("Couleur principale", current_primary)
    with col_b:
        secondary_color = st.color_picker("Couleur secondaire", current_secondary)
    with col_c:
        accent_color = st.color_picker("Couleur d'accent", current_accent)

    # ====================== APERÇU ======================
    st.subheader("👁️ Aperçu en temps réel")

    preview_col1, preview_col2 = st.columns([1, 4])

    with preview_col1:
        if (LOGO_DIR / "logo.png").exists():
            st.image(str(LOGO_DIR / "logo.png"), width=220)

    with preview_col2:
        st.markdown(
            f"<h1 style='color:{primary_color}; margin-bottom:0;'>{new_title or DEFAULT_CONFIG['site_title']}</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<h3 style='color:#666; margin-top:0;'>{new_subtitle or DEFAULT_CONFIG['site_subtitle']}</h3>",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div style="
            background:{secondary_color};
            border-left:6px solid {accent_color};
            border-radius:12px;
            padding:16px;
            margin-top:12px;
        ">
            <strong style="color:{primary_color};">Aperçu carte / bloc</strong><br>
            Exemple de rendu de couleur secondaire et accent.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ====================== SAUVEGARDE ======================
    st.subheader("💾 Enregistrement")

    if st.button("💾 Enregistrer tous les changements", type="primary", use_container_width=True):
        try:
            db.set_setting(SETTING_KEYS["site_title"], new_title or DEFAULT_CONFIG["site_title"])
            db.set_setting(SETTING_KEYS["site_subtitle"], new_subtitle or DEFAULT_CONFIG["site_subtitle"])
            db.set_setting(SETTING_KEYS["primary_color"], primary_color)
            db.set_setting(SETTING_KEYS["secondary_color"], secondary_color)
            db.set_setting(SETTING_KEYS["accent_color"], accent_color)

            st.success("✅ Tous les paramètres ont été enregistrés avec succès.")
            st.info("Les nouvelles valeurs sont maintenant persistées en base.")
            st.rerun()
        except Exception as e:
            st.error(f"Erreur lors de l'enregistrement : {e}")

    # ====================== VALEURS ACTUELLES ======================
    with st.expander("Voir les paramètres actuellement enregistrés", expanded=False):
        st.write(f"**Titre :** {current_title}")
        st.write(f"**Sous-titre :** {current_subtitle}")
        st.write(f"**Couleur principale :** {current_primary}")
        st.write(f"**Couleur secondaire :** {current_secondary}")
        st.write(f"**Couleur d'accent :** {current_accent}")

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
