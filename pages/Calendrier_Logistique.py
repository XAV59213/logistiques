# pages/Calendrier_Logistique.py

import sqlite3
from pathlib import Path
from datetime import datetime, date, timedelta
import calendar

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


BASE_DIR = Path("/opt/logistique-pro")
DEMANDES_DB = BASE_DIR / "data" / "demandes.db"


def connect():
    conn = sqlite3.connect(DEMANDES_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_columns():
    conn = connect()
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(demandes)")
    cols = [r["name"] for r in cur.fetchall()]

    needed = {
        "date_debut": "TEXT",
        "date_fin": "TEXT",
        "heure_evenement": "TEXT",
        "lieu": "TEXT",
        "adresse_livraison": "TEXT",
        "livraison_statut": "TEXT DEFAULT 'À livrer'",
        "retour_statut": "TEXT DEFAULT 'En attente retour'",
    }

    for col, typ in needed.items():
        if col not in cols:
            cur.execute(f"ALTER TABLE demandes ADD COLUMN {col} {typ}")

    conn.commit()
    conn.close()


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


def load_events():
    if not DEMANDES_DB.exists():
        return pd.DataFrame()

    conn = connect()

    df = pd.read_sql_query("""
        SELECT *
        FROM demandes
        WHERE statut IN ('Validée','Livrée','Retournée','Clôturée')
        ORDER BY COALESCE(date_debut, date_evenement), heure_evenement
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

    df = df[df["date_start"].notna()]
    return df


def event_color(row):
    livraison = str(row.get("livraison_statut", "") or "")
    retour = str(row.get("retour_statut", "") or "")

    if str(row.get("statut", "")) == "Clôturée":
        return "#64748b"
    statut = str(row.get("statut", "")).strip()
    livraison = str(row.get("livraison_statut", "")).strip()
    retour = str(row.get("retour_statut", "")).strip()
    cloture = str(row.get("cloture_statut", "")).strip()

    if cloture == "Clôturée" or statut == "Clôturée":
        return "#64748b"   # gris

    if retour == "Retournée":
        return "#16a34a"   # vert

    if livraison == "Livrée":
        return "#2563eb"   # bleu

    if statut == "Validée":
        return "#f59e0b"   # orange
    if livraison == "Livrée":
        return "#2563eb"
    return "#f59e0b"


def build_month_calendar(df, year, month):
    cal = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdatescalendar(year, month)

    html = """
    <style>
    .cal-table { width:100%; border-collapse:collapse; table-layout:fixed; }
    .cal-table th { background:#003366; color:white; padding:8px; text-align:center; }
    .cal-table td { vertical-align:top; height:130px; border:1px solid #dbe3ec; padding:6px; background:white; }
    .cal-muted { background:#f8fafc !important; color:#94a3b8; }
    .cal-day { font-weight:bold; margin-bottom:4px; }
    .cal-event { color:white; padding:4px 6px; border-radius:7px; margin:4px 0; font-size:12px; line-height:1.2; }
    </style>
    <table class="cal-table">
    <tr>
        <th>Lundi</th><th>Mardi</th><th>Mercredi</th><th>Jeudi</th><th>Vendredi</th><th>Samedi</th><th>Dimanche</th>
    </tr>
    """

    for week in weeks:
        html += "<tr>"
        for d in week:
            muted = "cal-muted" if d.month != month else ""
            html += f"<td class='{muted}'>"
            html += f"<div class='cal-day'>{d.day}</div>"

            day_events = df[
                (df["date_start"] <= d) &
                (df["date_end"] >= d)
            ]

            for _, row in day_events.iterrows():
                color = event_color(row)
                title = str(row.get("motif", "Événement"))
                demandeur = str(row.get("demandeur", ""))
                lieu = str(row.get("lieu", ""))
                html += f"""
                <div class="cal-event" style="background:{color};">
                    <b>#{row.get('id')} {title}</b><br>
                    {demandeur}<br>
                    {lieu}
                </div>
                """

            html += "</td>"
        html += "</tr>"

    html += "</table>"
    return html


def show():
    ensure_columns()

    st.title("📅 Calendrier Logistique")
    st.caption("Vue visuelle des événements validés, livraisons et retours")

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

    df = load_events()

    if df.empty:
        st.info("Aucun événement validé à afficher.")
        return

    today = date.today()

    c1, c2, c3 = st.columns(3)

    with c1:
        selected_month = st.selectbox(
            "Mois",
            list(range(1, 13)),
            index=today.month - 1,
            format_func=lambda m: calendar.month_name[m].capitalize(),
        )

    with c2:
        selected_year = st.number_input(
            "Année",
            min_value=2024,
            max_value=2035,
            value=today.year,
            step=1,
        )

    with c3:
        view_mode = st.selectbox(
            "Vue",
            ["Calendrier", "Liste détaillée", "Alertes"],
        )

    month_start = date(int(selected_year), int(selected_month), 1)
    last_day = calendar.monthrange(int(selected_year), int(selected_month))[1]
    month_end = date(int(selected_year), int(selected_month), last_day)

    df_month = df[
        (df["date_start"] <= month_end) &
        (df["date_end"] >= month_start)
    ].copy()

    st.divider()

    k1, k2, k3, k4 = st.columns(4)

    k1.metric("Événements du mois", len(df_month))
    k2.metric("À livrer", int((df_month["livraison_statut"].fillna("À livrer") != "Livrée").sum()))
    k3.metric("Livrés", int((df_month["livraison_statut"].fillna("") == "Livrée").sum()))
    k4.metric("Retournés", int((df_month["retour_statut"].fillna("") == "Retournée").sum()))

    if view_mode == "Calendrier":
        st.subheader("🗓️ Vue mensuelle")
        components.html(
            build_month_calendar(df_month, int(selected_year), int(selected_month)),
            height=900,
            scrolling=True,
        )

        st.info(
            "Couleurs : orange = à livrer, bleu = livré, vert = retourné."
        )

    elif view_mode == "Liste détaillée":
        st.subheader("📋 Liste détaillée")

        display = df_month.copy()

        cols = [
            c for c in [
                "id", "demandeur", "motif", "date_debut", "date_fin",
                "date_evenement", "heure_evenement", "lieu", "adresse_livraison",
                "livraison_statut", "retour_statut"
            ]
            if c in display.columns
        ]

        display = display[cols].rename(columns={
            "id": "Demande",
            "demandeur": "Demandeur",
            "motif": "Événement",
            "date_debut": "Début",
            "date_fin": "Fin",
            "date_evenement": "Date",
            "heure_evenement": "Heure",
            "lieu": "Lieu",
            "adresse_livraison": "Livraison",
            "livraison_statut": "Statut livraison",
            "retour_statut": "Statut retour",
        })

        st.dataframe(display, width="stretch", hide_index=True)

    else:
        st.subheader("⚠️ Alertes logistiques")

        alerts = []

        for _, row in df_month.iterrows():
            start = row["date_start"]
            livraison = str(row.get("livraison_statut", "") or "À livrer")
            retour = str(row.get("retour_statut", "") or "En attente retour")

            if start and start <= today + timedelta(days=2) and livraison != "Livrée":
                alerts.append({
                    "Type": "Livraison urgente",
                    "Demande": row.get("id"),
                    "Événement": row.get("motif"),
                    "Date": start.strftime("%d/%m/%Y"),
                    "Lieu": row.get("lieu"),
                    "Statut": livraison,
                })

            if row["date_end"] and row["date_end"] < today and retour != "Retournée":
                alerts.append({
                    "Type": "Retour en retard",
                    "Demande": row.get("id"),
                    "Événement": row.get("motif"),
                    "Date": row["date_end"].strftime("%d/%m/%Y"),
                    "Lieu": row.get("lieu"),
                    "Statut": retour,
                })

        if not alerts:
            st.success("Aucune alerte logistique.")
        else:
            st.dataframe(pd.DataFrame(alerts), width="stretch", hide_index=True)
