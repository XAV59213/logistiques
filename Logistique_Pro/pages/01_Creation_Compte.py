# pages/01_Creation_Compte.py
import streamlit as st
import utils.database as db
from utils.security import is_strong_password
from utils.validators import validate_email


def show() -> None:
    st.title("📝 Créer un compte")
    st.caption("Inscription à Logistique Pro - Ville de Marly")

    with st.form("create_account_form", clear_on_submit=False):
        username = st.text_input("Nom d'utilisateur *").strip()
        email = st.text_input("Email *").strip().lower()
        password = st.text_input("Mot de passe *", type="password")
        confirm_password = st.text_input("Confirmer le mot de passe *", type="password")

        submitted = st.form_submit_button(
            "Créer mon compte",
            type="primary",
            use_container_width=True
        )

        if submitted:
            if not username or not email or not password or not confirm_password:
                st.error("Tous les champs obligatoires doivent être remplis.")

            elif not validate_email(email):
                st.error("Adresse email invalide.")

            elif password != confirm_password:
                st.error("Les mots de passe ne correspondent pas.")

            else:
                strong, message = is_strong_password(password)
                if not strong:
                    st.error(f"Mot de passe insuffisant : {message}")
                else:
                    try:
                        is_admin = db.create_user(
                            username=username,
                            email=email,
                            password=password,
                            role="externe"
                        )

                        if is_admin:
                            user = db.authenticate_user(email, password)
                            st.session_state.user = user
                            st.session_state.theme = user.get("theme_prefere", "Municipal Bleu")
                            st.success("✅ Premier compte créé. Vous êtes maintenant administrateur.")
                            st.rerun()
                        else:
                            st.success("✅ Compte créé avec succès.")
                            st.info("Votre compte est en attente de validation par un administrateur.")

                    except ValueError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Erreur lors de la création du compte : {e}")

    st.markdown("---")
    st.info("Après validation de votre compte, vous pourrez vous connecter depuis le menu latéral.")

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
