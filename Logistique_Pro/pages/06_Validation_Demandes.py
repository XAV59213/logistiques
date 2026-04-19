# pages/06_Validation_Demandes.py
"""
Page Validation des Demandes
Accessible uniquement aux administrateurs.
"""

import streamlit as st
import pandas as pd


def show() -> None:
    st.title("✅ Validation des Demandes")
    st.caption("Demandes en attente de validation par l’administrateur")

    user = st.session_state.user
    if not user or user["role"] != "admin":
        st.error("Accès réservé aux administrateurs.")
        st.stop()

    demandes = [
        {
            "ID": 487,
            "Demandeur": "Association Les Amis de Marly",
            "Motif": "Fête de printemps",
            "Date événement": "25/04/2026",
            "Articles": "Barnum 6x6m (1), Chaises (80)",
            "Statut": "En attente"
        },
        {
            "ID": 492,
            "Demandeur": "M. Dupont",
            "Motif": "Mariage",
            "Date événement": "03/05/2026",
            "Articles": "Tables (15), Mange-debout (10)",
            "Statut": "En attente"
        },
        {
            "ID": 495,
            "Demandeur": "Club de foot",
            "Motif": "Tournoi",
            "Date événement": "08/05/2026",
            "Articles": "Barrières (20), Tentes (2)",
            "Statut": "En attente"
        },
    ]

    df = pd.DataFrame(demandes)
    st.dataframe(df, use_container_width=True, hide_index=True)

    selected_id = st.selectbox("Sélectionner une demande à traiter", df["ID"].tolist())

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Valider la demande", type="primary", use_container_width=True):
            st.success(f"Demande #{selected_id} validée avec succès.")
            st.info("Notifications à connecter à la base plus tard.")
            st.info("Génération PDF à brancher ultérieurement.")

    with col2:
        if st.button("❌ Refuser la demande", use_container_width=True):
            st.warning(f"Demande #{selected_id} refusée.")

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
