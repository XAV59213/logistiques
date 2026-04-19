# pages/04_Catalogue_Articles.py
"""
Page Catalogue Articles
Grille visuelle des articles avec photos, filtres et stock restant.
Accessible à tous les rôles (lecture seule pour la plupart, édition pour admin).
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import utils.database as db
from config import PHOTOS_DIR

def show() -> None:
    """Affiche la page Catalogue Articles."""
    st.title("📦 Catalogue Articles")
    st.caption("Logistique Événements - Stock en temps réel")

    user = st.session_state.user
    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    role = user["role"]

    # ====================== FILTRES ======================
    col1, col2, col3 = st.columns(3)
    with col1:
        search = st.text_input("🔍 Rechercher un article")
    with col2:
        categorie = st.selectbox(
            "Catégorie",
            ["Toutes", "Mobilier", "Structures", "Technique", "Vaisselle", "Divers"]
        )
    with col3:
        stock_filter = st.selectbox(
            "Niveau de stock",
            ["Tous", "Stock OK", "Stock bas", "Stock critique"]
        )

    # ====================== AFFICHAGE GRILLE ======================
    st.subheader("Articles disponibles")

    # Données de démonstration réalistes
    catalogue_data = [
        {"Nom": "Chaises pliantes noires", "Catégorie": "Mobilier", "Stock": 245, "Stock min": 10, "État": "OK", "Prix": "4,50 €"},
        {"Nom": "Barnum 6x6m blanc", "Catégorie": "Structures", "Stock": 12, "Stock min": 2, "État": "Bas", "Prix": "450 €"},
        {"Nom": "Tables rectangulaires 180cm", "Catégorie": "Mobilier", "Stock": 68, "Stock min": 5, "État": "OK", "Prix": "28 €"},
        {"Nom": "Sonorisation 2000W", "Catégorie": "Technique", "Stock": 6, "Stock min": 1, "État": "OK", "Prix": "890 €"},
        {"Nom": "Mange-debout hautes", "Catégorie": "Mobilier", "Stock": 42, "Stock min": 8, "État": "OK", "Prix": "45 €"},
    ]

    df = pd.DataFrame(catalogue_data)

    # Filtrage
    if search:
        df = df[df["Nom"].str.contains(search, case=False)]
    if categorie != "Toutes":
        df = df[df["Catégorie"] == categorie]

    # Affichage en grille
    for idx, row in df.iterrows():
        col_a, col_b = st.columns([1, 4])
        with col_a:
            st.image("https://via.placeholder.com/150", width=120)  # Placeholder photo
        with col_b:
            st.write(f"**{row['Nom']}**")
            st.write(f"Catégorie : {row['Catégorie']} | Stock : **{row['Stock']}** (min {row['Stock min']})")
            st.write(f"État : {row['État']} | Prix unitaire : {row['Prix']}")
            
            if role == "admin":
                col_edit, col_del = st.columns(2)
                with col_edit:
                    if st.button("✏️ Modifier", key=f"edit_{idx}"):
                        st.info(f"Modification de {row['Nom']} (simulation)")
                with col_del:
                    if st.button("🗑️ Supprimer", key=f"del_{idx}"):
                        st.warning(f"{row['Nom']} supprimé (simulation)")

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
