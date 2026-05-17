# -*- coding: utf-8 -*-
"""
Administration Système
Routeur interne qui garde le menu gauche de l'application.
"""

from __future__ import annotations

import streamlit as st

from administration_systeme.common import is_admin
from administration_systeme import (
    diagnostic,
    databases,
    backups,
    github_update,
    help_page,
    cleaning,
    logs,
    server_health,
    database_tools,
    maintenance,
    security,
    import_export,
    app_settings,
    github_export,
)


SECTIONS = {
    "Diagnostic": diagnostic.render,
    "Santé serveur": server_health.render,
    "Logs": logs.render,
    "Nettoyage": cleaning.render,
    "Bases de données": databases.render,
    "Outils bases": database_tools.render,
    "Sauvegarde": backups.render,
    "Maintenance": maintenance.render,
    "Sécurité": security.render,
    "Import / Export": import_export.render,
    "Paramètres": app_settings.render,
    "Export GitHub": github_export.render,
    "Mise à jour GitHub": github_update.render,
    "Aide": help_page.render,
}


def go(section: str):
    st.session_state["admin_systeme_module"] = section
    st.rerun()


def card(title: str, text: str, section: str, key: str):
    with st.container(border=True):
        st.subheader(title)
        st.write(text)
        if st.button(f"Ouvrir {section}", width="stretch", key=key):
            go(section)


def show_home():
    st.markdown("### Centre de gestion système")
    st.info("Choisis un bloc. Le menu gauche reste disponible.")

    col1, col2 = st.columns(2)

    with col1:
        card("🩺 Santé serveur", "RAM, disque, swap, service, processus.", "Santé serveur", "open_health")
        card("📜 Logs", "Logs du service, erreurs, recherche et export.", "Logs", "open_logs")
        card("🧹 Nettoyage", "Caches Python, fichiers temporaires, anciennes sauvegardes.", "Nettoyage", "open_cleaning")
        card("🗄️ Bases de données", "Toutes les bases SQLite et détail des tables.", "Bases de données", "open_db")
        card("🧱 Outils bases", "Integrity check, VACUUM, ANALYZE et dump SQL.", "Outils bases", "open_db_tools")

    with col2:
        card("📦 Sauvegarde", "Créer, télécharger, restaurer, supprimer et uploader.", "Sauvegarde", "open_backup")
        card("🚧 Maintenance", "Mode maintenance et message utilisateur.", "Maintenance", "open_maintenance")
        card("🔐 Sécurité", "Admins, fichiers sensibles, permissions et fichiers lourds.", "Sécurité", "open_security")
        card("📤 Import / Export", "Exporter et importer des tables CSV.", "Import / Export", "open_import_export")
        card("⚙️ Paramètres", "Nom, version, thème, footer, URL serveur.", "Paramètres", "open_settings")
        card("🔄 Mise à jour GitHub", "Git status, fetch et pull sécurisé.", "Mise à jour GitHub", "open_github")
        card("🚀 Export GitHub", "Publier les modifications sans images ni secrets, avec bases vides.", "Export GitHub", "open_github_export")
        card("🩺 Diagnostic", "Diagnostic classique et commandes rapides.", "Diagnostic", "open_diag")
        card("🛠️ Aide", "Commandes utiles serveur.", "Aide", "open_help")


def show_module(section: str):
    col1, col2 = st.columns([1, 4])

    with col1:
        if st.button("⬅️ Accueil", width="stretch", key="admin_back_home"):
            st.session_state["admin_systeme_module"] = "Accueil"
            st.rerun()

    with col2:
        st.markdown(f"### {section}")

    st.divider()

    render_func = SECTIONS.get(section)

    if render_func is None:
        st.warning("Module inconnu.")
        return

    render_func()


def show():
    st.title("Administration Système")
    st.success("Administration Système modulaire chargée avec le menu gauche.")

    if not is_admin():
        st.error("Accès réservé aux administrateurs.")
        st.stop()

    if "admin_systeme_module" not in st.session_state:
        st.session_state["admin_systeme_module"] = "Accueil"

    current = st.session_state.get("admin_systeme_module", "Accueil")

    if current == "Accueil":
        show_home()
    else:
        show_module(current)


if __name__ == "__main__":
    show()
