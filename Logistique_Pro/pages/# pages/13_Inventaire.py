# pages/06_Validation_Demandes.py
"""
Page Validation des Demandes
Accessible uniquement aux administrateurs.
Permet de valider les demandes, assigner une équipe + véhicule, générer la facture et créer les notifications.
"""

import streamlit as st
import pandas as pd
import utils.database as db
import utils.pdf_generator as pdf  # Sera créé plus tard
from datetime import datetime

def show() -> None:
    """Affiche la page de validation des demandes."""
    st.title("✅ Validation des Demandes")
    st.caption("Demandes en attente de validation par l’administrateur")

    user = st.session_state.user
    if not user or user["role"] != "admin":
        st.error("Accès réservé aux administrateurs.")
        st.stop()

    # Simulation des demandes en attente (à remplacer par vraie requête DB)
    demandes_en_attente = [
        {"ID": 487, "Demandeur": "Association Les Amis de Marly", "Motif": "Fête de printemps", "Date événement": "25/04/2026", "Articles demandés": "Barnum 6x6m (1), Chaises (80)", "Statut": "En attente"},
        {"ID": 492, "Demandeur": "M. Dupont", "Motif": "Mariage", "Date événement": "03/05/2026", "Articles demandés": "Tables (15), Mange-debout (10)", "Statut": "En attente"},
    ]

    df = pd.DataFrame(demandes_en_attente)
    st.dataframe(df, use_container_width=True)

    # Validation d'une demande
    selected_id = st.selectbox("Sélectionner une demande à valider", df["ID"].tolist())

    if st.button("✅ Valider cette demande", type="primary"):
        with st.spinner("Validation en cours..."):
            # Simulation de validation
            st.success(f"Demande #{selected_id} validée avec succès !")
            
            # Création des notifications
            st.info("Notifications envoyées :")
            st.success("• Demandeur notifié")
            st.success("• Équipe interne notifiée (préparation matériel)")
            
            # Génération facture
            if st.button("📄 Générer la facture PDF"):
                st.success("Facture PDF générée et disponible au téléchargement.")

            # Assignation véhicule et équipe
            st.info("Véhicule et équipe assignés automatiquement.")

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
