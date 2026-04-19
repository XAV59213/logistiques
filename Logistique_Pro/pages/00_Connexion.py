# pages/00_Connexion.py
import streamlit as st
import utils.database as db


def show() -> None:
    st.title("🔑 Connexion")
    st.caption("Accédez à Logistique Pro - Ville de Marly")

    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Email").strip().lower()
        password = st.text_input("Mot de passe", type="password")

        submitted = st.form_submit_button(
            "Se connecter",
            type="primary",
            use_container_width=True
        )

        if submitted:
            if not email or not password:
                st.error("Veuillez remplir tous les champs.")
            else:
                user = db.authenticate_user(email, password)

                if user:
                    st.session_state.user = user
                    st.session_state.theme = user.get("theme_prefere", "Municipal Bleu")
                    st.success(f"✅ Connexion réussie. Bienvenue {user['username']}.")
                    st.rerun()
                else:
                    st.error("❌ Email ou mot de passe incorrect.")

    st.markdown("---")
    st.markdown("**Pas encore de compte ?**")
    st.info("Utilisez le menu latéral puis cliquez sur « Créer un compte ».")

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
