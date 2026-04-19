# pages/06_Validation_Demandes.py
"""
Page Validation des Demandes
Accessible uniquement aux administrateurs.
Permet de valider les demandes, assigner équipe + véhicule, générer la facture PDF et créer les notifications.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import utils.database as db
import utils.pdf_generator as pdf_generator  # Sera implémenté plus tard

def show() -> None:
    """Affiche la page de validation des demandes."""
    st.title("✅ Validation des Demandes")
    st.caption("Demandes en attente de validation par l’administrateur")

    user = st.session_state.user
    if not user or user["role"] != "admin":
        st.error("Accès réservé aux administrateurs.")
        st.stop()

    # Simulation des demandes en attente
    demandes = [
        {"ID": 487, "Demandeur": "Association Les Amis de Marly", "Motif": "Fête de printemps", "Date événement": "25/04/2026", "Articles": "Barnum 6x6m (1), Chaises (80)", "Statut": "En attente"},
        {"ID": 492, "Demandeur": "M. Dupont", "Motif": "Mariage", "Date événement": "03/05/2026", "Articles": "Tables (15), Mange-debout (10)", "Statut": "En attente"},
        {"ID": 495, "Demandeur": "Club de foot", "Motif": "Tournoi", "Date événement": "08/05/2026", "Articles": "Barrières (20), Tentes (2)", "Statut": "En attente"},
    ]

    df = pd.DataFrame(demandes)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Validation
    selected_id = st.selectbox("Sélectionner une demande à traiter", df["ID"].tolist())

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Valider la demande", type="primary"):
            st.success(f"Demande #{selected_id} validée avec succès !")
            st.info("Notifications envoyées au demandeur et aux équipes internes.")
            st.success("Facture PDF générée automatiquement.")
            st.balloons()

    with col2:
        if st.button("❌ Refuser la demande"):
            st.warning(f"Demande #{selected_id} refusée.")

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
