# pages/03_Tableau_de_bord.py
"""
Page Tableau de Bord
Version dynamique selon le rôle de l'utilisateur.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import utils.database as db
import utils.weather as weather
import utils.ai_forecast as ai_forecast
from config import DEFAULT_CONFIG

def show() -> None:
    """Affiche le Tableau de Bord adapté au rôle de l'utilisateur."""
    st.title("📊 Tableau de Bord")
    user = st.session_state.user

    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    role = user["role"]
    status = user.get("status", "pending")

    if status == "pending":
        st.warning("Votre compte est en attente de validation.")
        st.stop()

    # ====================== NOTIFICATIONS ======================
    st.subheader("🛎️ Notifications")
    # Simulation de notifications (à remplacer par vraie requête DB)
    notifications = [
        {"title": "Nouvelle demande validée", "message": "Demande #487 - Barnum 6x6m", "type": "info"},
        {"title": "Alerte maintenance", "message": "Véhicule 75-BC-1234 - Révision due", "type": "warning"},
    ]

    for notif in notifications:
        st.markdown(f"""
        <div class="notification-card">
            <strong>{notif['title']}</strong><br>
            {notif['message']}
        </div>
        """, unsafe_allow_html=True)

    # ====================== ROLE-SPECIFIC DASHBOARD ======================
    if role == "admin" or role == "interne":
        # Vue Admin / Interne
        st.subheader("📈 Vue d'ensemble")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Demandes en attente", "7")
        with col2:
            st.metric("Événements cette semaine", "12")
        with col3:
            st.metric("Stock critique", "4 articles")
        with col4:
            st.metric("Véhicules disponibles", "9 / 14")

        # Météo
        weather.display_weather_widget()

        # Prévisions IA
        st.subheader("🔮 Prévisions IA (30 jours)")
        ai_forecast.display_ai_forecast()

        # Dernières demandes
        st.subheader("Dernières demandes validées")
        st.info("Tableau des 5 dernières demandes validées (simulation)")

    elif role == "equipe_interne":
        # Vue spécifique Équipe Interne
        st.subheader("🚛 Interventions à réaliser")
        
        # Simulation de demandes validées
        data = {
            "N° Demande": ["487", "492", "495"],
            "Événement": ["Mariage Dupont", "Fête communale", "Concert Place de l'Église"],
            "Date / Heure": ["21/04/2026 08:00", "22/04/2026 14:00", "23/04/2026 09:30"],
            "Lieu": ["Salle des Fêtes", "Parc communal", "Place de l'Église"],
            "Tâche": ["Livraison + Montage", "Montage", "Livraison"],
            "Stock restant critique": ["Chaises: 12", "Barnum: OK", "Tables: 8"]
        }
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)

        st.info("**Actions rapides** : Cliquez sur une ligne pour marquer comme terminé et signer.")

        if st.button("✅ Marquer intervention terminée + Signer"):
            st.success("Intervention signée avec succès ! Stock mis à jour.")

    else:
        # Vue standard (association, externe, client)
        st.subheader("📋 Mes dernières demandes")
        st.info("Vous n'avez pas de demande en cours pour le moment.")

    # Footer
    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
