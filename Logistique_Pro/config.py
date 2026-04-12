import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

class Config:
    APP_NAME = os.getenv("APP_NAME", "Logistique Pro - Ville de Marly")
    APP_ENV = os.getenv("APP_ENV", "dev")
    SECRET_KEY = os.getenv("SECRET_KEY", "change_me")

    DATA_DIR = BASE_DIR / "data"
    DB_PATH = DATA_DIR / "database.db"

    DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@marly.fr")
    DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "ChangeMe123!")

    DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "fr")
    DEFAULT_THEME = os.getenv("DEFAULT_THEME", "light")

    SITE_MAINTENANCE_ENABLED = os.getenv("SITE_MAINTENANCE_ENABLED", "false").lower() == "true"
    SITE_MAINTENANCE_MESSAGE = os.getenv("SITE_MAINTENANCE_MESSAGE", "Maintenance en cours")

    ENABLE_PREDICTIVE_AI = os.getenv("ENABLE_PREDICTIVE_AI", "false").lower() == "true"
    SMS_ENABLED = os.getenv("SMS_ENABLED", "false").lower() == "true"
    SMS_PROVIDER = os.getenv("SMS_PROVIDER", "")
    SMS_API_KEY = os.getenv("SMS_API_KEY", "")
    WEATHER_ENABLED = os.getenv("WEATHER_ENABLED", "false").lower() == "true"
    WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
