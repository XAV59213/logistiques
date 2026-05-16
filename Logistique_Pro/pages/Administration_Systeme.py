# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
import importlib
import importlib.util
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

try:
    from config import Config
except Exception:
    Config = None

try:
    from utils.database import get_connection
except Exception:
    get_connection = None

try:
    from utils.backups import create_backup, list_backups
except Exception:
    create_backup = None
    list_backups = None

try:
    from utils.system_manager import ensure_directories, maintenance_status
except Exception:
    ensure_directories = None
    maintenance_status = None


BASE_DIR = Path("/opt/logistique-pro")
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = DATA_DIR / "backups"

BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def format_size(size: int) -> str:
    if size < 1024:
        return f"{size} o"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} Ko"
    if size < 1024 * 1024 * 1024:
        return f"{size / 1024 / 1024:.1f} Mo"
    return f"{size / 1024 / 1024 / 1024:.2f} Go"


def _safe_download(path: Path, label: str, key_prefix: str) -> None:
    if not path.exists() or not path.is_file():
        st.warning("Fichier introuvable.")
        return

    mime = "application/zip" if path.suffix.lower() == ".zip" else "application/octet-stream"

    with open(path, "rb") as f:
        st.download_button(
            label,
            data=f.read(),
            file_name=path.name,
            mime=mime,
            width="stretch",
            key=f"{key_prefix}_{path.name}_{int(path.stat().st_mtime)}",
        )


def _render_external_page(page_filename: str, module_name: str) -> None:
    page_path = BASE_DIR / "pages" / page_filename

    if not page_path.exists():
        st.info(f"Page non disponible : `{page_filename}`")
        return

    try:
        spec = importlib.util.spec_from_file_location(module_name, page_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if hasattr(module, "show"):
            module.show()
        elif hasattr(module, "render"):
            module.render()
        else:
            st.warning(f"La page `{page_filename}` ne contient pas show() ou render().")

    except Exception as exc:
        st.error(f"Erreur chargement `{page_filename}` : {exc}")


def _render_module(module_name: str, missing_message: str) -> None:
    try:
        module = importlib.import_module(module_name)

        if hasattr(module, "render"):
            module.render()
        elif hasattr(module, "show"):
            module.show()
        else:
            st.error(f"Le module `{module_name}` ne contient pas render() ou show().")

    except Exception as exc:
        st.warning(f"{missing_message} : {exc}")


def should_exclude_full_backup(path: Path) -> bool:
    try:
        rel = path.relative_to(BASE_DIR)
    except Exception:
        return True

    excluded_dirs = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".cache",
        "node_modules",
    }

    excluded_roots = {
        "data/patch_backups",
        "data/backups/site_global",
    }

    if set(rel.parts) & excluded_dirs:
        return True

    rel_str = str(rel)

    if any(rel_str.startswith(root + "/") or rel_str == root for root in excluded_roots):
        return True

    if path.suffix.lower() in [".pyc", ".pyo", ".log"]:
        return True

    return False


def create_full_backup() -> Path:
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"site_backup_{now}.zip"

    with zipfile.ZipFile(backup_file, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(BASE_DIR):
            root_path = Path(root)

            dirs[:] = [
                d for d in dirs
                if not should_exclude_full_backup(root_path / d)
            ]

            for file in files:
                file_path = root_path / file

                if should_exclude_full_backup(file_path):
                    continue

                zipf.write(file_path, file_path.relative_to(BASE_DIR))

    return backup_file


def list_full_backups() -> list[Path]:
    roots = [
        BACKUP_DIR,
        BASE_DIR / "backups",
    ]

    files: list[Path] = []

    for root in roots:
        if root.exists():
            files.extend(root.glob("site_backup_*.zip"))
            files.extend(root.glob("logistique_pro_clean_backup_*.zip"))

    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def delete_backup_file(path: Path) -> bool:
    target = path.resolve()

    allowed_roots = [
        (BASE_DIR / "data" / "backups").resolve(),
        (BASE_DIR / "backups").resolve(),
    ]

    if not target.exists() or not target.is_file():
        return False

    if target.suffix.lower() != ".zip":
        return False

    if not any(str(target).startswith(str(root)) for root in allowed_roots):
        return False

    target.unlink()
    return True


def safe_extract(zip_path: Path, destination: Path) -> None:
    with zipfile.ZipFile(zip_path, "r") as zipf:
        for member in zipf.namelist():
            target = (destination / member).resolve()

            if not str(target).startswith(str(destination.resolve())):
                raise Exception("Archive non sécurisée.")

        zipf.extractall(destination)


def restore_full_backup(zip_path: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        safe_extract(zip_path, tmp_path)

        for item in tmp_path.iterdir():
            dest = BASE_DIR / item.name

            if item.name in [".git", ".venv", "venv"]:
                continue

            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)


def render_dossiers() -> None:
    st.markdown("### 📁 Vérification des dossiers")
    st.caption("Contrôle et création des dossiers nécessaires au bon fonctionnement du site.")

    required_dirs = [
        DATA_DIR,
        DATA_DIR / "backups",
        DATA_DIR / "exports",
        DATA_DIR / "patch_backups",
        BASE_DIR / "assets",
        BASE_DIR / "assets" / "photos",
        BASE_DIR / "pages",
        BASE_DIR / "utils",
        BASE_DIR / "administration_site",
    ]

    c1, c2 = st.columns([2, 1])

    with c1:
        for folder in required_dirs:
            if folder.exists():
                st.success(f"Présent : {folder}")
            else:
                st.error(f"Manquant : {folder}")

    with c2:
        if st.button("Vérifier / créer les dossiers", width="stretch", key="adminsys_create_dirs"):
            for folder in required_dirs:
                folder.mkdir(parents=True, exist_ok=True)

            if callable(ensure_directories):
                try:
                    ensure_directories()
                except Exception:
                    pass

            st.success("Dossiers vérifiés.")
            st.rerun()


def render_database() -> None:
    st.markdown("### 🗄️ Bases de données")
    st.caption("Contrôle des bases SQLite actives.")

    db_paths = []

    if Config is not None and hasattr(Config, "DB_PATH"):
        db_paths.append(Path(Config.DB_PATH))

    db_paths.extend(sorted(DATA_DIR.glob("*.db")) if DATA_DIR.exists() else [])
    db_paths.extend(sorted(BASE_DIR.glob("*.db")))

    unique_db_paths = []
    seen = set()

    for path in db_paths:
        if path not in seen:
            unique_db_paths.append(path)
            seen.add(path)

    if not unique_db_paths:
        st.info("Aucune base SQLite détectée.")
        return

    rows = []

    for db in unique_db_paths:
        rows.append(
            {
                "base": db.name,
                "chemin": str(db),
                "existe": "Oui" if db.exists() else "Non",
                "taille": format_size(db.stat().st_size) if db.exists() else "N/A",
            }
        )

    st.dataframe(rows, width="stretch", hide_index=True)

    st.divider()

    st.markdown("#### Statistiques base principale")

    if not callable(get_connection):
        st.info("Connexion base principale indisponible.")
        return

    try:
        conn = get_connection()
        cur = conn.cursor()

        tables = [
            "users",
            "articles",
            "notifications",
            "stock_items",
            "inventaire_items",
            "demandes",
            "messages",
            "vehicules",
            "fournisseurs",
        ]

        stats = {}

        for table in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cur.fetchone()[0]
            except Exception:
                stats[table] = 0

        conn.close()

        cols = st.columns(3)

        for index, table in enumerate(tables):
            cols[index % 3].metric(table, stats.get(table, 0))

    except Exception as exc:
        st.error(f"Erreur lecture statistiques : {exc}")


def render_maintenance() -> None:
    st.markdown("### 🚧 Entretien / maintenance")
    st.caption("État du mode maintenance et informations techniques.")

    if callable(maintenance_status):
        try:
            status = maintenance_status()

            if status.get("enabled"):
                st.warning(f"Maintenance active : {status.get('message', '')}")
            else:
                st.success("Mode maintenance désactivé.")

            with st.expander("Détails maintenance"):
                st.json(status)

        except Exception as exc:
            st.error(f"Erreur lecture maintenance : {exc}")
    else:
        st.info("Module maintenance indisponible.")

    st.divider()

    st.markdown("#### Commandes utiles")
    st.code("systemctl restart logistique.service", language="bash")
    st.code("systemctl status logistique.service --no-pager", language="bash")
    st.code("journalctl -u logistique.service -n 100 --no-pager", language="bash")


def render_sqlite_backups() -> None:
    st.markdown("### 💾 Sauvegardes SQLite")
    st.caption("Sauvegarde simple de la base principale.")

    if not callable(create_backup) or not callable(list_backups):
        st.info("Module de sauvegarde SQLite indisponible.")
        return

    if st.button("Créer une sauvegarde SQLite", width="stretch", key="adminsys_create_sqlite_backup"):
        success, message = create_backup()

        if success:
            st.success(f"Sauvegarde créée : {Path(message).name}")
            st.rerun()
        else:
            st.error(message)

    st.divider()

    backups = list_backups()

    if not backups:
        st.info("Aucune sauvegarde SQLite disponible.")
        return

    for backup_file in backups:
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])

            with c1:
                st.write(f"**{backup_file.name}**")
                st.caption(format_size(backup_file.stat().st_size))

            with c2:
                _safe_download(backup_file, "⬇️ Télécharger", "sqlite_backup")


def render_full_backups() -> None:
    st.markdown("### 🧰 Sauvegardes classiques")
    st.caption("Ancienne sauvegarde complète ZIP du site. À utiliser ponctuellement.")

    if st.button("📦 Créer une sauvegarde classique", width="stretch", key="adminsys_create_full_backup"):
        try:
            backup_file = create_full_backup()
            st.success(f"Sauvegarde créée : {backup_file.name}")
            st.rerun()
        except Exception as exc:
            st.error(f"Erreur création sauvegarde : {exc}")

    st.divider()

    uploaded_backup = st.file_uploader(
        "Importer une sauvegarde complète ZIP",
        type=["zip"],
        key="adminsys_upload_restore_zip",
    )

    if uploaded_backup is not None:
        st.warning("La restauration remplacera les fichiers existants présents dans l’archive.")

        confirm_upload_restore = st.checkbox(
            "Je confirme vouloir restaurer cette sauvegarde importée",
            key="adminsys_confirm_upload_restore",
        )

        if st.button(
            "♻️ Restaurer le ZIP importé",
            width="stretch",
            disabled=not confirm_upload_restore,
            key="adminsys_restore_uploaded_zip",
        ):
            try:
                temp_file = BACKUP_DIR / f"uploaded_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

                with open(temp_file, "wb") as f:
                    f.write(uploaded_backup.getbuffer())

                restore_full_backup(temp_file)
                st.success("Sauvegarde restaurée.")
                st.info("Redémarre ensuite : systemctl restart logistique.service")
            except Exception as exc:
                st.error(f"Erreur restauration : {exc}")

    st.divider()

    backups = list_full_backups()

    if not backups:
        st.info("Aucune sauvegarde classique disponible.")
        return

    selected = st.selectbox(
        "Sauvegarde classique",
        [str(p) for p in backups],
        format_func=lambda x: Path(x).name,
        key="adminsys_full_backup_select",
    )

    selected_path = Path(selected)

    c1, c2 = st.columns(2)

    with c1:
        st.write(f"**{selected_path.name}**")
        st.caption(format_size(selected_path.stat().st_size))
        _safe_download(selected_path, "⬇️ Télécharger", "full_backup")

    with c2:
        st.warning("Suppression définitive de la sauvegarde sélectionnée.")

        confirm_delete = st.checkbox(
            "Je confirme la suppression",
            key=f"adminsys_confirm_delete_full_{selected_path.name}",
        )

        if st.button(
            "🗑️ Supprimer cette sauvegarde",
            disabled=not confirm_delete,
            width="stretch",
            key=f"adminsys_delete_full_{selected_path.name}",
        ):
            if delete_backup_file(selected_path):
                st.success("Sauvegarde supprimée.")
                st.rerun()
            else:
                st.error("Suppression impossible.")


def render_global_backup() -> None:
    st.markdown("### 💾 Sauvegarde globale séparée")
    st.caption("Sauvegarde professionnelle : code, bases/configuration et fichiers lourds séparés.")

    try:
        module = importlib.import_module("administration_site.backup_global_site")
        if hasattr(module, "render"):
            module.render(show_title=False)
        elif hasattr(module, "show"):
            module.show()
        else:
            st.error("Le module sauvegarde globale ne contient pas render() ou show().")
    except Exception as exc:
        st.warning(f"Module sauvegarde globale indisponible : {exc}")



def render_cleaning() -> None:
    st.markdown("### 🧹 Nettoyage sécurisé")
    st.caption("Nettoyage des caches, anciens scripts, exports et sauvegardes obsolètes.")

    try:
        module = importlib.import_module("administration_site.nettoyage_site")
        if hasattr(module, "render"):
            module.render(show_title=False)
        elif hasattr(module, "show"):
            module.show()
        else:
            st.error("Le module nettoyage site ne contient pas render() ou show().")
    except Exception as exc:
        st.warning(f"Module nettoyage site indisponible : {exc}")



def render_journal() -> None:
    st.markdown("### 📜 Journal d’activité")
    _render_external_page("Journal_Activite.py", "journal_activite_admin_system")


def render_exports_backups() -> None:
    st.markdown("### 📦 Exports & Backups")
    _render_external_page("Exports_Backups.py", "exports_backups_admin_system")


def render_help() -> None:
    st.markdown("### ℹ️ Aide Administration Système")

    st.info(
        "Cette page est maintenant organisée en sections propres : "
        "dossiers, bases, maintenance, sauvegardes, nettoyage, journal et exports."
    )

    st.markdown(
        """
        **Organisation recommandée :**

        - **Sauvegardes SQLite** : sauvegarde rapide de la base principale.
        - **Sauvegardes classiques** : ancien ZIP complet, à utiliser rarement.
        - **Sauvegarde globale séparée** : méthode recommandée, avec code / bases / fichiers lourds séparés.
        - **Nettoyage sécurisé** : suppression des caches, vieux scripts et anciens backups.
        """
    )

    st.divider()

    st.markdown("#### Commandes utiles")
    st.code("systemctl restart logistique.service", language="bash")
    st.code("systemctl status logistique.service --no-pager", language="bash")
    st.code("journalctl -u logistique.service -n 100 --no-pager", language="bash")


def show() -> None:
    st.title("🛠️ Administration Système")
    st.caption("Outils techniques, maintenance, sauvegardes et diagnostic.")

    user = st.session_state.get("user")

    if not user or str(user.get("role", "")).lower() != "admin":
        st.error("Accès réservé aux administrateurs.")
        st.stop()

    tabs = st.tabs(
        [
            "📁 Dossiers",
            "🗄️ Bases",
            "🚧 Entretien",
            "💾 SQLite",
            "🧰 Classiques",
            "💾 Globale séparée",
            "🧹 Nettoyage",
            "📜 Journal",
            "📦 Exports",
            "ℹ️ Aide",
        ]
    )

    with tabs[0]:
        render_dossiers()

    with tabs[1]:
        render_database()

    with tabs[2]:
        render_maintenance()

    with tabs[3]:
        render_sqlite_backups()

    with tabs[4]:
        render_full_backups()

    with tabs[5]:
        render_global_backup()

    with tabs[6]:
        render_cleaning()

    with tabs[7]:
        render_journal()

    with tabs[8]:
        render_exports_backups()

    with tabs[9]:
        render_help()


if __name__ == "__main__":
    show()



def show() -> None:
    st.title("🛠️ Administration Système")
    st.caption("Outils techniques, maintenance, sauvegardes et diagnostic.")

    user = st.session_state.get("user")

    if not user or str(user.get("role", "")).lower() != "admin":
        st.error("Accès réservé aux administrateurs.")
        st.stop()

    modules = {
        "📁 Dossiers": render_dossiers,
        "🗄️ Bases": render_database,
        "🚧 Entretien": render_maintenance,
        "💾 SQLite": render_sqlite_backups,
        "🧰 Classiques": render_full_backups,
        "💾 Globale séparée": render_global_backup,
        "🧹 Nettoyage": render_cleaning,
        "📜 Journal": render_journal,
        "📦 Exports": render_exports_backups,
        "ℹ️ Aide": render_help,
    }

    selected = st.radio(
        "Section Administration Système",
        list(modules.keys()),
        horizontal=True,
        label_visibility="collapsed",
        key="admin_systeme_section",
    )

    st.divider()

    try:
        modules[selected]()
    except Exception as exc:
        st.error(f"Erreur pendant le chargement de la section `{selected}` : {exc}")
