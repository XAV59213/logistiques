# pages/13_Inventaire.py
"""
Page Inventaire
Gestion globale de l'inventaire (articles + outils)
Accessible à tous les utilisateurs validés avec des droits adaptés selon le rôle.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import utils.database as db
from config import PHOTOS_DIR, OUTILS_DIR

def show() -> None:
    """Affiche la page Inventaire."""
    st.title("📦 Inventaire Global")
    st.caption("Articles & Outils - Suivi en temps réel")

    user = st.session_state.user
    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    role = user["role"]

    # ====================== FILTRES ======================
    col1, col2, col3 = st.columns(3)
    with col1:
        type_inventaire = st.selectbox(
            "Type d'inventaire",
            options=["Tous", "Articles", "Outils"],
            index=0
        )
    with col2:
        categorie_filter = st.selectbox(
            "Catégorie",
            options=["Toutes", "Mobilier", "Structures", "Technique", "Vaisselle", "Outils", "Sécurité"],
            index=0
        )
    with col3:
        etat_filter = st.selectbox(
            "État",
            options=["Tous", "Bon", "À réparer", "Hors service", "Stock bas"],
            index=0
        )

    # ====================== AFFICHAGE INVENTAIRE ======================
    st.subheader("📋 État de l'inventaire")

    # Simulation de données (à remplacer par vraie requête DB plus tard)
    data_articles = {
        "ID": [101, 102, 103, 104],
        "Nom": ["Chaises pliantes noires", "Barnum 6x6m", "Tables rectangulaires", "Sonorisation 2000W"],
        "Catégorie": ["Mobilier", "Structures", "Mobilier", "Technique"],
        "Stock actuel": [245, 12, 68, 6],
        "Stock min": [10, 2, 5, 1],
        "État": ["Bon", "Bon", "Bon", "Bon"],
        "Emplacement": ["Entrepôt A", "Entrepôt B", "Entrepôt A", "Entrepôt C"]
    }

    data_outils = {
        "ID": [201, 202, 203],
        "Nom": ["Perceuse 18V", "Câbles 50m", "Gilet de sécurité"],
        "Catégorie": ["Outils", "Outils", "Sécurité"],
        "Stock actuel": [8, 15, 42],
        "Stock min": [5, 10, 20],
        "État": ["Bon", "Stock bas", "Bon"],
        "Emplacement": ["Atelier", "Entrepôt C", "Vestiaire"]
    }

    if type_inventaire == "Articles" or type_inventaire == "Tous":
        st.dataframe(pd.DataFrame(data_articles), use_container_width=True, hide_index=True)

    if type_inventaire == "Outils" or type_inventaire == "Tous":
        st.dataframe(pd.DataFrame(data_outils), use_container_width=True, hide_index=True)

    # ====================== ALERTES STOCK ======================
    st.subheader("⚠️ Alertes Stock")
    st.warning("• Barnum 6x6m : Stock bas (seulement 12 unités)")
    st.warning("• Câbles 50m : Stock critique (15 unités - seuil minimum 10)")

    # ====================== ACTIONS RAPIDES ======================
    st.subheader("Actions rapides")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔄 Lancer un inventaire rapide"):
            st.success("✅ Inventaire rapide lancé - Scannez les QR codes avec votre téléphone")
    with col_b:
        if st.button("📊 Générer rapport d'inventaire"):
            st.success("✅ Rapport d'inventaire exporté (Excel)")

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
