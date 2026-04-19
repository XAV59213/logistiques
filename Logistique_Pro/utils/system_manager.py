# utils/system_manager.py
from pathlib import Path
from config import Config


def ensure_directories() -> bool:
    for rel in [
        "data/backups",
        "data/reservations",
        "data/stock",
        "data/inventaires",
        "assets/icons",
        "assets/photos",
        "assets/logo",
        "assets/profiles",
        "assets/logos_users",
        "assets/vehicules",
        "assets/outils",
        "assets/signatures",
    ]:
        Path(rel).mkdir(parents=True, exist_ok=True)
    return True


def maintenance_status() -> dict:
    return {
        "enabled": Config.SITE_MAINTENANCE_ENABLED,
        "message": Config.SITE_MAINTENANCE_MESSAGE,
    }
