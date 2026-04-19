# config.py
from pathlib import Path
import streamlit as st

# ====================== CHEMINS DE BASE ======================
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"

# Dossiers principaux
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

# Création automatique de tous les dossiers
for directory in [
    DATA_DIR, ASSETS_DIR, LOGO_DIR, PHOTOS_DIR, PROFILES_DIR,
    LOGOS_USERS_DIR, VEHICULES_DIR, ASSURANCES_DIR,
    MAINTENANCE_VEHICULES_DIR, OUTILS_DIR, SIGNATURES_DIR, BACKUPS_DIR
]:
    directory.mkdir(parents=True, exist_ok=True)

# ====================== CONFIGURATION PAR DÉFAUT ======================
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

# ====================== CHEMINS UTILES ======================
DB_PATH = str(DATA_DIR / "logistique_marly.db")

# ====================== FONCTION D'INITIALISATION ======================
def init_config():
    """Initialise la configuration et retourne les paramètres par défaut"""
    # On peut charger ici des paramètres depuis la base si besoin (future évolution)
    return DEFAULT_CONFIG


# ====================== EXÉCUTION AU CHARGEMENT ======================
if __name__ == "__main__":
    init_config()
    print("✅ Configuration initialisée avec succès.")
