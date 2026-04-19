# pages/12_Mon_Profil.py
"""
Page Mon Profil
Permet à tous les utilisateurs validés de gérer :
- Photo de profil
- Logo personnel
- Thème personnel
- Informations de contact
"""

from pathlib import Path

import streamlit as st
import utils.database as db
from config import PROFILES_DIR, LOGOS_USERS_DIR


def show() -> None:
    st.title("👤 Mon Profil")
    user = st.session_state.user

    if not user:
        st.error("Vous devez être connecté pour accéder à cette page.")
        st.stop()

    st.subheader("📸 Photo de profil")
    col1, col2 = st.columns([1, 3])

    with col1:
        if user.get("photo_profil"):
            try:
                image_path = Path(user["photo_profil"])
                if image_path.exists():
                    st.image(str(image_path), width=150)
                else:
                    st.image("https://via.placeholder.com/150", width=150)
            except Exception:
                st.image("https://via.placeholder.com/150", width=150)
        else:
            st.image("https://via.placeholder.com/150", width=150)

    with col2:
        uploaded_photo = st.file_uploader(
            "Changer de photo de profil",
            type=["png", "jpg", "jpeg"],
            key="photo_upload"
        )
        if uploaded_photo and st.button("📤 Enregistrer la photo"):
            try:
                file_path = PROFILES_DIR / f"{user['id']}_{uploaded_photo.name}"
                file_path.write_bytes(uploaded_photo.getvalue())

                conn = db.get_connection()
                conn.execute(
                    "UPDATE users SET photo_profil = ? WHERE id = ?",
                    (str(file_path), user["id"])
                )
                conn.commit()
                conn.close()

                st.session_state.user["photo_profil"] = str(file_path)

                st.success("✅ Photo de profil mise à jour avec succès.")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur lors de la sauvegarde : {e}")

    st.subheader("🏷️ Logo personnel")
    if user["role"] in ["association", "externe", "client"]:
        col3, col4 = st.columns([1, 3])

        with col3:
            if user.get("logo_perso"):
                try:
                    logo_path = Path(user["logo_perso"])
                    if logo_path.exists():
                        st.image(str(logo_path), width=180)
                except Exception:
                    pass

        with col4:
            uploaded_logo = st.file_uploader(
                "Changer de logo personnel",
                type=["png", "jpg", "jpeg"],
                key="logo_upload"
            )
            if uploaded_logo and st.button("📤 Enregistrer le logo"):
                try:
                    file_path = LOGOS_USERS_DIR / f"{user['id']}_{uploaded_logo.name}"
                    file_path.write_bytes(uploaded_logo.getvalue())

                    conn = db.get_connection()
                    conn.execute(
                        "UPDATE users SET logo_perso = ? WHERE id = ?",
                        (str(file_path), user["id"])
                    )
                    conn.commit()
                    conn.close()

                    st.session_state.user["logo_perso"] = str(file_path)

                    st.success("✅ Logo personnel mis à jour.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")
    else:
        st.info("Le logo personnel est disponible uniquement pour les rôles Association, Externe et Client.")

    st.subheader("🎨 Thème de l'application")
    current_theme = st.session_state.get("theme", "Municipal Bleu")

    new_theme = st.selectbox(
        "Choisissez votre thème préféré",
        options=["Municipal Bleu", "Mode Clair", "Mode Sombre"],
        index=["Municipal Bleu", "Mode Clair", "Mode Sombre"].index(current_theme)
    )

    if new_theme != current_theme and st.button("💾 Enregistrer le thème"):
        st.session_state.theme = new_theme

        try:
            conn = db.get_connection()
            conn.execute(
                "UPDATE users SET theme_prefere = ? WHERE id = ?",
                (new_theme, user["id"])
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

        st.success("✅ Thème mis à jour.")
        st.rerun()

    st.subheader("📋 Informations personnelles")
    with st.form("form_profil"):
        new_display_name = st.text_input("Nom d'affichage", value=user.get("username", ""))
        new_phone = st.text_input("Téléphone", value=user.get("telephone", ""))

        submitted = st.form_submit_button("💾 Enregistrer les modifications")
        if submitted:
            if not new_display_name.strip():
                st.error("Le nom d'affichage est obligatoire.")
            else:
                try:
                    conn = db.get_connection()
                    conn.execute(
                        "UPDATE users SET username = ?, telephone = ? WHERE id = ?",
                        (new_display_name.strip(), new_phone.strip(), user["id"])
                    )
                    conn.commit()
                    conn.close()

                    st.session_state.user["username"] = new_display_name.strip()
                    st.session_state.user["telephone"] = new_phone.strip()

                    st.success("✅ Informations mises à jour avec succès.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur lors de la mise à jour : {e}")

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
