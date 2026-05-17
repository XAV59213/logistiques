import streamlit as st
from utils.emailer import get_settings, save_settings, send_email


def show():
    st.title("📧 Paramètres email")
    st.caption("Configuration SMTP pour les notifications professionnelles")

    user = st.session_state.get("user")

    if not user or str(user.get("role", "")).lower() != "admin":
        st.error("Accès réservé aux administrateurs.")
        st.stop()

    settings = get_settings()

    with st.form("smtp_settings_form"):
        smtp_enabled = st.checkbox(
            "Activer les emails automatiques",
            value=settings.get("smtp_enabled") == "1",
        )

        c1, c2 = st.columns(2)

        with c1:
            smtp_host = st.text_input("Serveur SMTP", value=settings.get("smtp_host", ""))
            smtp_port = st.text_input("Port SMTP", value=settings.get("smtp_port", "587"))
            smtp_user = st.text_input("Utilisateur SMTP", value=settings.get("smtp_user", ""))
            smtp_from = st.text_input("Adresse expéditeur", value=settings.get("smtp_from", ""))

        with c2:
            smtp_password = st.text_input("Mot de passe SMTP", value=settings.get("smtp_password", ""), type="password")
            smtp_tls = st.checkbox("Utiliser STARTTLS", value=settings.get("smtp_tls", "1") == "1")
            test_email = st.text_input("Email de test", value=user.get("email", ""))

        submitted = st.form_submit_button("💾 Enregistrer", width="stretch")

        if submitted:
            save_settings({
                "smtp_enabled": "1" if smtp_enabled else "0",
                "smtp_host": smtp_host.strip(),
                "smtp_port": smtp_port.strip(),
                "smtp_user": smtp_user.strip(),
                "smtp_password": smtp_password.strip(),
                "smtp_from": smtp_from.strip(),
                "smtp_tls": "1" if smtp_tls else "0",
            })
            st.success("Paramètres email enregistrés.")
            st.rerun()

    st.divider()

    if st.button("📨 Envoyer un email de test", width="stretch"):
        ok, msg = send_email(
            test_email,
            "Test email - Logistique Pro",
            """Bonjour,

Ceci est un email de test envoyé depuis Logistique Pro - Ville de Marly.

Cordialement,
Service Logistique""",
        )

        if ok:
            st.success(msg)
        else:
            st.error(msg)
