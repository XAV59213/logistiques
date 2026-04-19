# pages/01_Creation_Compte.py
import streamlit as st
import utils.database as db


def show() -> None:
    st.title("📝 Créer un compte")
    st.caption("Inscription à Logistique Pro - Ville de Marly")

    with st.form("create_account_form"):
        username = st.text_input("Nom d'utilisateur *")
        email = st.text_input("Email *")
        password = st.text_input("Mot de passe *", type="password")
        confirm_password = st.text_input("Confirmer le mot de passe *", type="password")

        submitted = st.form_submit_button("Créer mon compte", type="primary")

        if submitted:
            if not username or not email or not password or not confirm_password:
                st.error("Tous les champs obligatoires doivent être remplis.")
            elif password != confirm_password:
                st.error("Les mots de passe ne correspondent pas.")
            elif len(password) < 8:
                st.error("Le mot de passe doit contenir au moins 8 caractères.")
            else:
                try:
                    is_admin = db.create_user(username, email, password, role="externe")

                    if is_admin:
                        st.success("✅ Premier compte créé ! Vous êtes maintenant administrateur.")
                        st.session_state.user = db.authenticate_user(email, password)
                        st.rerun()
                    else:
                        st.success("✅ Compte créé avec succès !")
                        st.info("Votre compte est en attente de validation par un administrateur.")
                except ValueError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Erreur lors de la création du compte : {e}")

    st.markdown("---")
    st.caption("Retournez au menu latéral pour vous connecter.")
    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
