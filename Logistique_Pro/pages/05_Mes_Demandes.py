# pages/05_Mes_Demandes.py
"""
Page Mes Demandes
Affiche uniquement les demandes et factures de l'utilisateur connecté.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import utils.database as db

def show() -> None:
    """Affiche la page Mes Demandes."""
    st.title("📋 Mes Demandes")
    st.caption("Historique de vos demandes et factures")

    user = st.session_state.user
    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    # ====================== FILTRES ======================
    col1, col2 = st.columns(2)
    with col1:
        statut_filter = st.selectbox("Statut", ["Toutes", "En attente", "Validée", "Terminée"])
    with col2:
        date_filter = st.date_input("Période", value=datetime.now() - pd.Timedelta(days=90))

    # ====================== TABLEAU DES DEMANDES ======================
    st.subheader("📌 Mes demandes")

    # Données de démonstration réalistes
    mes_demandes = [
        {"N° Demande": "487", "Date": "15/04/2026", "Motif": "Fête de printemps", "Statut": "Validée", "Montant": "1 245 €", "Facture": "Télécharger"},
        {"N° Demande": "492", "Date": "10/04/2026", "Motif": "Mariage familial", "Statut": "Terminée", "Montant": "890 €", "Facture": "Télécharger"},
        {"N° Demande": "495", "Date": "05/04/2026", "Motif": "Anniversaire", "Statut": "En attente", "Montant": "-", "Facture": "-"},
    ]

    df = pd.DataFrame(mes_demandes)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ====================== FACTURES ======================
    st.subheader("📄 Mes factures")
    if st.button("📥 Télécharger toutes mes factures (ZIP)"):
        st.success("✅ Archive ZIP des factures téléchargée (simulation)")

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
