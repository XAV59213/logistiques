# config.py
import os
from pathlib import Path

# Chemins de base
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"
LOGO_DIR = ASSETS_DIR / "logo"
PHOTOS_DIR = ASSETS_DIR / "photos"
SIGNATURES_DIR = ASSETS_DIR / "signatures"
BACKUPS_DIR = DATA_DIR / "backups"

# Création des dossiers
for directory in [DATA_DIR, ASSETS_DIR, LOGO_DIR, PHOTOS_DIR, SIGNATURES_DIR, BACKUPS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Configuration par défaut
DEFAULT_CONFIG = {
    "site_title": "Logistique Pro - Ville de Marly",
    "site_subtitle": "Service Logistique & Événements",
    "primary_color": "#003366",
    "contact_email": "logistique@ville-marly.fr",
    "contact_phone": "03 87 00 00 00",
    "address": "Hôtel de Ville, Place de la Mairie, 57155 Marly",
}

DB_PATH = str(DATA_DIR / "logistique_marly.db")
