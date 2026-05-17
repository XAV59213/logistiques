# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import streamlit as st

from administration_systeme.common import APP_DIR, BACKUP_DIR, create_project_backup, fmt_size


MAX_DOWNLOAD_SIZE = 200 * 1024 * 1024  # 200 Mo


def is_safe_zip(zip_path: Path) -> tuple[bool, str]:
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            for member in z.infolist():
                name = member.filename

                if name.startswith("/") or name.startswith("\\"):
                    return False, f"Chemin absolu interdit : {name}"

                target = (APP_DIR / name).resolve()

                if not str(target).startswith(str(APP_DIR.resolve())):
                    return False, f"Chemin dangereux détecté : {name}"

        return True, "Archive valide."

    except zipfile.BadZipFile:
        return False, "Le fichier n'est pas une archive ZIP valide."
    except Exception as exc:
        return False, str(exc)


def safe_extract_zip(zip_path: Path, destination: Path) -> None:
    ok, msg = is_safe_zip(zip_path)

    if not ok:
        raise RuntimeError(msg)

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(destination)


def make_pre_restore_backup() -> Path:
    return create_project_backup()


def restore_backup(zip_path: Path) -> None:
    """
    Restaure une sauvegarde ZIP dans APP_DIR.
    Exclusions de sécurité :
    - .git
    - .venv / venv
    - __pycache__
    - data/backups
    - data/patch_backups
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        safe_extract_zip(zip_path, tmp_dir)

        for item in tmp_dir.iterdir():
            if item.name in {".git", ".venv", "venv", "__pycache__"}:
                continue

            if item.name == "data":
                src_data = item
                dst_data = APP_DIR / "data"

                for sub in src_data.iterdir():
                    if sub.name in {"backups", "patch_backups"}:
                        continue

                    dst = dst_data / sub.name

                    if sub.is_dir():
                        shutil.copytree(sub, dst, dirs_exist_ok=True)
                    else:
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(sub, dst)

                continue

            dst = APP_DIR / item.name

            if item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dst)


def delete_backup(path: Path) -> bool:
    path = path.resolve()
    allowed_root = BACKUP_DIR.resolve()

    if not str(path).startswith(str(allowed_root)):
        return False

    if not path.exists() or not path.is_file():
        return False

    if path.suffix.lower() != ".zip":
        return False

    path.unlink()
    return True


def save_uploaded_backup(uploaded_file) -> Path:
    filename = Path(uploaded_file.name).name

    if not filename.lower().endswith(".zip"):
        raise RuntimeError("Seuls les fichiers .zip sont acceptés.")

    target = BACKUP_DIR / f"uploaded_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"

    with open(target, "wb") as f:
        f.write(uploaded_file.getbuffer())

    ok, msg = is_safe_zip(target)

    if not ok:
        target.unlink(missing_ok=True)
        raise RuntimeError(msg)

    return target


def render_upload_restore():
    st.markdown("## Importer une sauvegarde ZIP")

    uploaded = st.file_uploader(
        "Uploader une sauvegarde ZIP",
        type=["zip"],
        key="admin_backup_upload_zip",
    )

    if uploaded is None:
        return

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Importer seulement", width="stretch", key="admin_backup_upload_only"):
            try:
                saved = save_uploaded_backup(uploaded)
                st.success(f"Sauvegarde importée : {saved.name}")
            except Exception as exc:
                st.error(f"Erreur import : {exc}")

    with col2:
        confirm = st.checkbox(
            "Je confirme vouloir restaurer le ZIP uploadé",
            key="admin_backup_confirm_restore_uploaded",
        )

        if st.button(
            "Importer et restaurer",
            type="primary",
            disabled=not confirm,
            width="stretch",
            key="admin_backup_upload_and_restore",
        ):
            try:
                saved = save_uploaded_backup(uploaded)

                st.info("Création d'une sauvegarde de sécurité avant restauration...")
                pre = make_pre_restore_backup()
                st.success(f"Sauvegarde avant restauration créée : {pre.name}")

                restore_backup(saved)

                st.success("Restauration terminée.")
                st.warning("Redémarre le service pour charger les fichiers restaurés.")
                st.code("systemctl restart logistique.service", language="bash")

            except Exception as exc:
                st.error(f"Erreur restauration : {exc}")


def render_existing_backups():
    st.markdown("## Dernières sauvegardes ZIP")

    backups = sorted(BACKUP_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not backups:
        st.info("Aucune sauvegarde ZIP disponible.")
        return

    for backup in backups[:20]:
        size = backup.stat().st_size
        safe_name = backup.name.replace(".", "_").replace("-", "_")

        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])

            with c1:
                st.write(f"**{backup.name}**")
                st.caption(f"{fmt_size(size)} — {backup}")

            with c2:
                if size <= MAX_DOWNLOAD_SIZE:
                    with open(backup, "rb") as f:
                        st.download_button(
                            "Télécharger",
                            data=f.read(),
                            file_name=backup.name,
                            mime="application/zip",
                            key=f"download_backup_{safe_name}",
                            width="stretch",
                        )
                else:
                    st.warning("Trop volumineux")
                    st.code(f"scp root@SERVEUR:{backup} .", language="bash")

            with c3:
                restore_confirm = st.checkbox(
                    "Confirmer",
                    key=f"confirm_restore_{safe_name}",
                )

                if st.button(
                    "Restaurer",
                    disabled=not restore_confirm,
                    type="primary",
                    key=f"restore_backup_{safe_name}",
                    width="stretch",
                ):
                    try:
                        ok, msg = is_safe_zip(backup)

                        if not ok:
                            st.error(msg)
                            return

                        st.info("Création d'une sauvegarde de sécurité avant restauration...")
                        pre = make_pre_restore_backup()
                        st.success(f"Sauvegarde avant restauration créée : {pre.name}")

                        restore_backup(backup)

                        st.success("Restauration terminée.")
                        st.warning("Redémarre le service pour charger les fichiers restaurés.")
                        st.code("systemctl restart logistique.service", language="bash")

                    except Exception as exc:
                        st.error(f"Erreur restauration : {exc}")

            with c4:
                delete_confirm = st.checkbox(
                    "Confirmer",
                    key=f"confirm_delete_{safe_name}",
                )

                if st.button(
                    "Supprimer",
                    disabled=not delete_confirm,
                    key=f"delete_backup_{safe_name}",
                    width="stretch",
                ):
                    try:
                        if delete_backup(backup):
                            st.success("Sauvegarde supprimée.")
                            st.rerun()
                        else:
                            st.error("Suppression refusée.")
                    except Exception as exc:
                        st.error(f"Erreur suppression : {exc}")


def render():
    st.subheader("Sauvegardes du site")

    st.info(
        "La sauvegarde exclut `.git`, `.venv`, les caches Python et les anciennes sauvegardes. "
        "Avant chaque restauration, une sauvegarde de sécurité est créée automatiquement."
    )

    if st.button("Créer une sauvegarde ZIP", type="primary", width="stretch", key="backup_create_zip_mod"):
        try:
            backup = create_project_backup()
            st.success(f"Sauvegarde créée : {backup.name}")
            st.rerun()
        except Exception as exc:
            st.error(f"Erreur sauvegarde : {exc}")

    st.divider()

    render_upload_restore()

    st.divider()

    render_existing_backups()
