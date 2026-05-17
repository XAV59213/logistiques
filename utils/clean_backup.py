import zipfile
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/opt/logistique-pro")
BACKUP_DIR = BASE_DIR / "backups"

EXCLUDE_DIRS = {
    ".venv",
    "__pycache__",
    "backups",
    ".git",
}

EXCLUDE_SUFFIXES = {
    ".pyc",
    ".bak",
    ".tmp",
    ".log",
}

EXCLUDE_CONTAINS = [
    ".bak_",
    "database_20",
]


def should_exclude(path: Path) -> bool:
    rel_parts = path.relative_to(BASE_DIR).parts

    if any(part in EXCLUDE_DIRS for part in rel_parts):
        return True

    if path.suffix.lower() in EXCLUDE_SUFFIXES:
        return True

    name = path.name.lower()
    if any(x.lower() in name for x in EXCLUDE_CONTAINS):
        return True

    return False


def create_clean_backup():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = BACKUP_DIR / f"logistique_pro_clean_backup_{timestamp}.zip"

    restore_content = """#!/bin/bash
set -e

APP_DIR="/opt/logistique-pro"

echo "=== Restauration Logistique Pro ==="

cd "$APP_DIR"

echo "Création environnement Python..."
python3 -m venv .venv

echo "Mise à jour pip..."
.venv/bin/python -m pip install --upgrade pip setuptools wheel

echo "Installation dépendances..."
.venv/bin/pip install -r requirements.txt

echo "Nettoyage cache..."
find "$APP_DIR" -name "*.pyc" -delete
find "$APP_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

echo "Test compilation..."
.venv/bin/python -m py_compile main.py
.venv/bin/python -m py_compile pages/*.py
.venv/bin/python -m py_compile utils/*.py

echo "Redémarrage service..."
systemctl restart logistique.service

echo "Restauration terminée."
"""

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for file in BASE_DIR.rglob("*"):
            if file.is_file() and not should_exclude(file):
                z.write(file, file.relative_to(BASE_DIR))

        z.writestr("restore.sh", restore_content)

    return zip_path
