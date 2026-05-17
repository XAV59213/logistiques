# -*- coding: utf-8 -*-
from __future__ import annotations

import shutil
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st

from administration_systeme.common import APP_DIR, BACKUP_DIR, PATCH_BACKUP_DIR, fmt_size


def count_path(path: Path) -> tuple[int, int]:
    total_files = 0
    total_size = 0

    if not path.exists():
        return 0, 0

    if path.is_file():
        return 1, path.stat().st_size

    for p in path.rglob("*"):
        try:
            if p.is_file():
                total_files += 1
                total_size += p.stat().st_size
        except Exception:
            pass

    return total_files, total_size


def delete_pycache() -> tuple[int, int]:
    deleted_dirs = 0
    deleted_files = 0

    for p in APP_DIR.rglob("__pycache__"):
        try:
            if p.is_dir():
                files, _ = count_path(p)
                shutil.rmtree(p, ignore_errors=True)
                deleted_dirs += 1
                deleted_files += files
        except Exception:
            pass

    for p in APP_DIR.rglob("*.pyc"):
        try:
            if p.is_file():
                p.unlink()
                deleted_files += 1
        except Exception:
            pass

    return deleted_dirs, deleted_files


def old_zip_files(days: int) -> list[Path]:
    limit = datetime.now() - timedelta(days=days)
    files = []

    for root in [BACKUP_DIR, PATCH_BACKUP_DIR]:
        if not root.exists():
            continue

        for p in root.glob("*.zip"):
            try:
                mtime = datetime.fromtimestamp(p.stat().st_mtime)
                if mtime < limit:
                    files.append(p)
            except Exception:
                pass

    return sorted(files, key=lambda x: x.stat().st_mtime)


def temp_files() -> list[Path]:
    patterns = [
        "*.tmp",
        "*.temp",
        "*.bak",
        "*.old",
        "*.log",
    ]

    results = []

    for pattern in patterns:
        for p in APP_DIR.rglob(pattern):
            try:
                if p.is_file():
                    if ".venv" in str(p) or "/.git/" in str(p):
                        continue
                    results.append(p)
            except Exception:
                pass

    return sorted(results)


def render():
    st.subheader("🧹 Nettoyage système")

    st.info(
        "Ce module nettoie uniquement les éléments non critiques : caches Python, fichiers temporaires, "
        "anciennes sauvegardes ZIP. Les bases de données ne sont jamais supprimées ici."
    )

    st.markdown("### Caches Python")

    pycache_count = len(list(APP_DIR.rglob("__pycache__")))
    pyc_count = len(list(APP_DIR.rglob("*.pyc")))

    c1, c2 = st.columns(2)
    c1.metric("__pycache__", pycache_count)
    c2.metric("Fichiers .pyc", pyc_count)

    if st.button("Nettoyer les caches Python", type="primary", width="stretch", key="clean_pycache"):
        dirs, files = delete_pycache()
        st.success(f"Nettoyage terminé : {dirs} dossier(s), {files} fichier(s) supprimé(s).")
        st.rerun()

    st.divider()

    st.markdown("### Anciennes sauvegardes ZIP")

    days = st.number_input(
        "Supprimer les sauvegardes ZIP plus anciennes que X jours",
        min_value=1,
        max_value=365,
        value=30,
        step=1,
        key="clean_old_zip_days",
    )

    zips = old_zip_files(int(days))
    total_size = sum(p.stat().st_size for p in zips if p.exists())

    c1, c2 = st.columns(2)
    c1.metric("ZIP concernés", len(zips))
    c2.metric("Espace récupérable", fmt_size(total_size))

    if zips:
        with st.expander("Voir les sauvegardes concernées"):
            for p in zips[:100]:
                st.caption(f"{p.name} — {fmt_size(p.stat().st_size)}")

    confirm = st.checkbox("Je confirme la suppression des anciennes sauvegardes ZIP", key="confirm_delete_old_zips")

    if st.button("Supprimer les anciennes sauvegardes", disabled=not confirm, width="stretch", key="delete_old_zips"):
        deleted = 0
        for p in zips:
            try:
                p.unlink()
                deleted += 1
            except Exception:
                pass

        st.success(f"{deleted} sauvegarde(s) supprimée(s).")
        st.rerun()

    st.divider()

    st.markdown("### Fichiers temporaires")

    temps = temp_files()
    temp_size = sum(p.stat().st_size for p in temps if p.exists())

    c1, c2 = st.columns(2)
    c1.metric("Fichiers temporaires", len(temps))
    c2.metric("Taille", fmt_size(temp_size))

    if temps:
        with st.expander("Voir les fichiers temporaires"):
            for p in temps[:200]:
                st.caption(f"{p.relative_to(APP_DIR)} — {fmt_size(p.stat().st_size)}")

    confirm_temp = st.checkbox("Je confirme la suppression des fichiers temporaires", key="confirm_delete_temp")

    if st.button("Supprimer les fichiers temporaires", disabled=not confirm_temp, width="stretch", key="delete_temp_files"):
        deleted = 0

        for p in temps:
            try:
                p.unlink()
                deleted += 1
            except Exception:
                pass

        st.success(f"{deleted} fichier(s) temporaire(s) supprimé(s).")
        st.rerun()
