# pages/03_Tableau_de_bord.py
"""
Page Tableau de Bord
Version dynamique avec statistiques réelles issues de la base SQLite.
"""

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

import utils.database as db
import utils.weather as weather
import utils.ai_forecast as ai_forecast


def _safe_count(query: str, params: tuple = ()) -> int:
    try:
        row = db.fetch_one(query, params)
        if row is None:
            return 0
        return int(row[0])
    except Exception:
        return 0


def _safe_rows(query: str, params: tuple = ()) -> list:
    try:
        rows = db.fetch_all(query, params)
        return rows or []
    except Exception:
        return []


def _get_admin_stats() -> dict:
    stats = {}

    stats["total_users"] = _safe_count("SELECT COUNT(*) FROM users")
    stats["pending_users"] = _safe_count("SELECT COUNT(*) FROM users WHERE status = 'pending'")
    stats["validated_users"] = _safe_count("SELECT COUNT(*) FROM users WHERE status = 'validated'")

    stats["total_articles"] = _safe_count("SELECT COUNT(*) FROM articles WHERE actif = 1")
    stats["critical_articles"] = _safe_count(
        """
        SELECT COUNT(*)
        FROM articles
        WHERE actif = 1
          AND quantite_stock <= stock_minimum
        """
    )
    stats["rupture_articles"] = _safe_count(
        """
        SELECT COUNT(*)
        FROM articles
        WHERE actif = 1
          AND quantite_stock <= 0
        """
    )

    stats["total_outils"] = _safe_count("SELECT COUNT(*) FROM outils WHERE actif = 1")
    stats["critical_outils"] = _safe_count(
        """
        SELECT COUNT(*)
        FROM outils
        WHERE actif = 1
          AND quantite_stock <= stock_minimum
        """
    )

    stats["total_stock_items"] = _safe_count("SELECT COUNT(*) FROM stock_items")
    stats["critical_stock_items"] = _safe_count(
        """
        SELECT COUNT(*)
        FROM stock_items
        WHERE quantity <= min_threshold
        """
    )

    stats["total_vehicules"] = _safe_count("SELECT COUNT(*) FROM vehicules")
    stats["vehicules_disponibles"] = _safe_count(
        """
        SELECT COUNT(*)
        FROM vehicules
        WHERE LOWER(COALESCE(etat, '')) = 'disponible'
        """
    )
    stats["vehicules_maintenance"] = _safe_count(
        """
        SELECT COUNT(*)
        FROM vehicules
        WHERE LOWER(COALESCE(etat, '')) = 'maintenance'
        """
    )

    stats["total_evenements"] = _safe_count("SELECT COUNT(*) FROM evenements")
    stats["notifications_non_lues"] = _safe_count(
        """
        SELECT COUNT(*)
        FROM notifications
        WHERE is_read = 0
        """
    )
    stats["total_buildings"] = _safe_count("SELECT COUNT(*) FROM buildings")

    return stats


def _get_internal_stats() -> dict:
    stats = {}

    stats["total_articles"] = _safe_count("SELECT COUNT(*) FROM articles WHERE actif = 1")
    stats["critical_articles"] = _safe_count(
        """
        SELECT COUNT(*)
        FROM articles
        WHERE actif = 1
          AND quantite_stock <= stock_minimum
        """
    )

    stats["total_outils"] = _safe_count("SELECT COUNT(*) FROM outils WHERE actif = 1")
    stats["critical_outils"] = _safe_count(
        """
        SELECT COUNT(*)
        FROM outils
        WHERE actif = 1
          AND quantite_stock <= stock_minimum
        """
    )

    stats["vehicules_disponibles"] = _safe_count(
        """
        SELECT COUNT(*)
        FROM vehicules
        WHERE LOWER(COALESCE(etat, '')) = 'disponible'
        """
    )
    stats["total_vehicules"] = _safe_count("SELECT COUNT(*) FROM vehicules")

    stats["notifications_non_lues"] = _safe_count(
        """
        SELECT COUNT(*)
        FROM notifications
        WHERE is_read = 0
        """
    )

    stats["evenements_a_venir"] = _safe_count(
        """
        SELECT COUNT(*)
        FROM evenements
        WHERE date(date_debut) >= date('now')
        """
    )

    return stats


def _get_recent_notifications(limit: int = 5) -> list[dict]:
    rows = _safe_rows(
        """
        SELECT id, title, message, level, is_read, created_at
        FROM notifications
        ORDER BY datetime(created_at) DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [dict(r) for r in rows]


def _get_recent_events(limit: int = 5) -> list[dict]:
    rows = _safe_rows(
        """
        SELECT id, titre, description, date_debut, date_fin, lieu, type
        FROM evenements
        ORDER BY date(date_debut) ASC
        LIMIT ?
        """,
        (limit,),
    )
    return [dict(r) for r in rows]


def _get_recent_articles(limit: int = 5) -> list[dict]:
    rows = _safe_rows(
        """
        SELECT id, nom, categorie, quantite_stock, stock_minimum, prix_unitaire
        FROM articles
        WHERE actif = 1
        ORDER BY nom ASC
        LIMIT ?
        """,
        (limit,),
    )
    return [dict(r) for r in rows]


def _get_low_stock_elements(limit: int = 10) -> pd.DataFrame:
    article_rows = _safe_rows(
        """
        SELECT
            'Article' AS type_element,
            nom AS nom,
            categorie AS categorie,
            quantite_stock AS stock,
            stock_minimum AS stock_min
        FROM articles
        WHERE actif = 1
          AND quantite_stock <= stock_minimum
        """
    )

    outil_rows = _safe_rows(
        """
        SELECT
            'Outil' AS type_element,
            nom AS nom,
            categorie AS categorie,
            quantite_stock AS stock,
            stock_minimum AS stock_min
        FROM outils
        WHERE actif = 1
          AND quantite_stock <= stock_minimum
        """
    )

    stock_rows = _safe_rows(
        """
        SELECT
            'Stock' AS type_element,
            name AS nom,
            category AS categorie,
            quantity AS stock,
            min_threshold AS stock_min
        FROM stock_items
        WHERE quantity <= min_threshold
        """
    )

    data = [dict(r) for r in article_rows] + [dict(r) for r in outil_rows] + [dict(r) for r in stock_rows]

    if not data:
        return pd.DataFrame(columns=["Type", "Nom", "Catégorie", "Stock", "Seuil mini"])

    df = pd.DataFrame(data)
    df = df.rename(
        columns={
            "type_element": "Type",
            "nom": "Nom",
            "categorie": "Catégorie",
            "stock": "Stock",
            "stock_min": "Seuil mini",
        }
    )
    df = df.sort_values(by=["Stock", "Nom"], ascending=[True, True]).head(limit)
    return df


def _render_notifications() -> None:
    st.subheader("🛎️ Notifications récentes")
    notifications = _get_recent_notifications(limit=5)

    if not notifications:
        st.info("Aucune notification disponible.")
        return

    for notif in notifications:
        level = (notif.get("level") or "info").lower()
        title = notif.get("title", "Sans titre")
        message = notif.get("message", "")
        created_at = notif.get("created_at", "")
        read_label = "Lue" if int(notif.get("is_read", 0)) == 1 else "Non lue"

        text = f"**{title}**\n\n{message}\n\n*{created_at} • {read_label}*"

        if level == "success":
            st.success(text)
        elif level == "warning":
            st.warning(text)
        elif level == "error":
            st.error(text)
        else:
            st.info(text)


def _render_events() -> None:
    st.subheader("📅 Événements")
    events = _get_recent_events(limit=5)

    if not events:
        st.info("Aucun événement enregistré.")
        return

    rows = []
    for event in events:
        rows.append(
            {
                "Titre": event.get("titre", ""),
                "Début": event.get("date_debut", ""),
                "Fin": event.get("date_fin", ""),
                "Lieu": event.get("lieu", ""),
                "Type": event.get("type", ""),
            }
        )

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_low_stock_table() -> None:
    st.subheader("📦 Éléments en stock bas")
    low_stock_df = _get_low_stock_elements(limit=10)

    if low_stock_df.empty:
        st.success("Aucun élément n'est actuellement sous le seuil minimum.")
        return

    st.dataframe(low_stock_df, use_container_width=True, hide_index=True)


def _render_weather_and_ai() -> None:
    try:
        weather.display_weather_widget()
    except Exception as e:
        st.warning(f"Météo indisponible pour le moment : {e}")

    try:
        ai_forecast.display_ai_forecast()
    except Exception as e:
        st.warning(f"Prévisions IA indisponibles pour le moment : {e}")


def show() -> None:
    st.title("📊 Tableau de Bord")

    user = st.session_state.get("user")
    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    role = user.get("role")
    status = user.get("status", "pending")

    if status == "pending":
        st.warning("Votre compte est en attente de validation.")
        st.stop()

    st.caption(f"Bienvenue {user.get('username', 'Utilisateur')}")

    # ====================== NOTIFICATIONS ======================
    _render_notifications()

    # ====================== DASHBOARD PAR RÔLE ======================
    if role in ["admin", "interne"]:
        stats = _get_admin_stats()

        st.subheader("📈 Vue d'ensemble")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Utilisateurs en attente", stats["pending_users"])
        with col2:
            total_critical = stats["critical_articles"] + stats["critical_outils"] + stats["critical_stock_items"]
            st.metric("Stock critique", total_critical)
        with col3:
            st.metric("Événements", stats["total_evenements"])
        with col4:
            st.metric("Véhicules disponibles", f"{stats['vehicules_disponibles']} / {stats['total_vehicules']}")

        col5, col6, col7, col8 = st.columns(4)
        with col5:
            st.metric("Articles actifs", stats["total_articles"])
        with col6:
            st.metric("Outils actifs", stats["total_outils"])
        with col7:
            st.metric("Notifications non lues", stats["notifications_non_lues"])
        with col8:
            st.metric("Bâtiments", stats["total_buildings"])

        st.markdown("---")
        _render_low_stock_table()

        st.markdown("---")
        _render_events()

        st.markdown("---")
        _render_weather_and_ai()

    elif role == "equipe_interne":
        stats = _get_internal_stats()

        st.subheader("🚛 Vue opérationnelle")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Articles actifs", stats["total_articles"])
        with col2:
            st.metric("Outils actifs", stats["total_outils"])
        with col3:
            st.metric("Stock critique", stats["critical_articles"] + stats["critical_outils"])
        with col4:
            st.metric("Véhicules disponibles", f"{stats['vehicules_disponibles']} / {stats['total_vehicules']}")

        col5, col6 = st.columns(2)
        with col5:
            st.metric("Notifications non lues", stats["notifications_non_lues"])
        with col6:
            st.metric("Événements à venir", stats["evenements_a_venir"])

        st.markdown("---")
        _render_low_stock_table()

        st.markdown("---")
        _render_events()

        st.markdown("---")
        if st.button("✅ Marquer une intervention terminée", use_container_width=False):
            st.info("Le module d'interventions réelles peut maintenant être relié à une future table missions.")

    else:
        st.subheader("📋 Vue utilisateur")
        notifications_non_lues = _safe_count(
            """
            SELECT COUNT(*)
            FROM notifications
            WHERE is_read = 0
            """
        )
        total_evenements = _safe_count("SELECT COUNT(*) FROM evenements")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Notifications non lues", notifications_non_lues)
        with col2:
            st.metric("Événements disponibles", total_evenements)

        st.markdown("---")
        _render_events()

        st.markdown("---")
        st.info("Le suivi personnalisé des demandes utilisateur pourra être branché quand la table des demandes sera créée.")

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
