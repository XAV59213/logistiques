# pages/00_Connexion.py

from pathlib import Path
import importlib.util

import streamlit as st
import utils.database as db


def open_create_account_page():
    page_path = Path("/opt/logistique-pro/pages/Creation_Compte.py")

    spec = importlib.util.spec_from_file_location("creation_compte", page_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    module.show()


def show() -> None:
    if st.session_state.get("open_create_account"):
        if st.button("⬅️ Retour à la connexion"):
            st.session_state["open_create_account"] = False
            st.rerun()

        open_create_account_page()
        return

    st.title("🔑 Connexion")
    st.caption("Accédez à Logistique Pro - Ville de Marly")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Mot de passe", type="password")
        remember_me = st.checkbox("Rester connecté", value=True)

        col1, col2 = st.columns([3, 1])

        with col1:
            login_submitted = st.form_submit_button("Se connecter", type="primary", width="stretch")

        with col2:
            create_submitted = st.form_submit_button("Créer un compte", width="stretch")

        if create_submitted:
            st.session_state["open_create_account"] = True
            st.rerun()

        if login_submitted:
            if not email or not password:
                st.error("Email et mot de passe obligatoires.")
            else:
                user = db.authenticate_user(email, password)

                if user:
                    if user.get("status") == "pending":
                        st.warning("Votre compte est en attente de validation.")
                    elif user.get("status") == "disabled":
                        st.error("Votre compte est désactivé.")
                    else:
                        st.session_state.user = user

                        if remember_me:
                            try:
                                token = db.create_login_session(user.get("id"), days=30)
                                st.query_params["login_token"] = token
                            except Exception as e:
                                st.warning(f"Connexion persistante non activée : {e}")

                        st.success("Connexion réussie.")
                        st.rerun()
                else:
                    st.error("Identifiants invalides.")

    st.markdown("---")
    st.write("Pas encore de compte ?")

    if st.button("Créer un nouveau compte", width="content"):
        st.session_state["open_create_account"] = True
        st.rerun()

