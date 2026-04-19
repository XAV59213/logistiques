# pages/00_Connexion.py
import streamlit as st
import utils.database as db


def show() -> None:
    st.title("🔑 Connexion")
    st.caption("Accédez à Logistique Pro - Ville de Marly")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Mot de passe", type="password")

        col1, col2 = st.columns([3, 1])
        with col1:
            submitted = st.form_submit_button("Se connecter", type="primary", use_container_width=True)
        with col2:
            st.form_submit_button("Créer un compte", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Veuillez remplir tous les champs.")
            else:
                user = db.authenticate_user(email, password)

                if user:
                    st.session_state.user = user
                    st.success(f"✅ Connexion réussie ! Bienvenue {user['username']}.")
                    st.rerun()
                else:
                    st.error("❌ Email ou mot de passe incorrect.")

    st.markdown("---")
    st.markdown("Pas encore de compte ?")
    if st.button("Créer un nouveau compte"):
        st.session_state["goto_page"] = "create_account"
        st.info("Retournez au menu latéral puis cliquez sur « Créer un compte ».")

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
