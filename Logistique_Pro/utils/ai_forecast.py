# utils/ai_forecast.py
"""
Module IA pour les prévisions dans Logistique Pro - Ville de Marly.
Version sécurisée : si les tables métier n'existent pas encore,
des données de démonstration sont utilisées.
"""

from typing import Dict
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import streamlit as st

from utils.database import get_connection


def get_demo_dataframe() -> pd.DataFrame:
    dates = pd.date_range(start=datetime.now() - timedelta(days=90), periods=90, freq="D")
    return pd.DataFrame(
        {
            "date_demande": dates,
            "nb_demandes": np.random.randint(2, 15, 90),
            "total_articles": np.random.randint(50, 450, 90),
        }
    )


def get_historical_data() -> pd.DataFrame:
    """
    Récupère les données historiques des demandes validées.
    On utilise la date de création de la demande comme base temporelle,
    car la table ne contient pas de colonne date_demande.
    """
    try:
        conn = get_connection()
        query = """
            SELECT
                date(d.created_at) AS date_demande,
                COUNT(DISTINCT d.id) AS nb_demandes,
                COALESCE(SUM(dl.quantite_demandee), 0) AS total_articles
            FROM demandes d
            LEFT JOIN demande_lignes dl ON d.id = dl.demande_id
            WHERE d.statut = 'Validée'
            GROUP BY date(d.created_at)
            ORDER BY date(d.created_at)
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            return get_demo_dataframe()

        df["date_demande"] = pd.to_datetime(df["date_demande"], errors="coerce")
        df["nb_demandes"] = pd.to_numeric(df["nb_demandes"], errors="coerce").fillna(0)
        df["total_articles"] = pd.to_numeric(df["total_articles"], errors="coerce").fillna(0)

        df = df.dropna(subset=["date_demande"]).sort_values("date_demande")

        if df.empty:
            return get_demo_dataframe()

        return df

    except Exception:
        return get_demo_dataframe()


def forecast_demand(days_ahead: int = 30) -> Dict:
    """
    Produit une prévision simple à partir de l'historique.
    Ce n'est pas un vrai modèle ML, mais une projection robuste.
    """
    df = get_historical_data()

    if len(df) < 10:
        return {"error": "Pas assez de données historiques pour faire une prévision."}

    df = df.set_index("date_demande").resample("D").sum().fillna(0)

    avg_value = float(df["total_articles"].mean())
    avg_value = max(avg_value, 1.0)

    recent_trend = float(df["total_articles"].tail(14).mean()) if len(df) >= 14 else avg_value
    growth_factor = 1.0

    if recent_trend > avg_value:
        growth_factor = min(1.20, 1 + ((recent_trend - avg_value) / max(avg_value, 1)) * 0.2)
    elif recent_trend < avg_value:
        growth_factor = max(0.85, 1 - ((avg_value - recent_trend) / max(avg_value, 1)) * 0.1)

    forecast_dates = pd.date_range(start=datetime.now().date(), periods=days_ahead, freq="D")
    forecast_values = []

    for i in range(days_ahead):
        progressive_factor = 1 + (i / max(days_ahead, 1)) * 0.05
        predicted = int(avg_value * growth_factor * progressive_factor)
        forecast_values.append(max(predicted, 1))

    forecast_df = pd.DataFrame(
        {
            "date": forecast_dates,
            "predicted_demand": forecast_values,
        }
    )

    recommendations = []
    if forecast_values[0] > avg_value * 1.3:
        recommendations.append("⚠️ Risque de forte demande les prochains jours → préparer le stock.")
    if max(forecast_values) > 400:
        recommendations.append("📦 Risque de saturation sur certains articles → vérifier la disponibilité.")
    if growth_factor > 1.05:
        recommendations.append("📈 Tendance haussière détectée sur les demandes validées.")
    elif growth_factor < 0.95:
        recommendations.append("📉 Tendance plus calme observée sur la période récente.")

    return {
        "forecast": forecast_df.to_dict(orient="records"),
        "average_daily": round(avg_value, 1),
        "max_predicted": max(forecast_values),
        "recommendations": recommendations,
    }


def display_ai_forecast() -> None:
    """Affiche le widget de prévisions IA dans le tableau de bord."""
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
        st.metric("Tendance", "📈 Projection calculée")

    forecast_df = pd.DataFrame(result["forecast"])
    st.line_chart(
        forecast_df.set_index("date")["predicted_demand"],
        use_container_width=True,
    )

    if result["recommendations"]:
        st.info("**Recommandations IA :**")
        for rec in result["recommendations"]:
            st.write(f"• {rec}")
