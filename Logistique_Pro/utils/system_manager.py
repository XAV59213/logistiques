from pathlib import Path
from config import Config

def ensure_directories():
    for rel in [
        "data/backups", "data/reservations", "data/stock", "data/inventaires",
        "assets/icons", "assets/photos"
    ]:
        Path(rel).mkdir(parents=True, exist_ok=True)
    return True

def maintenance_status():
    return {
        "enabled": Config.SITE_MAINTENANCE_ENABLED,
        "message": Config.SITE_MAINTENANCE_MESSAGE,
    }
