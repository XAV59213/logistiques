# pages/07_Calendrier_Evenements.py
"""
Page Calendrier des Événements
Affichage du calendrier des événements avec intégration météo et alertes.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import utils.weather as weather
import utils.database as db

def show() -> None:
    """Affiche la page Calendrier des Événements."""
    st.title("📅 Calendrier des Événements")
    st.caption("Vue globale des événements programmés avec météo")

    user = st.session_state.user
    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    # ====================== FILTRES ======================
    col1, col2 = st.columns(2)
    with col1:
        periode = st.selectbox("Période", ["Cette semaine", "Ce mois", "30 prochains jours", "Tout"])
    with col2:
        filtre_type = st.multiselect("Type d'événement", ["Mariage", "Fête communale", "Concert", "Réunion", "Autre"], default=["Mariage", "Fête communale"])

    # ====================== CALENDRIER ======================
    st.subheader("📆 Événements à venir")

    # Données de démonstration réalistes
    events_data = [
        {"Date": "22/04/2026", "Événement": "Mariage Durand", "Lieu": "Salle des Fêtes", "Heure": "14:00", "Météo": "☀️ 18°C", "Statut": "Confirmé"},
        {"Date": "25/04/2026", "Événement": "Fête de printemps", "Lieu": "Parc communal", "Heure": "10:00", "Météo": "🌧️ 14°C", "Statut": "En préparation"},
        {"Date": "03/05/2026", "Événement": "Concert Place de l'Église", "Lieu": "Place de l'Église", "Heure": "20:00", "Météo": "🌤️ 16°C", "Statut": "Confirmé"},
    ]

    df = pd.DataFrame(events_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ====================== MÉTÉO INTÉGRÉE ======================
    st.subheader("🌤 Météo sur les événements")
    weather.display_weather_widget()

    # Alertes météo pour les événements à venir
    st.warning("⚠️ Alerte : Pluie possible le 25/04 pour la Fête de printemps → prévoir barnum supplémentaire")

    # ====================== ACTIONS ======================
    if st.button("➕ Ajouter un nouvel événement"):
        st.success("Formulaire d'ajout d'événement ouvert (simulation)")

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
