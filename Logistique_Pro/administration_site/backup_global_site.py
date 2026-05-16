# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st


PROJECT_DIR = Path("/opt/logistique-pro")
DATA_DIR = PROJECT_DIR / "data"

GLOBAL_BACKUP_DIR = DATA_DIR / "backups" / "site_global"
CODE_BACKUP_DIR = GLOBAL_BACKUP_DIR / "code_light"
DB_BACKUP_DIR = GLOBAL_BACKUP_DIR / "bases_config"
FILES_BACKUP_DIR = GLOBAL_BACKUP_DIR / "fichiers_lourds"

for folder in [GLOBAL_BACKUP_DIR, CODE_BACKUP_DIR, DB_BACKUP_DIR, FILES_BACKUP_DIR]:
    folder.mkdir(parents=True, exist_ok=True)


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _clean(value: Any) -> str:
    if value is None:
        return ""
    value = str(value)
    if value.lower() in ["none", "nan", "nat"]:
        return ""
    return value.strip()


def _file_size(path: Path) -> str:
    size = path.stat().st_size

    if size < 1024:
        return f"{size} o"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} Ko"
    if size < 1024 * 1024 * 1024:
        return f"{size / 1024 / 1024:.1f} Mo"

    return f"{size / 1024 / 1024 / 1024:.2f} Go"


def _folder_size(folder: Path) -> tuple[int, int]:
    if not folder.exists():
        return 0, 0

    total_size = 0
    total_files = 0

    for file in folder.rglob("*"):
        if file.is_file():
            try:
                total_size += file.stat().st_size
                total_files += 1
            except Exception:
                pass

    return total_size, total_files


def _download_file(path: Path, label: str) -> None:
    if not path.exists():
        st.error(f"Fichier introuvable : {path}")
        return

    with open(path, "rb") as f:
        st.download_button(
            label,
            data=f.read(),
            file_name=path.name,
            mime="application/zip",
            width="stretch",
            key=f"download_backup_{path.name}_{int(path.stat().st_mtime)}",
        )


def _zip_file(z: zipfile.ZipFile, file: Path, arcname: str | None = None) -> None:
    if file.exists() and file.is_file():
        z.write(file, arcname=arcname or str(file.relative_to(PROJECT_DIR)))


def _zip_dir(z: zipfile.ZipFile, folder: Path, arc_prefix: str) -> None:
    if not folder.exists():
        return

    for file in folder.rglob("*"):
        if file.is_file():
            z.write(file, arcname=f"{arc_prefix}/{file.relative_to(folder)}")


def _is_excluded_code_file(file: Path) -> bool:
    rel = file.relative_to(PROJECT_DIR)
    rel_str = str(rel)

    excluded_dirs = {
        ".venv",
        "venv",
        "__pycache__",
        ".git",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
    }

    excluded_roots = {
        "data/backups",
        "data/patch_backups",
        "data/exports",
        "data/uploads",
        "data/tmp",
        "data/patrimoine_documents",
        "data/patrimoine_photos",
        "data/garage_photos",
        "data/garage_documents",
        "data/article_images",
        "data/images",
        "data/documents",
        "data/photos",
        "backups",
        "assets/photos",
    }

    excluded_suffixes = {
        ".pyc",
        ".pyo",
        ".db",
        ".sqlite",
        ".sqlite3",
        ".zip",
        ".tar",
        ".gz",
        ".tgz",
        ".7z",
        ".rar",
        ".pdf",
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
        ".bmp",
        ".tiff",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".mp4",
        ".mov",
        ".avi",
        ".bak",
    }

    if set(rel.parts) & excluded_dirs:
        return True

    if any(rel_str.startswith(root + "/") or rel_str == root for root in excluded_roots):
        return True

    if file.suffix.lower() in excluded_suffixes:
        return True

    return False


def create_code_light_backup() -> Path:
    """
    Sauvegarde uniquement le code actif du site.
    Exclut les bases, documents, images, PDF, exports, patch_backups, .venv et caches.
    """
    zip_path = CODE_BACKUP_DIR / f"logistique_site_code_light_{_timestamp()}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for file in PROJECT_DIR.rglob("*"):
            if not file.is_file():
                continue

            if _is_excluded_code_file(file):
                continue

            z.write(file, arcname=str(file.relative_to(PROJECT_DIR)))

    return zip_path


def create_databases_backup() -> Path:
    """
    Sauvegarde toutes les bases SQLite et fichiers de configuration utiles.
    """
    zip_path = DB_BACKUP_DIR / f"logistique_site_bases_config_{_timestamp()}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        if DATA_DIR.exists():
            patterns = [
                "*.db",
                "*.sqlite",
                "*.sqlite3",
                "*.txt",
                "*.json",
                "*.yaml",
                "*.yml",
                "*.toml",
                "*.ini",
            ]

            for pattern in patterns:
                for file in DATA_DIR.glob(pattern):
                    _zip_file(z, file)

        important_root_files = [
            "database.db",
            "logistique.db",
            "settings.db",
            "requirements.txt",
            "pyproject.toml",
            "config.py",
            "main.py",
            "app.py",
            "streamlit_app.py",
            ".streamlit/config.toml",
        ]

        for name in important_root_files:
            _zip_file(z, PROJECT_DIR / name)

    return zip_path


def create_heavy_files_backup() -> Path:
    """
    Sauvegarde uniquement les fichiers lourds :
    images, PDF, documents, exports, uploads, photos.
    """
    zip_path = FILES_BACKUP_DIR / f"logistique_site_fichiers_lourds_{_timestamp()}.zip"

    folders = [
        DATA_DIR / "patrimoine_documents",
        DATA_DIR / "patrimoine_photos",
        DATA_DIR / "garage_photos",
        DATA_DIR / "garage_documents",
        DATA_DIR / "uploads",
        DATA_DIR / "exports",
        DATA_DIR / "article_images",
        DATA_DIR / "images",
        DATA_DIR / "documents",
        DATA_DIR / "photos",
        PROJECT_DIR / "assets" / "photos",
    ]

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for folder in folders:
            if folder.exists():
                _zip_dir(z, folder, str(folder.relative_to(PROJECT_DIR)))

        heavy_suffixes = [
            "*.pdf",
            "*.jpg",
            "*.jpeg",
            "*.png",
            "*.webp",
            "*.gif",
            "*.bmp",
            "*.doc",
            "*.docx",
            "*.xls",
            "*.xlsx",
            "*.ppt",
            "*.pptx",
            "*.csv",
        ]

        if DATA_DIR.exists():
            for suffix in heavy_suffixes:
                for file in DATA_DIR.glob(suffix):
                    _zip_file(z, file)

    return zip_path


def create_all_split_backups() -> tuple[Path, Path, Path]:
    code = create_code_light_backup()
    bases = create_databases_backup()
    files = create_heavy_files_backup()
    return code, bases, files


def list_backups() -> list[Path]:
    files: list[Path] = []

    for folder in [CODE_BACKUP_DIR, DB_BACKUP_DIR, FILES_BACKUP_DIR]:
        if folder.exists():
            files.extend(folder.glob("*.zip"))

    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def _backup_category(path: Path) -> str:
    if CODE_BACKUP_DIR in path.parents:
        return "Code"
    if DB_BACKUP_DIR in path.parents:
        return "Bases / configuration"
    if FILES_BACKUP_DIR in path.parents:
        return "Fichiers lourds"
    return "Autre"


def _safe_delete_backup(path: Path) -> bool:
    target = path.resolve()

    allowed_roots = [
        CODE_BACKUP_DIR.resolve(),
        DB_BACKUP_DIR.resolve(),
        FILES_BACKUP_DIR.resolve(),
    ]

    if not target.exists() or not target.is_file():
        return False

    if target.suffix.lower() != ".zip":
        return False

    if not any(str(target).startswith(str(root)) for root in allowed_roots):
        return False

    target.unlink()
    return True


def cleanup_old_backups(days: int = 60) -> int:
    limit = time.time() - days * 86400
    deleted = 0

    for file in list_backups():
        if file.stat().st_mtime < limit:
            if _safe_delete_backup(file):
                deleted += 1

    return deleted


def render_create() -> None:
    st.markdown("### 💾 Créer une sauvegarde globale")

    st.info(
        "La sauvegarde globale est séparée en trois parties pour éviter les gros ZIP : "
        "code, bases/configuration, fichiers lourds."
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("🧩 Sauvegarder CODE", width="stretch", key="patch69_backup_code"):
            try:
                path = create_code_light_backup()
                st.success(f"Code sauvegardé : {path.name} — {_file_size(path)}")
                _download_file(path, "📥 Télécharger le code")
            except Exception as exc:
                st.error(f"Erreur sauvegarde code : {exc}")

    with c2:
        if st.button("🗄️ Sauvegarder BASES / config", width="stretch", key="patch69_backup_bases"):
            try:
                path = create_databases_backup()
                st.success(f"Bases/config sauvegardées : {path.name} — {_file_size(path)}")
                _download_file(path, "📥 Télécharger bases/config")
            except Exception as exc:
                st.error(f"Erreur sauvegarde bases/config : {exc}")

    with c3:
        if st.button("📎 Sauvegarder FICHIERS lourds", width="stretch", key="patch69_backup_files"):
            try:
                path = create_heavy_files_backup()
                st.success(f"Fichiers lourds sauvegardés : {path.name} — {_file_size(path)}")
                _download_file(path, "📥 Télécharger fichiers lourds")
            except Exception as exc:
                st.error(f"Erreur sauvegarde fichiers : {exc}")

    st.divider()

    if st.button("🚀 Générer les 3 sauvegardes", width="stretch", key="patch69_backup_all"):
        try:
            code, bases, files = create_all_split_backups()

            st.success("Sauvegardes générées.")

            st.write(f"**Code :** `{code.name}` — {_file_size(code)}")
            _download_file(code, "📥 Télécharger code")

            st.write(f"**Bases/config :** `{bases.name}` — {_file_size(bases)}")
            _download_file(bases, "📥 Télécharger bases/config")

            st.write(f"**Fichiers lourds :** `{files.name}` — {_file_size(files)}")
            _download_file(files, "📥 Télécharger fichiers lourds")

        except Exception as exc:
            st.error(f"Erreur sauvegarde globale : {exc}")


def render_list_and_delete() -> None:
    st.markdown("### 📁 Sauvegardes disponibles")

    files = list_backups()

    if not files:
        st.info("Aucune sauvegarde globale disponible.")
        return

    rows = []

    for file in files:
        rows.append(
            {
                "catégorie": _backup_category(file),
                "fichier": file.name,
                "taille": _file_size(file),
                "date": datetime.fromtimestamp(file.stat().st_mtime).strftime("%d/%m/%Y %H:%M"),
                "chemin": str(file),
            }
        )

    st.dataframe(rows, width="stretch", hide_index=True)

    st.markdown("### 📥 Télécharger / supprimer")

    selected = st.selectbox(
        "Sélectionner une sauvegarde",
        [str(f) for f in files],
        format_func=lambda x: Path(x).name,
        key="patch69_selected_backup",
    )

    selected_path = Path(selected)

    c1, c2 = st.columns(2)

    with c1:
        st.write(f"**Fichier :** `{selected_path.name}`")
        st.write(f"**Catégorie :** `{_backup_category(selected_path)}`")
        st.write(f"**Taille :** `{_file_size(selected_path)}`")
        _download_file(selected_path, "📥 Télécharger la sauvegarde sélectionnée")

    with c2:
        st.warning("Suppression définitive de la sauvegarde sélectionnée.")

        confirm = st.checkbox(
            f"Confirmer la suppression de {selected_path.name}",
            key=f"patch69_confirm_delete_{selected_path.name}",
        )

        if st.button(
            "🗑️ Supprimer cette sauvegarde",
            disabled=not confirm,
            width="stretch",
            key=f"patch69_delete_{selected_path.name}",
        ):
            try:
                ok = _safe_delete_backup(selected_path)

                if ok:
                    st.success(f"Sauvegarde supprimée : {selected_path.name}")
                    st.rerun()
                else:
                    st.error("Suppression refusée ou fichier introuvable.")
            except Exception as exc:
                st.error(f"Erreur suppression : {exc}")


def render_diagnostic() -> None:
    st.markdown("### 🔍 Diagnostic espace disque")

    folders = [
        ("Projet complet", PROJECT_DIR),
        ("Data", DATA_DIR),
        ("Backups globaux", GLOBAL_BACKUP_DIR),
        ("Code light", CODE_BACKUP_DIR),
        ("Bases/config", DB_BACKUP_DIR),
        ("Fichiers lourds", FILES_BACKUP_DIR),
        ("Exports", DATA_DIR / "exports"),
        ("Patch backups", DATA_DIR / "patch_backups"),
        ("Patrimoine documents", DATA_DIR / "patrimoine_documents"),
        ("Patrimoine photos", DATA_DIR / "patrimoine_photos"),
        ("Assets photos", PROJECT_DIR / "assets" / "photos"),
        ("Uploads", DATA_DIR / "uploads"),
    ]

    rows = []

    for label, folder in folders:
        if not folder.exists():
            continue

        size, count = _folder_size(folder)

        rows.append(
            {
                "élément": label,
                "chemin": str(folder),
                "fichiers": count,
                "taille Mo": round(size / 1024 / 1024, 2),
            }
        )

    st.dataframe(rows, width="stretch", hide_index=True)


def render_cleanup() -> None:
    st.markdown("### 🧹 Nettoyage automatique")

    days = st.number_input(
        "Supprimer les sauvegardes globales plus anciennes que X jours",
        min_value=7,
        max_value=365,
        value=60,
        step=1,
    )

    st.warning("Ce nettoyage supprime uniquement les ZIP de sauvegarde globale.")

    confirm = st.checkbox("Je confirme le nettoyage automatique")

    if st.button(
        "🧹 Nettoyer les anciennes sauvegardes",
        disabled=not confirm,
        width="stretch",
        key="patch69_cleanup_old",
    ):
        deleted = cleanup_old_backups(int(days))
        st.success(f"{deleted} sauvegarde(s) supprimée(s).")


def render(show_title: bool = True) -> None:
    if show_title:  # PATCH73_TITLE_GUARDED
        st.markdown("### 💾 Sauvegarde globale du site")
    if show_title:  # PATCH73_TITLE_GUARDED
        st.caption("Sauvegarde séparée : code, bases/configuration, fichiers lourds.")

    tabs = st.tabs(
        [
            "💾 Créer",
            "📁 Gérer / supprimer",
            "🔍 Diagnostic",
            "🧹 Nettoyage",
        ]
    )

    with tabs[0]:
        render_create()

    with tabs[1]:
        render_list_and_delete()

    with tabs[2]:
        render_diagnostic()

    with tabs[3]:
        render_cleanup()


def show() -> None:
    render(show_title=True)



def render(show_title: bool = True) -> None:
    if show_title:
        st.markdown("### 💾 Sauvegarde globale du site")
        st.caption("Sauvegarde séparée : code, bases/configuration, fichiers lourds.")

    sections = {
        "💾 Créer": render_create,
        "📁 Gérer / supprimer": render_list_and_delete,
        "🔍 Diagnostic": render_diagnostic,
        "🧹 Nettoyage": render_cleanup,
    }

    selected = st.radio(
        "Section sauvegarde globale",
        list(sections.keys()),
        horizontal=True,
        label_visibility="collapsed",
        key="backup_global_site_section",
    )

    st.divider()

    sections[selected]()
