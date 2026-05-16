# -*- coding: utf-8 -*-
from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


PROJECT_DIR = Path("/opt/logistique-pro")
DATA_DIR = PROJECT_DIR / "data"

SAFE_DELETE_ROOTS = [
    PROJECT_DIR,
    DATA_DIR / "exports",
    DATA_DIR / "patch_backups",
    DATA_DIR / "backups",
    PROJECT_DIR / "backups",
]


def _file_size(size: int) -> str:
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


def _is_safe_path(path: Path) -> bool:
    try:
        resolved = path.resolve()
    except Exception:
        return False

    allowed = [p.resolve() for p in SAFE_DELETE_ROOTS if p.exists()]

    return any(str(resolved).startswith(str(root)) for root in allowed)


def _scan_pycache() -> list[Path]:
    results = []

    for folder in PROJECT_DIR.rglob("__pycache__"):
        if folder.is_dir():
            results.append(folder)

    return results


def _scan_pyc() -> list[Path]:
    return [p for p in PROJECT_DIR.rglob("*.pyc") if p.is_file()]


def _scan_patch_scripts() -> list[Path]:
    roots = [Path("/root"), PROJECT_DIR]
    results = []

    patterns = [
        "*patch*.sh",
        "*Patch*.sh",
        "*PATCH*.sh",
        "[0-9][0-9]_*.sh",
        "[0-9][0-9][a-z]_*.sh",
        "[0-9][0-9][A-Z]_*.sh",
    ]

    for root in roots:
        if not root.exists():
            continue

        for pattern in patterns:
            results.extend([p for p in root.glob(pattern) if p.is_file()])

    return sorted(set(results))


def _scan_bak_files() -> list[Path]:
    results = []

    for pattern in ["*.bak", "*.backup", "*.old", "*.disabled_patch*"]:
        results.extend([p for p in PROJECT_DIR.rglob(pattern) if p.is_file()])

    return sorted(set(results))


def _scan_old_files(folder: Path, days: int, suffixes: list[str] | None = None) -> list[Path]:
    if not folder.exists():
        return []

    limit = time.time() - days * 86400
    results = []

    for file in folder.rglob("*"):
        if not file.is_file():
            continue

        if suffixes and file.suffix.lower() not in suffixes:
            continue

        try:
            if file.stat().st_mtime < limit:
                results.append(file)
        except Exception:
            pass

    return results


def _delete_file(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False

    if not _is_safe_path(path):
        return False

    # Protection bases actives à la racine de data
    if path.parent == DATA_DIR and path.suffix.lower() in [".db", ".sqlite", ".sqlite3"]:
        return False

    try:
        path.unlink()
        return True
    except Exception:
        return False


def _delete_folder(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False

    if path.name != "__pycache__":
        return False

    if not _is_safe_path(path):
        return False

    try:
        import shutil
        shutil.rmtree(path)
        return True
    except Exception:
        return False


def build_scan(days_exports: int = 30, days_backups: int = 30, days_patch_backups: int = 30) -> dict[str, list[Path]]:
    return {
        "__pycache__": _scan_pycache(),
        ".pyc": _scan_pyc(),
        "scripts_patch": _scan_patch_scripts(),
        "fichiers_bak": _scan_bak_files(),
        "exports_anciens": _scan_old_files(DATA_DIR / "exports", days_exports),
        "backups_anciens": _scan_old_files(DATA_DIR / "backups", days_backups, [".zip", ".db", ".tgz", ".gz"]),
        "patch_backups_anciens": _scan_old_files(DATA_DIR / "patch_backups", days_patch_backups),
    }


def scan_to_dataframe(scan: dict[str, list[Path]]) -> pd.DataFrame:
    rows = []

    for category, paths in scan.items():
        for path in paths:
            try:
                size = path.stat().st_size if path.is_file() else _folder_size(path)[0]
                date = datetime.fromtimestamp(path.stat().st_mtime).strftime("%d/%m/%Y %H:%M")
            except Exception:
                size = 0
                date = ""

            rows.append(
                {
                    "catégorie": category,
                    "nom": path.name,
                    "chemin": str(path),
                    "taille": _file_size(size),
                    "taille_octets": size,
                    "date": date,
                }
            )

    return pd.DataFrame(rows)


def run_cleanup(scan: dict[str, list[Path]], selected_categories: list[str]) -> dict[str, Any]:
    deleted = 0
    refused = 0
    total_size = 0

    for category in selected_categories:
        for path in scan.get(category, []):
            try:
                size = path.stat().st_size if path.is_file() else _folder_size(path)[0]
            except Exception:
                size = 0

            ok = False

            if path.is_dir():
                ok = _delete_folder(path)
            elif path.is_file():
                ok = _delete_file(path)

            if ok:
                deleted += 1
                total_size += size
            else:
                refused += 1

    return {
        "supprimés": deleted,
        "refusés": refused,
        "espace_libéré": _file_size(total_size),
        "octets_libérés": total_size,
    }


def render_scan() -> None:
    st.markdown("### 🔍 Scanner les fichiers nettoyables")

    c1, c2, c3 = st.columns(3)

    with c1:
        days_exports = st.number_input("Exports plus anciens que X jours", min_value=1, max_value=365, value=30)

    with c2:
        days_backups = st.number_input("Backups plus anciens que X jours", min_value=1, max_value=365, value=30)

    with c3:
        days_patch = st.number_input("Patch backups plus anciens que X jours", min_value=1, max_value=365, value=30)

    scan = build_scan(int(days_exports), int(days_backups), int(days_patch))
    df = scan_to_dataframe(scan)

    if df.empty:
        st.success("Aucun fichier nettoyable détecté.")
        return

    st.warning(f"{len(df)} élément(s) nettoyable(s) détecté(s).")

    total = int(df["taille_octets"].sum())
    st.metric("Espace potentiel", _file_size(total))

    st.dataframe(
        df.drop(columns=["taille_octets"]),
        width="stretch",
        hide_index=True,
    )

    st.download_button(
        "📥 Export CSV du scan",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"scan_nettoyage_site_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        width="stretch",
        key="download_scan_nettoyage_site",
    )


def render_cleanup() -> None:
    st.markdown("### 🧹 Nettoyage sécurisé")

    st.info("Les bases actives dans `/opt/logistique-pro/data/*.db` sont protégées.")

    days_exports = st.number_input("Exports anciens : jours", min_value=1, max_value=365, value=30, key="clean_exports_days")
    days_backups = st.number_input("Backups anciens : jours", min_value=1, max_value=365, value=30, key="clean_backups_days")
    days_patch = st.number_input("Patch backups anciens : jours", min_value=1, max_value=365, value=30, key="clean_patch_days")

    scan = build_scan(int(days_exports), int(days_backups), int(days_patch))

    categories = {
        "__pycache__": "Dossiers __pycache__",
        ".pyc": "Fichiers .pyc",
        "scripts_patch": "Scripts de patch .sh",
        "fichiers_bak": "Fichiers .bak / .old / disabled_patch",
        "exports_anciens": "Exports anciens",
        "backups_anciens": "Backups anciens",
        "patch_backups_anciens": "Patch backups anciens",
    }

    selected = []

    for key, label in categories.items():
        count = len(scan.get(key, []))
        checked = st.checkbox(f"{label} — {count} élément(s)", value=key in ["__pycache__", ".pyc", "scripts_patch"], key=f"clean_cat_{key}")
        if checked:
            selected.append(key)

    if not selected:
        st.warning("Sélectionne au moins une catégorie à nettoyer.")
        return

    df = scan_to_dataframe({k: scan[k] for k in selected})

    if df.empty:
        st.success("Rien à supprimer dans les catégories sélectionnées.")
        return

    total = int(df["taille_octets"].sum())

    st.warning(f"{len(df)} élément(s) seront supprimés. Espace estimé : {_file_size(total)}")

    with st.expander("Voir les éléments qui seront supprimés", expanded=False):
        st.dataframe(df.drop(columns=["taille_octets"]), width="stretch", hide_index=True)

    confirm = st.checkbox("Je confirme lancer le nettoyage sécurisé", key="confirm_clean_site")

    if st.button("🧹 Nettoyer maintenant", disabled=not confirm, width="stretch", key="btn_clean_site_now"):
        result = run_cleanup(scan, selected)
        st.success(
            f"Nettoyage terminé : {result['supprimés']} supprimé(s), "
            f"{result['refusés']} refusé(s), espace libéré : {result['espace_libéré']}."
        )
        st.rerun()


def render_diagnostic() -> None:
    st.markdown("### 📊 Diagnostic espace disque")

    folders = [
        ("Projet", PROJECT_DIR),
        ("Data", DATA_DIR),
        ("Exports", DATA_DIR / "exports"),
        ("Backups", DATA_DIR / "backups"),
        ("Patch backups", DATA_DIR / "patch_backups"),
        ("Documents patrimoine", DATA_DIR / "patrimoine_documents"),
        ("Photos patrimoine", DATA_DIR / "patrimoine_photos"),
        ("Assets photos", PROJECT_DIR / "assets" / "photos"),
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
                "taille": _file_size(size),
                "taille Mo": round(size / 1024 / 1024, 2),
            }
        )

    st.dataframe(rows, width="stretch", hide_index=True)


def render(show_title: bool = True) -> None:
    if show_title:  # PATCH73_TITLE_GUARDED
        st.markdown("### 🧹 Nettoyage sécurisé du site")
    if show_title:  # PATCH73_TITLE_GUARDED
        st.caption("Nettoyage des caches, anciens scripts, exports et sauvegardes obsolètes.")

    tabs = st.tabs(
        [
            "🔍 Scanner",
            "🧹 Nettoyer",
            "📊 Diagnostic",
        ]
    )

    with tabs[0]:
        render_scan()

    with tabs[1]:
        render_cleanup()

    with tabs[2]:
        render_diagnostic()


def show() -> None:
    render(show_title=True)



def render(show_title: bool = True) -> None:
    if show_title:
        st.markdown("### 🧹 Nettoyage sécurisé du site")
        st.caption("Nettoyage des caches, anciens scripts, exports et sauvegardes obsolètes.")

    sections = {
        "🔍 Scanner": render_scan,
        "🧹 Nettoyer": render_cleanup,
        "📊 Diagnostic": render_diagnostic,
    }

    selected = st.radio(
        "Section nettoyage site",
        list(sections.keys()),
        horizontal=True,
        label_visibility="collapsed",
        key="nettoyage_site_section",
    )

    st.divider()

    sections[selected]()
