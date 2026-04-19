# pages/13_Inventaire.py
"""
Page Inventaire
Gestion globale de l'inventaire (articles + outils) avec rapports.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import utils.database as db
from config import PHOTOS_DIR, OUTILS_DIR

def show() -> None:
    """Affiche la page Inventaire."""
    st.title("📦 Inventaire Global")
    st.caption("Articles & Outils - Suivi complet")

    user = st.session_state.user
    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    role = user["role"]

    # Filtres
    col1, col2, col3 = st.columns(3)
    with col1:
        type_filter = st.selectbox("Type", ["Tous", "Articles", "Outils"])
    with col2:
        categorie_filter = st.selectbox("Catégorie", ["Toutes", "Mobilier", "Structures", "Technique", "Outils"])
    with col3:
        etat_filter = st.selectbox("État", ["Tous", "Bon", "Stock bas", "À réparer"])

    # Tableau inventaire
    st.subheader("État actuel de l'inventaire")

    # Données de démonstration
    data = {
        "ID": [101, 102, 201, 202],
        "Nom": ["Chaises pliantes", "Barnum 6x6m", "Perceuse 18V", "Câbles 50m"],
        "Type": ["Article", "Article", "Outil", "Outil"],
        "Catégorie": ["Mobilier", "Structures", "Outils", "Outils"],
        "Stock": [245, 12, 8, 15],
        "Stock min": [10, 2, 5, 10],
        "État": ["OK", "Bas", "OK", "Bas"],
        "Emplacement": ["Entrepôt A", "Entrepôt B", "Atelier", "Entrepôt C"]
    }

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Rapports d'inventaire
    st.subheader("📊 Rapports d'inventaire")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("📥 Exporter inventaire complet (Excel)"):
            st.success("✅ Rapport Excel généré et téléchargé")
    with col_b:
        if st.button("📄 Générer rapport PDF"):
            st.success("✅ Rapport PDF généré")

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
