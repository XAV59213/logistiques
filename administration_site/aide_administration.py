# -*- coding: utf-8 -*-
"""
Aide administration

Module d'aide pour l'administration du site Logistique Pro.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st


PROJECT_DIR = Path("/opt/logistique-pro")
DATA_DIR = PROJECT_DIR / "data"
BACKUP_DIR = DATA_DIR / "patch_backups"
ADMIN_DIR = PROJECT_DIR / "administration_site"
PAGES_DIR = PROJECT_DIR / "pages"


def _code_block(title: str, code: str) -> None:
    st.markdown(f"#### {title}")
    st.code(code.strip(), language="bash")


def _file_status(path: Path) -> str:
    if path.exists():
        return "✅ Présent"
    return "❌ Absent"


def render_overview() -> None:
    st.markdown("### 🧭 Vue d’ensemble")

    st.info(
        "Cette page regroupe les informations utiles pour gérer l’administration "
        "du site Logistique Pro : modules, commandes serveur, sauvegardes et diagnostics."
    )

    modules = [
        {
            "Onglet": "🎨 Thème & identité",
            "Fichier": "administration_site/theme_identite.py",
            "Rôle": "Logo, couleurs, identité visuelle et personnalisation.",
        },
        {
            "Onglet": "👥 Utilisateurs",
            "Fichier": "administration_site/gestion_utilisateurs.py",
            "Rôle": "Gestion des utilisateurs existants.",
        },
        {
            "Onglet": "✅ Validation comptes",
            "Fichier": "administration_site/validation_comptes.py",
            "Rôle": "Validation ou refus des nouveaux comptes.",
        },
        {
            "Onglet": "📦 Articles / Catégories",
            "Fichier": "administration_site/articles_categories.py",
            "Rôle": "Paramétrage des familles, catégories et articles.",
        },
        {
            "Onglet": "📋 Inventaire",
            "Fichier": "administration_site/inventaire.py",
            "Rôle": "Accès au module inventaire.",
        },
        {
            "Onglet": "🚗 Garage / Véhicules",
            "Fichier": "administration_site/garage/",
            "Rôle": "Gestion complète du parc véhicules.",
        },
        {
            "Onglet": "🏢 Patrimoine bâti",
            "Fichier": "administration_site/patrimoine_bati.py",
            "Rôle": "Gestion du patrimoine bâti. Module encore très gros, à découper.",
        },
        {
            "Onglet": "🧾 Facturation",
            "Fichier": "administration_site/parametres_facturation.py",
            "Rôle": "Paramètres de facturation.",
        },
        {
            "Onglet": "❓ Aide",
            "Fichier": "administration_site/aide_administration.py",
            "Rôle": "Aide, diagnostic et commandes utiles.",
        },
    ]

    st.dataframe(modules, width="stretch", hide_index=True)


def render_paths() -> None:
    st.markdown("### 📁 Chemins importants")

    paths = [
        {"Élément": "Projet", "Chemin": str(PROJECT_DIR), "État": _file_status(PROJECT_DIR)},
        {"Élément": "Pages Streamlit", "Chemin": str(PAGES_DIR), "État": _file_status(PAGES_DIR)},
        {"Élément": "Modules Administration", "Chemin": str(ADMIN_DIR), "État": _file_status(ADMIN_DIR)},
        {"Élément": "Données", "Chemin": str(DATA_DIR), "État": _file_status(DATA_DIR)},
        {"Élément": "Sauvegardes patchs", "Chemin": str(BACKUP_DIR), "État": _file_status(BACKUP_DIR)},
        {"Élément": "Venv Python", "Chemin": str(PROJECT_DIR / ".venv"), "État": _file_status(PROJECT_DIR / ".venv")},
        {
            "Élément": "Base Garage",
            "Chemin": str(DATA_DIR / "garage_vehicules.db"),
            "État": _file_status(DATA_DIR / "garage_vehicules.db"),
        },
    ]

    st.dataframe(paths, width="stretch", hide_index=True)


def render_commands() -> None:
    st.markdown("### 🖥️ Commandes utiles LXC / Proxmox")

    _code_block(
        "Redémarrer le service",
        """
systemctl restart logistique.service
systemctl status logistique.service --no-pager
        """,
    )

    _code_block(
        "Voir les logs récents",
        """
journalctl -u logistique.service -n 120 --no-pager
        """,
    )

    _code_block(
        "Suivre les logs en direct",
        """
journalctl -u logistique.service -f
        """,
    )

    _code_block(
        "Compiler les fichiers Python avec le bon environnement",
        """
cd /opt/logistique-pro
/opt/logistique-pro/.venv/bin/python -m compileall pages administration_site utils
        """,
    )

    _code_block(
        "Lister les sauvegardes de patchs",
        """
ls -lh /opt/logistique-pro/data/patch_backups
        """,
    )

    _code_block(
        "Sauvegarde complète manuelle",
        """
cd /opt/logistique-pro
tar --exclude="./data/patch_backups" --exclude="./.venv" --exclude="./venv" --exclude="./__pycache__" \\
    -czf /opt/logistique-pro/data/patch_backups/backup_manual_$(date +%Y%m%d_%H%M%S).tar.gz .
        """,
    )


def render_diagnostics() -> None:
    st.markdown("### 🔍 Diagnostic rapide")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Projet", "OK" if PROJECT_DIR.exists() else "Absent")

    with col2:
        st.metric("Administration", "OK" if ADMIN_DIR.exists() else "Absent")

    with col3:
        st.metric("Sauvegardes", "OK" if BACKUP_DIR.exists() else "Absent")

    st.divider()

    st.markdown("#### Fichiers Administration")

    files = [
        ADMIN_DIR / "theme_identite.py",
        ADMIN_DIR / "gestion_utilisateurs.py",
        ADMIN_DIR / "validation_comptes.py",
        ADMIN_DIR / "articles_categories.py",
        ADMIN_DIR / "inventaire.py",
        ADMIN_DIR / "garage_vehicules.py",
        ADMIN_DIR / "patrimoine_bati.py",
        ADMIN_DIR / "parametres_facturation.py",
        ADMIN_DIR / "aide_administration.py",
    ]

    rows = []
    for file in files:
        rows.append(
            {
                "Fichier": str(file.relative_to(PROJECT_DIR)),
                "État": _file_status(file),
                "Taille": file.stat().st_size if file.exists() else 0,
            }
        )

    st.dataframe(rows, width="stretch", hide_index=True)

    st.markdown("#### Recommandations")

    st.warning(
        "Le module Patrimoine bâti est encore très volumineux. "
        "Il est conseillé de le découper en package comme Garage."
    )

    st.info(
        "Les modules Inventaire et Paramètres facturation sont encore courts. "
        "Il faudra vérifier s’ils doivent rester comme relais ou être reconstruits."
    )


def render_patch_history() -> None:
    st.markdown("### 🧩 Historique / sauvegardes patchs")

    if not BACKUP_DIR.exists():
        st.warning("Aucun dossier de sauvegarde trouvé.")
        return

    files = sorted(BACKUP_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not files:
        st.info("Aucune sauvegarde ou rapport trouvé.")
        return

    rows = []
    for file in files[:100]:
        rows.append(
            {
                "Nom": file.name,
                "Type": "Dossier" if file.is_dir() else "Fichier",
                "Taille": file.stat().st_size if file.is_file() else "",
                "Modifié": file.stat().st_mtime,
            }
        )

    st.dataframe(rows, width="stretch", hide_index=True)

    st.caption("Les dates sont affichées en timestamp système. Les fichiers les plus récents sont en haut.")


def render() -> None:
    st.subheader("❓ Aide administration")

    tabs = st.tabs(
        [
            "🧭 Vue d’ensemble",
            "📁 Chemins",
            "🖥️ Commandes",
            "🔍 Diagnostic",
            "🧩 Sauvegardes",
        ]
    )

    with tabs[0]:
        render_overview()

    with tabs[1]:
        render_paths()

    with tabs[2]:
        render_commands()

    with tabs[3]:
        render_diagnostics()

    with tabs[4]:
        render_patch_history()


def show() -> None:
    render()
