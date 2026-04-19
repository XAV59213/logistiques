# pages/11_Messages.py
"""
Page Messages / Communication
Permet le dialogue entre administrateurs et équipes internes.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import utils.database as db

def show() -> None:
    """Affiche la page Messages / Communication."""
    st.title("✉️ Messages")
    st.caption("Communication interne entre administrateurs et équipes")

    user = st.session_state.user
    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    role = user["role"]

    # ====================== TABS ======================
    tab_inbox, tab_new, tab_sent = st.tabs(["📥 Boîte de réception", "✍️ Nouveau message", "📤 Messages envoyés"])

    with tab_inbox:
        st.subheader("Messages reçus")
        # Données de démonstration
        messages = [
            {"De": "Admin", "Sujet": "Nouvelle demande validée #487", "Date": "19/04/2026 10:15", "Lu": False},
            {"De": "Équipe Beta", "Sujet": "Problème sur le barnum", "Date": "18/04/2026 16:40", "Lu": True},
        ]
        df = pd.DataFrame(messages)
        st.dataframe(df, use_container_width=True, hide_index=True)

        if st.button("Marquer tout comme lu"):
            st.success("✅ Tous les messages marqués comme lus.")

    with tab_new:
        st.subheader("Envoyer un nouveau message")
        destinataire = st.selectbox("Destinataire", ["Tous les equipe_interne", "Admin", "Équipe Alpha", "Équipe Beta"])
        sujet = st.text_input("Sujet du message")
        message_body = st.text_area("Message", height=200)

        if st.button("📤 Envoyer le message", type="primary"):
            if sujet and message_body:
                st.success("✅ Message envoyé avec succès !")
            else:
                st.warning("Veuillez remplir le sujet et le message.")

    with tab_sent:
        st.subheader("Messages envoyés")
        st.info("Aucun message envoyé pour le moment (simulation).")

    # ====================== NOTIFICATIONS RAPIDES ======================
    if role == "equipe_interne":
        st.success("👷‍♂️ Vous êtes en mode Équipe Interne – priorité aux messages de l’admin.")

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
