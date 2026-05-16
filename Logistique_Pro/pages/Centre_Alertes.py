# pages/Centre_Alertes.py

import sqlite3
from pathlib import Path
from datetime import datetime, date, timedelta

import pandas as pd
import streamlit as st


BASE_DIR = Path("/opt/logistique-pro")
DEMANDES_DB = BASE_DIR / "data" / "demandes.db"
CATALOGUE_DB = BASE_DIR / "data" / "catalogue_articles.db"


def connect(path):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def parse_date(value):
    if not value:
        return None

    value = str(value).strip()

    for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
        try:
            return datetime.strptime(value, fmt).date()
        except Exception:
            pass

    return None


def load_stock_alerts():
    if not CATALOGUE_DB.exists():
        return pd.DataFrame()

    conn = connect(CATALOGUE_DB)

    df = pd.read_sql_query("""
        SELECT id, nom, categorie, sous_categorie, stock, stock_min, unite, emplacement, etat
        FROM catalogue_articles
        WHERE 
            CAST(stock AS INTEGER) <= CAST(stock_min AS INTEGER)
            OR etat IN ('Bas', 'Critique')
        ORDER BY stock ASC, nom
    """, conn)

    conn.close()
    return df


def load_demandes():
    if not DEMANDES_DB.exists():
        return pd.DataFrame()

    conn = connect(DEMANDES_DB)

    df = pd.read_sql_query("""
        SELECT *
        FROM demandes
        WHERE statut = 'Validée'
        ORDER BY COALESCE(date_debut, date_evenement), id
    """, conn)

    conn.close()

    if df.empty:
        return df

    df["date_start"] = df.apply(
        lambda r: parse_date(r.get("date_debut")) or parse_date(r.get("date_evenement")),
        axis=1,
    )

    df["date_end"] = df.apply(
        lambda r: parse_date(r.get("date_fin")) or parse_date(r.get("date_evenement")),
        axis=1,
    )

    return df


def load_stock_reserve():
    if not DEMANDES_DB.exists():
        return pd.DataFrame()

    conn = connect(DEMANDES_DB)

    try:
        df = pd.read_sql_query("""
            SELECT 
                dl.article_id,
                dl.article_nom,
                SUM(dl.quantite) AS reserve
            FROM demande_lignes dl
            INNER JOIN demandes d ON d.id = dl.demande_id
            WHERE d.statut = 'Validée'
              AND COALESCE(d.retour_stock_reintegre, 0) = 0
              AND LOWER(COALESCE(dl.article_nom, '')) NOT LIKE '%transport%'
            GROUP BY dl.article_id, dl.article_nom
        """, conn)
    except Exception:
        df = pd.DataFrame()

    conn.close()
    return df


def load_catalogue():
    if not CATALOGUE_DB.exists():
        return pd.DataFrame()

    conn = connect(CATALOGUE_DB)
    df = pd.read_sql_query("""
        SELECT id, nom, stock, stock_min, unite, emplacement, etat
        FROM catalogue_articles
    """, conn)
    conn.close()
    return df


def build_alerts():
    today = date.today()
    alerts = []

    stock_alerts = load_stock_alerts()

    for _, row in stock_alerts.iterrows():
        niveau = "Critique" if int(row.get("stock", 0) or 0) <= 0 else "Stock bas"
        alerts.append({
            "Priorité": "Haute" if niveau == "Critique" else "Moyenne",
            "Type": niveau,
            "Référence": f"Article #{row.get('id')}",
            "Objet": row.get("nom"),
            "Date": "-",
            "Détail": f"Stock {row.get('stock')} {row.get('unite')} | min {row.get('stock_min')} | {row.get('emplacement') or '-'}",
        })

    demandes = load_demandes()

    if not demandes.empty:
        for _, row in demandes.iterrows():
            livraison = str(row.get("livraison_statut", "") or "À livrer")
            retour = str(row.get("retour_statut", "") or "En attente retour")

            start = row.get("date_start")
            end = row.get("date_end")

            if start and start <= today + timedelta(days=2) and livraison != "Livrée":
                alerts.append({
                    "Priorité": "Haute",
                    "Type": "Livraison urgente",
                    "Référence": f"Demande #{row.get('id')}",
                    "Objet": row.get("motif"),
                    "Date": start.strftime("%d/%m/%Y"),
                    "Détail": f"{row.get('demandeur')} | {row.get('lieu') or '-'} | statut : {livraison}",
                })

            if end and end < today and retour != "Retournée":
                alerts.append({
                    "Priorité": "Haute",
                    "Type": "Retour en retard",
                    "Référence": f"Demande #{row.get('id')}",
                    "Objet": row.get("motif"),
                    "Date": end.strftime("%d/%m/%Y"),
                    "Détail": f"{row.get('demandeur')} | {row.get('lieu') or '-'} | statut : {retour}",
                })

    reserves = load_stock_reserve()
    catalogue = load_catalogue()

    if not reserves.empty and not catalogue.empty:
        merged = reserves.merge(
            catalogue,
            how="left",
            left_on="article_id",
            right_on="id",
        )

        for _, row in merged.iterrows():
            stock = int(row.get("stock", 0) or 0)
            reserve = int(row.get("reserve", 0) or 0)
            disponible = stock - reserve

            if disponible < 0:
                alerts.append({
                    "Priorité": "Haute",
                    "Type": "Sur-réservation",
                    "Référence": f"Article #{row.get('article_id')}",
                    "Objet": row.get("article_nom"),
                    "Date": "-",
                    "Détail": f"Stock réel {stock} | réservé {reserve} | manque {abs(disponible)}",
                })

    return pd.DataFrame(alerts)


def show():
    st.title("🚨 Centre d’alertes")
    st.caption("Alertes stock, livraisons urgentes, retours en retard et sur-réservations")

    user = st.session_state.get("user")

    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    role = str(user.get("role", "")).lower()
    preview_role = st.session_state.get("preview_role")

    if role == "admin" and preview_role:
        role = str(preview_role).lower()

    if role not in ["admin", "interne", "equipe_interne"]:
        st.error("Accès réservé aux administrateurs et équipes internes.")
        st.stop()

    if st.button("🔄 Actualiser les alertes", width="stretch"):
        st.rerun()

    df = build_alerts()

    if df.empty:
        st.success("Aucune alerte détectée.")
        return

    c1, c2, c3 = st.columns(3)

    c1.metric("Alertes totales", len(df))
    c2.metric("Priorité haute", int((df["Priorité"] == "Haute").sum()))
    c3.metric("Stock / réservation", int(df["Type"].isin(["Critique", "Stock bas", "Sur-réservation"]).sum()))

    st.divider()

    type_filter = st.selectbox(
        "Filtrer par type",
        ["Toutes"] + sorted(df["Type"].dropna().unique().tolist()),
    )

    priority_filter = st.selectbox(
        "Filtrer par priorité",
        ["Toutes", "Haute", "Moyenne"],
    )

    filtered = df.copy()

    if type_filter != "Toutes":
        filtered = filtered[filtered["Type"] == type_filter]

    if priority_filter != "Toutes":
        filtered = filtered[filtered["Priorité"] == priority_filter]

    st.subheader("📋 Alertes détectées")
    st.dataframe(filtered, width="stretch", hide_index=True)

    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Exporter les alertes CSV",
        data=csv,
        file_name="alertes_logistiques.csv",
        mime="text/csv",
        width="stretch",
    )
