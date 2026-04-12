from config import Config

def get_weather_stub():
    if not Config.WEATHER_ENABLED:
        return {"enabled": False, "message": "Météo désactivée"}
    return {"enabled": True, "message": "Intégration météo à compléter"}
