# utils/weather.py
"""
Module de gestion de la météo pour Logistique Pro - Ville de Marly.
Utilise l'API Open-Meteo (gratuite, sans clé API).
Coordonnées : Marly (Moselle) → lat=49.0667, lon=6.15
"""

import requests
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import streamlit as st

# Coordonnées de Marly (Moselle)
MARLY_LAT = 49.0667
MARLY_LON = 6.15

def get_current_weather() -> Dict:
    """Récupère la météo actuelle pour Marly."""
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={MARLY_LAT}&longitude={MARLY_LON}"
            f"&current_weather=true&timezone=Europe/Paris"
        )
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        current = data["current_weather"]
        return {
            "temperature": round(current["temperature"], 1),
            "windspeed": round(current["windspeed"], 1),
            "winddirection": current["winddirection"],
            "weathercode": current["weathercode"],
            "time": current["time"],
            "is_day": current["is_day"]
        }
    except Exception as e:
        st.error(f"Erreur lors de la récupération de la météo actuelle : {e}")
        return {"temperature": 0, "windspeed": 0, "weathercode": 0, "error": True}


def get_7day_forecast() -> List[Dict]:
    """Récupère les prévisions sur 7 jours."""
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={MARLY_LAT}&longitude={MARLY_LON}"
            f"&daily=weathercode,temperature_2m_max,temperature_2m_min,"
            f"precipitation_sum,windspeed_10m_max&timezone=Europe/Paris"
        )
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        forecast = []
        for i in range(7):
            forecast.append({
                "date": data["daily"]["time"][i],
                "temp_max": round(data["daily"]["temperature_2m_max"][i], 1),
                "temp_min": round(data["daily"]["temperature_2m_min"][i], 1),
                "precipitation": round(data["daily"]["precipitation_sum"][i], 1),
                "windspeed_max": round(data["daily"]["windspeed_10m_max"][i], 1),
                "weathercode": data["daily"]["weathercode"][i]
            })
        return forecast
    except Exception as e:
        st.error(f"Erreur lors de la récupération des prévisions : {e}")
        return []


def get_weather_alerts(forecast: List[Dict]) -> List[Dict]:
    """Détecte les alertes météo importantes."""
    alerts = []
    for day in forecast:
        alert = None
        if day["precipitation"] > 5:
            alert = {"level": "rouge", "message": "Pluie forte prévue", "icon": "🌧️"}
        elif day["windspeed_max"] > 40:
            alert = {"level": "orange", "message": "Vent fort", "icon": "🌬️"}
        elif day["temp_max"] > 32 or day["temp_min"] < -5:
            alert = {"level": "rouge", "message": "Température extrême", "icon": "🌡️"}
        
        if alert:
            alerts.append({"date": day["date"], **alert})
    
    return alerts


def display_weather_widget() -> None:
    """Affiche un widget météo complet dans le tableau de bord ou sidebar."""
    st.subheader("🌤 Météo à Marly")
    
    current = get_current_weather()
    if "error" in current:
        st.warning("Impossible de récupérer la météo pour le moment.")
        return
    
    col1, col2 = st.columns([1, 3])
    with col1:
        st.metric("Température", f"{current['temperature']}°C")
    with col2:
        st.write(f"🌬️ Vent : {current['windspeed']} km/h")
    
    # Prévisions 7 jours
    forecast = get_7day_forecast()
    alerts = get_weather_alerts(forecast)
    
    if alerts:
        st.warning("⚠️ Alertes météo détectées")
        for alert in alerts:
            st.error(f"{alert['icon']} {alert['date']} → {alert['message']}")
    
    # Affichage simple des prévisions
    with st.expander("Prévisions 7 jours", expanded=False):
        for day in forecast[:7]:
            st.write(f"**{day['date']}** : {day['temp_min']}°C → {day['temp_max']}°C | 💧 {day['precipitation']} mm | 🌬️ {day['windspeed_max']} km/h")
