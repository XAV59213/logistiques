# pages/10_Administration_Systeme.py
"""
Page Administration Système
Paramètres techniques, état de la base, dossiers et sauvegardes.
"""

from pathlib import Path
import streamlit as st

from config import Config
from utils.database import get_connection
from utils.backups import create_backup, list_backups
from utils.system_manager import ensure_directories, maintenance_status


def show() -> None:
    st.title("🛠️ Administration Système")
    st.caption("Gestion technique de l'application")

    user = st.session_state.user
    if not user or user.get("role") != "admin":
        st.error("Accès réservé aux administrateurs.")
        st.stop()

    st.subheader("📁 Vérification des dossiers")
    if st.button("Vérifier / créer les dossiers nécessaires", use_container_width=True):
        ensure_directories()
        st.success("Les dossiers requis sont présents.")

    st.subheader("🗄️ État de la base de données")
    db_path = Path(Config.DB_PATH)

    if db_path.exists():
        st.success(f"Base détectée : {db_path.name}")
        st.caption(f"Chemin : {db_path}")
        st.caption(f"Taille : {db_path.stat().st_size} octets")
    else:
        st.error("Base de données introuvable.")

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM articles")
        total_articles = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM notifications")
        total_notifications = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM stock_items")
        total_stock_items = cur.fetchone()[0]

        conn.close()

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Utilisateurs", total_users)
        with c2:
            st.metric("Articles", total_articles)
        with c3:
            st.metric("Notifications", total_notifications)
        with c4:
            st.metric("Stock QR", total_stock_items)

    except Exception as e:
        st.error(f"Erreur lors de la lecture des statistiques système : {e}")

    st.subheader("🚧 Maintenance")
    status = maintenance_status()
    if status["enabled"]:
        st.warning(f"Maintenance active : {status['message']}")
    else:
        st.success("Mode maintenance désactivé.")

    st.info("Le mode maintenance est piloté par les variables d'environnement du fichier .env.")

    st.subheader("💾 Sauvegardes")
    if st.button("Créer une sauvegarde SQLite", type="primary", use_container_width=True):
        success, message = create_backup()
        if success:
            st.success(f"Sauvegarde créée : {Path(message).name}")
        else:
            st.error(message)

    backups = list_backups()
    if not backups:
        st.info("Aucune sauvegarde disponible.")
    else:
        for backup_file in backups:
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{backup_file.name}**")
                    st.caption(f"Taille : {backup_file.stat().st_size} octets")
                with col2:
                    with open(backup_file, "rb") as f:
                        st.download_button(
                            "Télécharger",
                            data=f.read(),
                            file_name=backup_file.name,
                            mime="application/octet-stream",
                            key=f"download_backup_{backup_file.name}",
                            use_container_width=True,
                        )

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
