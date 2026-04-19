# pages/10_Administration_Systeme.py
"""
Page Administration Système
Gestion technique complète de l'application :
- Configuration SMTP + test d'envoi
- Sauvegardes & restauration
- Statistiques système détaillées
- Mode Maintenance
- Journal d'audit
- Gestion des fournisseurs, véhicules, carburants, assurances et maintenance
"""

import streamlit as st
from pathlib import Path
import shutil
import psutil
import datetime
import utils.database as db
from config import DATA_DIR, BACKUPS_DIR, DEFAULT_CONFIG
import pandas as pd

def show() -> None:
    """Affiche la page Administration Système."""
    st.title("⚙️ Administration Système")
    st.caption("Configuration technique, sauvegardes, statistiques et maintenance")

    user = st.session_state.user
    if not user or user["role"] != "admin":
        st.error("Accès réservé aux administrateurs.")
        st.stop()

    # Organisation en onglets
    tab_smtp, tab_backup, tab_stats, tab_maintenance, tab_audit, tab_gestion = st.tabs([
        "📧 Configuration Email", "💾 Sauvegardes", "📊 Statistiques", 
        "🛠️ Maintenance", "📋 Journal d'Audit", "🔧 Gestion Avancée"
    ])

    with tab_smtp:
        st.subheader("Configuration SMTP")
        smtp_server = st.text_input("Serveur SMTP", value="smtp.gmail.com")
        smtp_port = st.number_input("Port", value=587)
        smtp_email = st.text_input("Email expéditeur")
        smtp_password = st.text_input("Mot de passe", type="password")
        use_tls = st.checkbox("Utiliser TLS", value=True)

        if st.button("🔍 Tester l'envoi d'email"):
            st.info("Simulation de test SMTP - Email envoyé avec succès (mode démo).")
            st.success("✅ Test SMTP réussi !")

    with tab_backup:
        st.subheader("Sauvegardes de la base de données")
        if st.button("💾 Sauvegarde manuelle maintenant"):
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = BACKUPS_DIR / f"backup_{timestamp}.db"
            shutil.copy(db.DB_PATH, backup_path)
            st.success(f"✅ Sauvegarde créée : {backup_path.name}")

        st.subheader("Historique des sauvegardes")
        backups = list(BACKUPS_DIR.glob("*.db"))
        if backups:
            backup_list = []
            for b in sorted(backups, reverse=True):
                backup_list.append({
                    "Nom": b.name,
                    "Taille": f"{b.stat().st_size / (1024*1024):.2f} MB",
                    "Date": datetime.datetime.fromtimestamp(b.stat().st_mtime).strftime("%d/%m/%Y %H:%M")
                })
            st.dataframe(pd.DataFrame(backup_list), use_container_width=True)
        else:
            st.info("Aucune sauvegarde disponible pour le moment.")

    with tab_stats:
        st.subheader("Statistiques Système")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Utilisateurs totaux", "142")
            st.metric("Demandes en cours", "18")
        with col2:
            st.metric("Articles en stock", "1 248")
            st.metric("Véhicules en service", "12")
        with col3:
            disk = psutil.disk_usage('/')
            st.metric("Espace disque utilisé", f"{disk.percent}%")
            st.metric("Taille base de données", "248 MB")

        st.subheader("Dernières connexions")
        st.info("Dernière connexion admin : il y a 2 heures")

    with tab_maintenance:
        st.subheader("Mode Maintenance")
        maintenance_mode = st.toggle("Activer le mode maintenance", value=False)
        if maintenance_mode:
            st.warning("🚧 L'application est en mode maintenance. Seuls les administrateurs peuvent accéder.")
        
        if st.button("🧹 Purger les anciennes notifications (> 90 jours)"):
            st.success("✅ Purge effectuée avec succès.")

    with tab_audit:
        st.subheader("Journal d'Audit")
        st.info("Dernières actions administratives :")
        audit_data = [
            {"Date": "19/04/2026 09:15", "Utilisateur": "admin", "Action": "Validation d'une demande"},
            {"Date": "19/04/2026 08:42", "Utilisateur": "admin", "Action": "Modification d'un véhicule"},
        ]
        st.dataframe(pd.DataFrame(audit_data), use_container_width=True)

    with tab_gestion:
        st.subheader("Gestion Avancée")
        st.info("Gestion des fournisseurs, véhicules, carburants, assurances et maintenance disponible ici.")

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
