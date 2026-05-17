# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import streamlit as st


APP_DIR = Path("/opt/logistique-pro")
DATA_DIR = APP_DIR / "data"
BACKUP_DIR = DATA_DIR / "backups"
PATCH_BACKUP_DIR = DATA_DIR / "patch_backups"

for d in (DATA_DIR, BACKUP_DIR, PATCH_BACKUP_DIR):
    d.mkdir(parents=True, exist_ok=True)


def is_admin() -> bool:
    user = st.session_state.get("user") or st.session_state.get("current_user") or {}
    if isinstance(user, dict) and str(user.get("role", "")).lower() == "admin":
        return True
    return str(st.session_state.get("role", "")).lower() == "admin"


def run_cmd(cmd: list[str], timeout: int = 60) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            cmd,
            cwd=str(APP_DIR),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = ""
        if result.stdout:
            output += result.stdout.strip()
        if result.stderr:
            output += ("\n\n" if output else "") + result.stderr.strip()
        return result.returncode == 0, output or f"Code retour : {result.returncode}"
    except subprocess.TimeoutExpired:
        return False, f"Commande trop longue : timeout après {timeout} secondes."
    except Exception as exc:
        return False, str(exc)


def fmt_size(size: int) -> str:
    try:
        size = int(size)
    except Exception:
        return "N/A"

    units = ["o", "Ko", "Mo", "Go", "To"]
    value = float(size)

    for unit in units:
        if value < 1024:
            if unit == "o":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024

    return f"{value:.1f} Po"


def get_db_files() -> list[Path]:
    files: list[Path] = []

    for root in [DATA_DIR, APP_DIR]:
        if root.exists():
            files.extend(root.glob("*.db"))
            files.extend(root.glob("*.sqlite"))
            files.extend(root.glob("*.sqlite3"))

    unique = []
    seen = set()

    for f in files:
        try:
            key = str(f.resolve())
        except Exception:
            key = str(f)

        if key not in seen:
            unique.append(f)
            seen.add(key)

    priority = ["logistique_marly.db", "logistique.db", "database.db", "app.db"]

    def sort_key(path: Path):
        name = path.name.lower()
        if name in priority:
            return (0, priority.index(name))
        if "logistique" in name:
            return (1, name)
        return (2, name)

    return sorted(unique, key=sort_key)


def sqlite_tables(db: Path) -> list[str]:
    try:
        conn = sqlite3.connect(str(db))
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        rows = [r[0] for r in cur.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []


def sqlite_count(db: Path, table: str):
    try:
        conn = sqlite3.connect(str(db))
        cur = conn.cursor()
        cur.execute(f'SELECT COUNT(*) FROM "{table}"')
        value = cur.fetchone()[0]
        conn.close()
        return value
    except Exception:
        return "Erreur"


def skip_backup_file(path: Path) -> bool:
    s = str(path)

    excluded = [
        "/.git/",
        "/.venv/",
        "/venv/",
        "/__pycache__/",
        "/data/backups/",
        "/data/patch_backups/",
    ]

    if any(x in s for x in excluded):
        return True

    if path.suffix.lower() in [".pyc", ".pyo", ".log"]:
        return True

    return False


def create_project_backup() -> Path:
    backup = BACKUP_DIR / f"logistique_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

    with zipfile.ZipFile(backup, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(APP_DIR):
            root_path = Path(root)

            dirs[:] = [
                d for d in dirs
                if not skip_backup_file(root_path / d)
            ]

            for file in files:
                path = root_path / file

                if skip_backup_file(path):
                    continue

                z.write(path, path.relative_to(APP_DIR))

    return backup
