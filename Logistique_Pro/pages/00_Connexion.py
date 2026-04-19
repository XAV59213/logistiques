# pages/00_Connexion.py
"""
Page Connexion
Gestion de la connexion des utilisateurs avec support du mode sombre/clair.
"""

import streamlit as st
import utils.database as db
from config import DEFAULT_CONFIG

def show() -> None:
    """Affiche la page de connexion."""
    st.title("🔑 Connexion")
    st.caption("Accédez à Logistique Pro - Ville de Marly")

    # Formulaire de connexion
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Mot de passe", type="password")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            submitted = st.form_submit_button("Se connecter", type="primary", use_container_width=True)
        with col2:
            if st.form_submit_button("Créer un compte", use_container_width=True):
                st.switch_page("pages/01_Creation_Compte.py")

        if submitted:
            if not email or not password:
                st.error("Veuillez remplir tous les champs.")
            else:
                # Vérification des identifiants (simulation + appel DB)
                conn = db.get_connection()
                user_data = conn.execute(
                    """
                    SELECT id, username, email, role, categorie, status, photo_profil
                    FROM users 
                    WHERE email = ? 
                    """, 
                    (email,)
                ).fetchone()
                conn.close()

                if user_data:
                    # Vérification du mot de passe (simulation pour l'instant)
                    st.session_state.user = {
                        "id": user_data["id"],
                        "username": user_data["username"],
                        "email": user_data["email"],
                        "role": user_data["role"],
                        "categorie": user_data["categorie"],
                        "status": user_data["status"],
                        "photo_profil": user_data["photo_profil"]
                    }
                    st.success(f"✅ Connexion réussie ! Bienvenue {user_data['username']}.")
                    st.rerun()
                else:
                    st.error("❌ Email ou mot de passe incorrect.")

    # Lien vers création de compte
    st.markdown("---")
    st.markdown("Pas encore de compte ?")
    if st.button("Créer un nouveau compte"):
        st.switch_page("pages/01_Creation_Compte.py")

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
