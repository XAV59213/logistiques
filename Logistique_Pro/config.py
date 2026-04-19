======= CHEMINS DE BASE ======================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"

LOGO_DIR = ASSETS_DIR / "logo"
PHOTOS_DIR = ASSETS_DIR / "photos"
PROFILES_DIR = ASSETS_DIR / "profiles"
LOGOS_USERS_DIR = ASSETS_DIR / "logos_users"
VEHICULES_DIR = ASSETS_DIR / "vehicules"
ASSURANCES_DIR = ASSETS_DIR / "assurances"
MAINTENANCE_VEHICULES_DIR = ASSETS_DIR / "maintenance_vehicules"
OUTILS_DIR = ASSETS_DIR / "outils"
SIGNATURES_DIR = ASSETS_DIR / "signatures"
BACKUPS_DIR = DATA_DIR / "backups"

for directory in [
    DATA_DIR,
    ASSETS_DIR,
    LOGO_DIR,
    PHOTOS_DIR,
    PROFILES_DIR,
    LOGOS_USERS_DIR,
    VEHICULES_DIR,
    ASSURANCES_DIR,
    MAINTENANCE_VEHICULES_DIR,
    OUTILS_DIR,
    SIGNATURES_DIR,
    BACKUPS_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)

DB_PATH = str(DATA_DIR / "logistique_marly.db")

DEFAULT_CONFIG = {
    "site_title": "Logistique Pro - Ville de Marly",
    "site_subtitle": "Service Logistique & Événements",
    "primary_color": "#003366",
    "secondary_color": "#f8f9fa",
    "accent_color": "#ffc107",
    "contact_email": "logistique@ville-marly.fr",
    "contact_phone": "03 87 00 00 00",
    "address": "Hôtel de Ville, Place de la Mairie, 57155 Marly",
    "default_theme": "Municipal Bleu",
}

# ====================== VARIABLES ENV ======================
APP_NAME = os.getenv("APP_NAME", DEFAULT_CONFIG["site_title"])
APP_ENV = os.getenv("APP_ENV", "dev")
SECRET_KEY = os.getenv("SECRET_KEY", "change_me")

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
SMS_ACCOUNT_SID = os.getenv("SMS_ACCOUNT_SID", "")
SMS_AUTH_TOKEN = os.getenv("SMS_AUTH_TOKEN", "")
SMS_FROM = os.getenv("SMS_FROM", "")

WEATHER_ENABLED = os.getenv("WEATHER_ENABLED", "false").lower() == "true"
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
WEATHER_CITY = os.getenv("WEATHER_CITY", "Marly")


def init_config():
    return DEFAULT_CONFIG


class Config:
    BASE_DIR = BASE_DIR
    DATA_DIR = DATA_DIR
    ASSETS_DIR = ASSETS_DIR
    DB_PATH = DB_PATH

    DEFAULT_ADMIN_EMAIL = DEFAULT_ADMIN_EMAIL
    DEFAULT_ADMIN_PASSWORD = DEFAULT_ADMIN_PASSWORD

    SITE_MAINTENANCE_ENABLED = SITE_MAINTENANCE_ENABLED
    SITE_MAINTENANCE_MESSAGE = SITE_MAINTENANCE_MESSAGE

    SMS_ENABLED = SMS_ENABLED
    WEATHER_ENABLED = WEATHER_ENABLED


if __name__ == "__main__":
    init_config()
    print("✅ Configuration initialisée avec succès.")
