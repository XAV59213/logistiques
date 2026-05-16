# -*- coding: utf-8 -*-
from __future__ import annotations

import shutil
import zipfile
from datetime import datetime
from pathlib import Path

import streamlit as st

from .db import get_db_path


PROJECT_DIR = Path("/opt/logistique-pro")
DATA_DIR = PROJECT_DIR / "data"

PHOTOS_DIR = DATA_DIR / "patrimoine_photos"
DOCUMENTS_DIR = DATA_DIR / "patrimoine_documents"

BACKUP_DIR = DATA_DIR / "backups" / "patrimoine"
BACKUP_CODE_DIR = DATA_DIR / "backups" / "code_light"
BACKUP_FILES_DIR = DATA_DIR / "backups" / "fichiers_lourds"

EXPORT_DIR = DATA_DIR / "exports" / "patrimoine"

for d in [BACKUP_DIR, BACKUP_CODE_DIR, BACKUP_FILES_DIR, EXPORT_DIR, PHOTOS_DIR, DOCUMENTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _db_path() -> Path:
    return Path(get_db_path())


def _zip_write_if_exists(z: zipfile.ZipFile, path: Path, arcname: str | None = None) -> None:
    if path.exists() and path.is_file():
        z.write(path, arcname=arcname or str(path.relative_to(PROJECT_DIR)))


def _zip_dir(z: zipfile.ZipFile, folder: Path, arc_prefix: str) -> None:
    if not folder.exists():
        return

    for file in folder.rglob("*"):
        if file.is_file():
            z.write(file, arcname=f"{arc_prefix}/{file.relative_to(folder)}")


def create_db_backup() -> Path:
    src = _db_path()

    if not src.exists():
        raise FileNotFoundError(f"Base introuvable : {src}")

    dest = BACKUP_DIR / f"patrimoine_bati_db_{_timestamp()}.db"
    shutil.copy2(src, dest)
    return dest


def create_code_light_backup() -> Path:
    """
    Sauvegarde légère du code du site.
    Exclut tous les fichiers lourds : images, PDF, documents, exports, backups, venv, caches.
    """
    zip_path = BACKUP_CODE_DIR / f"logistique_code_light_{_timestamp()}.zip"

    excluded_dirs = {
        ".venv",
        "venv",
        "__pycache__",
        ".git",
        "node_modules",
    }

    excluded_data_roots = {
        "data/backups",
        "data/patch_backups",
        "data/exports",
        "data/patrimoine_documents",
        "data/patrimoine_photos",
        "data/uploads",
        "data/tmp",
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
    }

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for file in PROJECT_DIR.rglob("*"):
            if not file.is_file():
                continue

            rel = file.relative_to(PROJECT_DIR)
            rel_str = str(rel)

            parts = set(rel.parts)

            if parts & excluded_dirs:
                continue

            if any(rel_str.startswith(root + "/") or rel_str == root for root in excluded_data_roots):
                continue

            if file.suffix.lower() in excluded_suffixes:
                continue

            z.write(file, arcname=rel_str)

    return zip_path


def create_site_config_backup() -> Path:
    """
    Sauvegarde des bases et paramètres importants, sans fichiers lourds.
    """
    zip_path = BACKUP_CODE_DIR / f"logistique_config_bases_{_timestamp()}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        # Bases utiles
        for db in DATA_DIR.glob("*.db"):
            _zip_write_if_exists(z, db)

        # Configs texte/json/yaml éventuelles
        for pattern in ["*.txt", "*.json", "*.yaml", "*.yml", "*.toml", "*.ini"]:
            for file in DATA_DIR.glob(pattern):
                _zip_write_if_exists(z, file)

        # Fichiers projet importants
        for name in [
            "requirements.txt",
            "pyproject.toml",
            "config.py",
            "main.py",
            "app.py",
            "streamlit_app.py",
        ]:
            _zip_write_if_exists(z, PROJECT_DIR / name)

    return zip_path


def create_heavy_files_backup() -> Path:
    """
    Sauvegarde séparée des fichiers lourds du site :
    photos, PDF, documents, exports, uploads.
    """
    zip_path = BACKUP_FILES_DIR / f"logistique_fichiers_lourds_{_timestamp()}.zip"

    folders = [
        (DATA_DIR / "patrimoine_documents", "data/patrimoine_documents"),
        (DATA_DIR / "patrimoine_photos", "data/patrimoine_photos"),
        (DATA_DIR / "uploads", "data/uploads"),
        (DATA_DIR / "exports", "data/exports"),
    ]

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for folder, prefix in folders:
            _zip_dir(z, folder, prefix)

        # Images / PDF isolés dans data
        for suffix in ["*.pdf", "*.jpg", "*.jpeg", "*.png", "*.webp", "*.doc", "*.docx", "*.xls", "*.xlsx"]:
            for file in DATA_DIR.glob(suffix):
                _zip_write_if_exists(z, file)

    return zip_path


def create_full_split_backups() -> tuple[Path, Path, Path]:
    """
    Produit 3 fichiers séparés :
    - code léger
    - bases / config
    - fichiers lourds
    """
    code = create_code_light_backup()
    config = create_site_config_backup()
    files = create_heavy_files_backup()
    return code, config, files


def list_backups() -> list[Path]:
    files = []

    for folder in [BACKUP_DIR, BACKUP_CODE_DIR, BACKUP_FILES_DIR]:
        if folder.exists():
            for pattern in ["*.db", "*.zip"]:
                files.extend(folder.glob(pattern))

    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def restore_db_from_uploaded(uploaded_file) -> Path:
    if uploaded_file is None:
        raise ValueError("Aucun fichier fourni.")

    if not uploaded_file.name.lower().endswith(".db"):
        raise ValueError("Le fichier doit être une base .db.")

    current = _db_path()

    if current.exists():
        safety = BACKUP_DIR / f"patrimoine_bati_before_restore_{_timestamp()}.db"
        shutil.copy2(current, safety)

    with open(current, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return current


def restore_from_existing_db(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(path)

    if path.suffix.lower() != ".db":
        raise ValueError("La restauration directe accepte uniquement les fichiers .db.")

    current = _db_path()

    if current.exists():
        safety = BACKUP_DIR / f"patrimoine_bati_before_restore_{_timestamp()}.db"
        shutil.copy2(current, safety)

    shutil.copy2(path, current)
    return current


def _download_file(path: Path, label: str):
    with open(path, "rb") as f:
        mime = "application/zip" if path.suffix.lower() == ".zip" else "application/octet-stream"

        st.download_button(
            label,
            data=f.read(),
            file_name=path.name,
            mime=mime,
            width="stretch",
            key=f"download_backup_{path.name}_{int(path.stat().st_mtime)}",
        )


def _file_size(path: Path) -> str:
    size = path.stat().st_size

    if size < 1024:
        return f"{size} o"

    if size < 1024 * 1024:
        return f"{size / 1024:.1f} Ko"

    if size < 1024 * 1024 * 1024:
        return f"{size / 1024 / 1024:.1f} Mo"

    return f"{size / 1024 / 1024 / 1024:.1f} Go"


def render_sauvegarde() -> None:
    st.markdown("### 💾 Sauvegardes séparées")

    st.info(
        "Les sauvegardes sont maintenant séparées pour éviter les ZIP trop volumineux : "
        "code léger, bases/configuration, fichiers lourds."
    )

    st.write(f"**Base patrimoine actuelle :** `{_db_path()}`")
    st.write(f"**Dossier sauvegardes code :** `{BACKUP_CODE_DIR}`")
    st.write(f"**Dossier sauvegardes fichiers lourds :** `{BACKUP_FILES_DIR}`")

    st.divider()

    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("💾 Sauvegarder DB patrimoine", width="stretch", key="btn_backup_db_patrimoine"):
            try:
                path = create_db_backup()
                st.success(f"Sauvegarde créée : {path.name} — {_file_size(path)}")
                _download_file(path, "📥 Télécharger la DB patrimoine")
            except Exception as exc:
                st.error(f"Erreur sauvegarde DB : {exc}")

    with c2:
        if st.button("🧩 Sauvegarder CODE léger", width="stretch", key="btn_backup_code_light"):
            try:
                path = create_code_light_backup()
                st.success(f"Code sauvegardé : {path.name} — {_file_size(path)}")
                _download_file(path, "📥 Télécharger le code léger")
            except Exception as exc:
                st.error(f"Erreur sauvegarde code : {exc}")

    with c3:
        if st.button("🗄️ Sauvegarder bases/config", width="stretch", key="btn_backup_config_bases"):
            try:
                path = create_site_config_backup()
                st.success(f"Bases/config sauvegardées : {path.name} — {_file_size(path)}")
                _download_file(path, "📥 Télécharger bases/config")
            except Exception as exc:
                st.error(f"Erreur sauvegarde config : {exc}")

    st.divider()

    st.markdown("### 📎 Sauvegarde des fichiers lourds")

    st.warning(
        "Cette sauvegarde contient les images, PDF, documents, exports et uploads. "
        "Elle peut être volumineuse. À faire moins souvent."
    )

    if st.button("📦 Sauvegarder fichiers lourds séparément", width="stretch", key="btn_backup_heavy_files"):
        try:
            path = create_heavy_files_backup()
            st.success(f"Fichiers lourds sauvegardés : {path.name} — {_file_size(path)}")
            _download_file(path, "📥 Télécharger les fichiers lourds")
        except Exception as exc:
            st.error(f"Erreur sauvegarde fichiers lourds : {exc}")

    st.divider()

    st.markdown("### 🚀 Pack complet séparé")

    st.caption("Génère 3 fichiers distincts : code léger + bases/config + fichiers lourds.")

    if st.button("🚀 Générer les 3 sauvegardes séparées", width="stretch", key="btn_backup_split_all"):
        try:
            code, config, files = create_full_split_backups()

            st.success("Sauvegardes séparées générées.")

            st.write(f"**Code :** `{code.name}` — {_file_size(code)}")
            _download_file(code, "📥 Télécharger code léger")

            st.write(f"**Bases/config :** `{config.name}` — {_file_size(config)}")
            _download_file(config, "📥 Télécharger bases/config")

            st.write(f"**Fichiers lourds :** `{files.name}` — {_file_size(files)}")
            _download_file(files, "📥 Télécharger fichiers lourds")

        except Exception as exc:
            st.error(f"Erreur génération sauvegardes séparées : {exc}")


def render_liste() -> None:
    st.markdown("### 📁 Sauvegardes disponibles")

    files = list_backups()

    if not files:
        st.info("Aucune sauvegarde disponible.")
        return

    rows = []

    for file in files:
        if BACKUP_CODE_DIR in file.parents:
            categorie = "Code / bases"
        elif BACKUP_FILES_DIR in file.parents:
            categorie = "Fichiers lourds"
        else:
            categorie = "Patrimoine DB"

        rows.append(
            {
                "catégorie": categorie,
                "fichier": file.name,
                "type": file.suffix.lower(),
                "taille": _file_size(file),
                "date": datetime.fromtimestamp(file.stat().st_mtime).strftime("%d/%m/%Y %H:%M"),
                "chemin": str(file),
            }
        )

    st.dataframe(rows, width="stretch", hide_index=True)

    selected = st.selectbox("Sélectionner une sauvegarde", [file.name for file in files])
    selected_path = next((f for f in files if f.name == selected), None)

    if selected_path:
        _download_file(selected_path, "📥 Télécharger la sauvegarde sélectionnée")


def render_restauration_upload() -> None:
    st.markdown("### ♻️ Restaurer depuis un fichier uploadé")

    st.warning(
        "La restauration remplace uniquement la base patrimoine actuelle. "
        "Une sauvegarde automatique est faite juste avant restauration."
    )

    uploaded = st.file_uploader(
        "Fichier patrimoine_bati.db",
        type=["db"],
        key="patrimoine_restore_upload",
    )

    confirm = st.checkbox("Je confirme vouloir restaurer cette base uploadée")

    if st.button("♻️ Restaurer la base uploadée", disabled=not confirm, width="stretch", key="btn_restore_upload_db"):
        try:
            restored = restore_db_from_uploaded(uploaded)
            st.success(f"Base restaurée : {restored}")
            st.info("Redémarre le service puis recharge la page.")
        except Exception as exc:
            st.error(f"Erreur restauration : {exc}")


def render_restauration_existante() -> None:
    st.markdown("### ♻️ Restaurer depuis une sauvegarde existante")

    db_files = [file for file in list_backups() if file.suffix.lower() == ".db"]

    if not db_files:
        st.info("Aucune sauvegarde .db disponible.")
        return

    selected = st.selectbox("Sauvegarde DB", [file.name for file in db_files])
    selected_path = next((f for f in db_files if f.name == selected), None)

    st.write(f"Fichier sélectionné : `{selected_path}`")

    confirm = st.checkbox("Je confirme restaurer cette sauvegarde DB existante")

    if st.button("♻️ Restaurer cette sauvegarde", disabled=not confirm, width="stretch", key="btn_restore_existing_db"):
        try:
            restored = restore_from_existing_db(selected_path)
            st.success(f"Base restaurée : {restored}")
            st.info("Redémarre le service puis recharge la page.")
        except Exception as exc:
            st.error(f"Erreur restauration : {exc}")


def render_diagnostic() -> None:
    st.markdown("### 🔍 Diagnostic sauvegardes")

    st.write(f"**Base actuelle :** `{_db_path()}`")
    st.write(f"**Base existe :** `{_db_path().exists()}`")

    if _db_path().exists():
        st.write(f"**Taille DB :** `{_file_size(_db_path())}`")

    st.write(f"**Sauvegardes patrimoine :** `{BACKUP_DIR}`")
    st.write(f"**Sauvegardes code :** `{BACKUP_CODE_DIR}`")
    st.write(f"**Sauvegardes fichiers lourds :** `{BACKUP_FILES_DIR}`")

    photos = [p for p in PHOTOS_DIR.rglob("*") if p.is_file()] if PHOTOS_DIR.exists() else []
    documents = [p for p in DOCUMENTS_DIR.rglob("*") if p.is_file()] if DOCUMENTS_DIR.exists() else []

    st.write(f"**Photos patrimoine :** `{len(photos)}` fichier(s)")
    st.write(f"**Documents patrimoine :** `{len(documents)}` fichier(s)")

    folders = [
        DATA_DIR / "patrimoine_documents",
        DATA_DIR / "patrimoine_photos",
        DATA_DIR / "exports",
        DATA_DIR / "backups",
        DATA_DIR / "patch_backups",
    ]

    rows = []

    for folder in folders:
        if not folder.exists():
            continue

        size = sum(p.stat().st_size for p in folder.rglob("*") if p.is_file())
        rows.append(
            {
                "dossier": str(folder),
                "taille Mo": round(size / 1024 / 1024, 2),
                "fichiers": len([p for p in folder.rglob("*") if p.is_file()]),
            }
        )

    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)


def render() -> None:
    st.markdown("### 💾 Sauvegarde / restauration Patrimoine")
    st.caption("Sauvegardes séparées : code léger, bases/configuration et fichiers lourds.")

    tabs = st.tabs(
        [
            "💾 Sauvegarder",
            "📁 Sauvegardes",
            "♻️ Restaurer upload",
            "♻️ Restaurer existante",
            "🔍 Diagnostic",
        ]
    )

    with tabs[0]:
        render_sauvegarde()

    with tabs[1]:
        render_liste()

    with tabs[2]:
        render_restauration_upload()

    with tabs[3]:
        render_restauration_existante()

    with tabs[4]:
        render_diagnostic()


def show() -> None:
    render()
