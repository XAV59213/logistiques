# pages/Tableau_de_bord.py

import sqlite3
from pathlib import Path
from datetime import date

import pandas as pd
import streamlit as st


BASE_DIR = Path("/opt/logistique-pro")
DEMANDES_DB = BASE_DIR / "data" / "demandes.db"
CATALOGUE_DB = BASE_DIR / "data" / "catalogue_articles.db"


def connect(path):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def count_demandes_user(email):
    if not DEMANDES_DB.exists():
        return 0, 0, 0

    conn = connect(DEMANDES_DB)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM demandes WHERE email = ?", (email,))
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM demandes WHERE email = ? AND statut = 'En attente'", (email,))
    attente = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM demandes WHERE email = ? AND statut = 'Validée'", (email,))
    validees = cur.fetchone()[0]

    conn.close()
    return total, attente, validees


def load_demandes_by_status(statut):
    if not DEMANDES_DB.exists():
        return pd.DataFrame()

    conn = connect(DEMANDES_DB)

    df = pd.read_sql_query("""
        SELECT id, numero_demande, demandeur, email, motif,
               date_debut, date_fin, date_evenement, lieu, statut, created_at
        FROM demandes
        WHERE statut = ?
        ORDER BY created_at DESC
    """, conn, params=[statut])

    conn.close()
    return df


def load_stock_alert_articles(etat_filter=None):
    if not CATALOGUE_DB.exists():
        return pd.DataFrame()

    conn = connect(CATALOGUE_DB)

    query = """
        SELECT id, nom, categorie, sous_categorie, stock, stock_min, unite, emplacement, etat
        FROM catalogue_articles
        WHERE etat IN ('Bas', 'Critique')
    """
    params = []

    if etat_filter:
        query += " AND etat = ?"
        params.append(etat_filter)

    query += " ORDER BY etat, stock ASC, nom"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def count_admin_stats():
    stats = {
        "demandes_attente": 0,
        "demandes_validees": 0,
        "stock_critique": 0,
        "stock_bas": 0,
    }

    if DEMANDES_DB.exists():
        conn = connect(DEMANDES_DB)
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM demandes WHERE statut = 'En attente'")
        stats["demandes_attente"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM demandes WHERE statut = 'Validée'")
        stats["demandes_validees"] = cur.fetchone()[0]

        conn.close()

    if CATALOGUE_DB.exists():
        conn = connect(CATALOGUE_DB)
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM catalogue_articles WHERE etat = 'Critique'")
        stats["stock_critique"] = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM catalogue_articles WHERE etat = 'Bas'")
        stats["stock_bas"] = cur.fetchone()[0]

        conn.close()

    return stats


def load_my_last_demandes(email):
    if not DEMANDES_DB.exists():
        return pd.DataFrame()

    conn = connect(DEMANDES_DB)
    df = pd.read_sql_query("""
        SELECT id, numero_demande, motif, date_debut, date_fin, date_evenement, lieu, statut
        FROM demandes
        WHERE email = ?
        ORDER BY created_at DESC
        LIMIT 5
    """, conn, params=[email])
    conn.close()
    return df


def load_admin_last_demandes():
    if not DEMANDES_DB.exists():
        return pd.DataFrame()

    conn = connect(DEMANDES_DB)
    df = pd.read_sql_query("""
        SELECT id, demandeur, motif, date_debut, date_fin, date_evenement, lieu, statut
        FROM demandes
        ORDER BY created_at DESC
        LIMIT 8
    """, conn)
    conn.close()
    return df


def load_team_tasks():
    if not DEMANDES_DB.exists():
        return pd.DataFrame()

    conn = connect(DEMANDES_DB)
    df = pd.read_sql_query("""
        SELECT id, demandeur, motif, date_debut, date_fin, date_evenement, lieu,
               livraison_statut, retour_statut
        FROM demandes
        WHERE statut = 'Validée'
        ORDER BY COALESCE(date_debut, date_evenement), id
        LIMIT 10
    """, conn)
    conn.close()
    return df


def show_admin_dashboard(user):
    st.subheader("📈 Vue administrateur")

    stats = count_admin_stats()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Demandes en attente", stats["demandes_attente"])
        if st.button("Voir en attente", key="btn_show_demandes_attente", width="stretch"):
            st.session_state.dashboard_demandes_filter = "En attente"

    with c2:
        st.metric("Demandes validées", stats["demandes_validees"])
        if st.button("Voir validées", key="btn_show_demandes_validees", width="stretch"):
            st.session_state.dashboard_demandes_filter = "Validée"

    with c3:
        st.metric("Stock critique", stats["stock_critique"])
        if st.button("Voir critiques", key="btn_show_stock_critique", width="stretch"):
            st.session_state.dashboard_stock_filter = "Critique"

    with c4:
        st.metric("Stock bas", stats["stock_bas"])
        if st.button("Voir stock bas", key="btn_show_stock_bas", width="stretch"):
            st.session_state.dashboard_stock_filter = "Bas"

    demandes_filter = st.session_state.get("dashboard_demandes_filter")

    if demandes_filter:
        st.subheader(f"📋 Demandes : {demandes_filter}")

        df_dem = load_demandes_by_status(demandes_filter)

        if df_dem.empty:
            st.info(f"Aucune demande avec le statut {demandes_filter}.")
        else:
            st.dataframe(df_dem, width="stretch", hide_index=True)

            if st.button("Masquer la liste demandes", key="hide_dashboard_demandes_list"):
                st.session_state.dashboard_demandes_filter = None
                st.rerun()

    stock_filter = st.session_state.get("dashboard_stock_filter")

    if stock_filter:
        st.subheader(f"📦 Articles en stock {stock_filter.lower()}")

        df_stock = load_stock_alert_articles(stock_filter)

        if df_stock.empty:
            st.success(f"Aucun article en stock {stock_filter.lower()}.")
        else:
            st.dataframe(df_stock, width="stretch", hide_index=True)

            if st.button("Masquer la liste stock", key="hide_dashboard_stock_list"):
                st.session_state.dashboard_stock_filter = None
                st.rerun()

    st.divider()

    st.subheader("⚠️ Alertes stock")
    if stats["stock_critique"] > 0 or stats["stock_bas"] > 0:
        st.warning(f"{stats['stock_critique']} article(s) critique(s), {stats['stock_bas']} article(s) en stock bas.")
    else:
        st.success("Aucune alerte stock.")

    st.subheader("📅 Planning à venir")
    tasks = load_team_tasks()
    if tasks.empty:
        st.info("Aucun événement validé à venir.")
    else:
        st.dataframe(tasks, width="stretch", hide_index=True)

    st.subheader("🔮 Prévisions IA / charge logistique")
    st.info("Section réservée administrateur : analyse prévisionnelle de la charge logistique.")

    st.subheader("📋 Dernières demandes")
    df = load_admin_last_demandes()
    if df.empty:
        st.info("Aucune demande.")
    else:
        st.dataframe(df, width="stretch", hide_index=True)


def show_team_dashboard(user):
    st.subheader("🚚 Tableau de bord équipe interne")

    tasks = load_team_tasks()

    if tasks.empty:
        st.info("Aucune mission validée pour le moment.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Missions visibles", len(tasks))
    c2.metric("À livrer", int((tasks["livraison_statut"].fillna("À livrer") != "Livrée").sum()))
    c3.metric("Retours attendus", int((tasks["retour_statut"].fillna("En attente retour") != "Retournée").sum()))

    st.subheader("📦 Missions logistiques")
    st.dataframe(tasks, width="stretch", hide_index=True)

    st.info("Pour valider une livraison ou un retour, utilisez la page Équipe Logistique.")


def show_public_dashboard(user):
    st.subheader("👤 Mon espace")

    email = user.get("email", "")
    total, attente, validees = count_demandes_user(email)

    c1, c2, c3 = st.columns(3)
    c1.metric("Mes demandes", total)
    c2.metric("En attente", attente)
    c3.metric("Validées", validees)

    st.info(
        "Vous pouvez créer une demande de matériel ou consulter vos demandes validées depuis le menu."
    )

    st.subheader("📋 Mes dernières demandes")

    df = load_my_last_demandes(email)
    if df.empty:
        st.info("Vous n'avez pas encore de demande.")
    else:
        st.dataframe(df, width="stretch", hide_index=True)


def show():
    st.title("📊 Tableau de Bord")

    user = st.session_state.get("user")

    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    role = str(user.get("role", "")).lower()
    status = user.get("status", "pending")

    preview_role = st.session_state.get("preview_role")
    if role == "admin" and preview_role:
        role = str(preview_role).lower()

    if status == "pending":
        st.warning("Votre compte est en attente de validation.")
        st.stop()

    st.caption(f"Connecté : {user.get('username', '-')} | Profil : {role}")

    if role == "admin":
        show_admin_dashboard(user)

    elif role in ["interne", "equipe_interne"]:
        show_team_dashboard(user)

    elif role in ["association", "particulier", "societe", "prestataire"]:
        show_public_dashboard(user)

    else:
        show_public_dashboard(user)
