# pages/01_Creation_Compte.py
"""
Page Création de Compte
Gestion de la création de compte avec logique du premier admin.
"""

import streamlit as st
import utils.database as db
from config import DEFAULT_CONFIG

def show() -> None:
    """Affiche la page de création de compte."""
    st.title("📝 Créer un compte")
    st.caption("Inscription à Logistique Pro - Ville de Marly")

    # Formulaire de création de compte
    with st.form("create_account_form"):
        username = st.text_input("Nom d'utilisateur *")
        email = st.text_input("Email *")
        password = st.text_input("Mot de passe *", type="password")
        confirm_password = st.text_input("Confirmer le mot de passe *", type="password")

        submitted = st.form_submit_button("Créer mon compte", type="primary")

        if submitted:
            if not username or not email or not password:
                st.error("Tous les champs obligatoires doivent être remplis.")
            elif password != confirm_password:
                st.error("Les mots de passe ne correspondent pas.")
            elif len(password) < 8:
                st.error("Le mot de passe doit contenir au moins 8 caractères.")
            else:
                # Création du compte via la fonction database
                is_admin = db.create_user(username, email, password, role="externe")

                if is_admin:
                    st.success("✅ Premier compte créé ! Vous êtes maintenant administrateur.")
                    st.session_state.user = {
                        "id": 1,
                        "username": username,
                        "email": email,
                        "role": "admin",
                        "status": "validated"
                    }
                    st.rerun()
                else:
                    st.success("✅ Compte créé avec succès !")
                    st.info("Votre compte est en attente de validation par un administrateur.")
                    st.rerun()

    # Lien vers connexion
    st.markdown("---")
    if st.button("J'ai déjà un compte → Se connecter"):
        st.switch_page("pages/00_Connexion.py")

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
