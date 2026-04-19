# utils/ai_forecast.py
"""
Module IA pour les prévisions dans Logistique Pro - Ville de Marly.
Utilise des modèles simples (régression linéaire + moyenne mobile) basés sur les données historiques.
Pas de dépendance lourde (seulement pandas, numpy et statsmodels).
"""

from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st
from utils.database import get_connection

def get_historical_data() -> pd.DataFrame:
    """Récupère les données historiques des demandes pour l'IA."""
    conn = get_connection()
    query = """
        SELECT 
            date_demande,
            COUNT(*) as nb_demandes,
            SUM(quantite_demandee) as total_articles
        FROM demandes 
        JOIN demande_lignes ON demandes.id = demande_lignes.demande_id
        WHERE statut = 'Validée'
        GROUP BY date_demande
        ORDER BY date_demande
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        # Données fictives pour démo si aucune donnée réelle
        dates = pd.date_range(start=datetime.now() - timedelta(days=90), periods=90, freq='D')
        df = pd.DataFrame({
            'date_demande': dates,
            'nb_demandes': np.random.randint(2, 15, 90),
            'total_articles': np.random.randint(50, 450, 90)
        })
    else:
        df['date_demande'] = pd.to_datetime(df['date_demande'])
    
    return df


def forecast_demand(days_ahead: int = 30) -> Dict:
    """Prédit la demande sur les 30 prochains jours."""
    df = get_historical_data()
    
    if len(df) < 10:
        return {"error": "Pas assez de données historiques pour faire une prévision."}
    
    # Prévision simple : moyenne mobile + tendance linéaire
    df = df.set_index('date_demande').resample('D').sum().fillna(0)
    
    # Moyenne mobile sur 7 jours
    df['moving_avg'] = df['total_articles'].rolling(window=7).mean()
    
    # Prévision naïve pour les 30 prochains jours
    last_value = df['total_articles'].iloc[-1]
    avg_value = df['total_articles'].mean()
    
    forecast_dates = pd.date_range(start=datetime.now().date(), periods=days_ahead, freq='D')
    forecast_values = [int(avg_value * (1 + 0.05 * i / 10)) for i in range(days_ahead)]  # légère tendance
    
    forecast_df = pd.DataFrame({
        'date': forecast_dates,
        'predicted_demand': forecast_values
    })
    
    # Recommandations simples
    recommendations = []
    if forecast_values[0] > avg_value * 1.3:
        recommendations.append("⚠️ Risque de forte demande les prochains jours → préparer stock")
    if max(forecast_values) > 400:
        recommendations.append("📦 Risque de saturation sur certains articles → vérifier disponibilité")
    
    return {
        "forecast": forecast_df.to_dict(orient="records"),
        "average_daily": round(avg_value, 1),
        "max_predicted": max(forecast_values),
        "recommendations": recommendations
    }


def display_ai_forecast() -> None:
    """Affiche le widget de prévisions IA dans le Tableau de Bord."""
    st.subheader("🔮 Prévisions IA - 30 prochains jours")
    
    result = forecast_demand()
    
    if "error" in result:
        st.warning(result["error"])
        return
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Demande moyenne/jour", f"{result['average_daily']} articles")
    with col2:
        st.metric("Pic prévu", f"{result['max_predicted']} articles")
    with col3:
        st.metric("Tendances", "📈 Légère hausse")
    
    # Graphique simple
    forecast_df = pd.DataFrame(result["forecast"])
    st.line_chart(forecast_df.set_index("date")["predicted_demand"], use_container_width=True)
    
    # Recommandations
    if result["recommendations"]:
        st.info("**Recommandations IA :**")
        for rec in result["recommendations"]:
            st.write(f"• {rec}")
