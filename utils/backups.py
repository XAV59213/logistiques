from pathlib import Path
from datetime import datetime
import shutil
from config import Config


BACKUP_DIR = Path("data/backups")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def create_backup():
    db_path = Path(Config.DB_PATH)

    if not db_path.exists():
        return False, "Base de données introuvable"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"backup_{timestamp}.db"

    shutil.copy2(db_path, backup_file)
    return True, str(backup_file)


def list_backups():
    return sorted(BACKUP_DIR.glob("*.db"), reverse=True)


def delete_backup(file_name: str):
    file_path = BACKUP_DIR / file_name
    if file_path.exists():
        file_path.unlink()
        return True
    return False
