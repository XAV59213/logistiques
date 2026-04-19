# pages/08_Planning_Equipes.py
"""
Page Planning des Équipes
Gestion du planning des interventions (livraison, montage, démontage).
Accessible selon les rôles avec des vues adaptées.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import utils.database as db

def show() -> None:
    """Affiche la page Planning des Équipes."""
    st.title("📅 Planning des Équipes")
    st.caption("Gestion des interventions - Livraison, Montage, Démontage")

    user = st.session_state.user
    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    role = user["role"]

    # ====================== FILTRES ======================
    col1, col2, col3 = st.columns(3)
    with col1:
        date_filter = st.date_input("Date", value=datetime.today())
    with col2:
        type_tache = st.multiselect("Type de tâche", ["Livraison", "Montage", "Démontage", "Retour"], default=["Livraison", "Montage"])
    with col3:
        equipe_filter = st.selectbox("Équipe", ["Toutes", "Équipe Alpha", "Équipe Beta", "Équipe Gamma"])

    # ====================== PLANNING PRINCIPAL ======================
    st.subheader("Interventions planifiées")

    # Données de démonstration réalistes
    planning_data = [
        {"Date": "22/04/2026", "Heure": "08:00", "Tâche": "Livraison + Montage", "Événement": "Mariage Durand", "Équipe": "Équipe Alpha", "Véhicule": "75-BC-1234", "Statut": "Planifié"},
        {"Date": "23/04/2026", "Heure": "09:30", "Tâche": "Montage", "Événement": "Fête communale", "Équipe": "Équipe Beta", "Véhicule": "57-XY-9876", "Statut": "En cours"},
        {"Date": "25/04/2026", "Heure": "14:00", "Tâche": "Démontage", "Événement": "Concert Place de l'Église", "Équipe": "Équipe Alpha", "Véhicule": "75-BC-1234", "Statut": "Planifié"},
    ]

    df = pd.DataFrame(planning_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ====================== VUE SPÉCIFIQUE SELON RÔLE ======================
    if role == "equipe_interne":
        st.success("👷‍♂️ Vue Équipe Interne - Vous voyez uniquement vos interventions assignées")
        if st.button("✅ Marquer comme terminé + Signer"):
            st.success("Intervention signée et stock mis à jour !")

    elif role == "admin" or role == "interne":
        st.subheader("Assignation rapide")
        selected_event = st.selectbox("Sélectionner une intervention à assigner", df["Événement"].tolist())
        equipe_assign = st.selectbox("Assigner à l'équipe", ["Équipe Alpha", "Équipe Beta", "Équipe Gamma"])
        if st.button("Assigner l'équipe"):
            st.success(f"Équipe {equipe_assign} assignée à {selected_event}")

    # ====================== DÉTECTION DE CONFLITS ======================
    st.subheader("⚠️ Détection de conflits")
    st.info("Aucun conflit détecté pour le moment.")

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
