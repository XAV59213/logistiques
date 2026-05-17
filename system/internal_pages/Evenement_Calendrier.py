# pages/07_Calendrier_Evenements.py
"""
Calendrier des Événements
Version réelle : lecture depuis les demandes validées et la table evenements si disponible.
Aucune donnée de démonstration.
"""

import calendar
import csv
import io
import sqlite3
from datetime import datetime, date, timedelta
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

try:
    from config import Config
    MAIN_DB = Path(Config.DB_PATH)
except Exception:
    MAIN_DB = Path("/opt/logistique-pro/database.db")

BASE_DIR = Path("/opt/logistique-pro")
DEMANDES_DB = BASE_DIR / "data" / "demandes.db"


ITEMS_PER_PAGE = 10


def parse_date(value):
    if not value:
        return None

    value = str(value).strip()

    for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"]:
        try:
            return datetime.strptime(value, fmt).date()
        except Exception:
            pass

    return None


def format_date(value):
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return ""


def table_exists(cur, table_name):
    row = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def get_columns(cur, table_name):
    try:
        return [r["name"] for r in cur.execute(f"PRAGMA table_info({table_name})").fetchall()]
    except Exception:
        return []


def clean(value):
    return " ".join(str(value or "").strip().split())


def event_color(statut):
    statut = clean(statut).lower()

    if statut in ["clôturée", "cloturee", "terminé", "termine"]:
        return "#64748b"

    if statut in ["retournée", "retournee"]:
        return "#16a34a"

    if statut in ["livrée", "livree"]:
        return "#2563eb"

    if statut in ["validée", "validee", "confirmé", "confirme"]:
        return "#f59e0b"

    return "#0f766e"


def load_from_demandes():
    events = []

    if not DEMANDES_DB.exists():
        return events

    conn = sqlite3.connect(DEMANDES_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if not table_exists(cur, "demandes"):
        conn.close()
        return events

    cols = get_columns(cur, "demandes")

    wanted = [
        "id",
        "numero_demande",
        "demandeur",
        "email",
        "motif",
        "date_debut",
        "date_fin",
        "date_evenement",
        "heure_evenement",
        "lieu",
        "adresse_livraison",
        "statut",
        "livraison_statut",
        "retour_statut",
        "created_at",
    ]

    select_cols = [c for c in wanted if c in cols]

    if not select_cols:
        conn.close()
        return events

    # On affiche les demandes réellement enregistrées.
    # Les statuts validés/logistiques sont prioritaires.
    status_filter = ""
    if "statut" in cols:
        status_filter = """
        WHERE COALESCE(statut, '') IN (
            'Validée',
            'Validee',
            'Livrée',
            'Livree',
            'Retournée',
            'Retournee',
            'Clôturée',
            'Cloturee',
            'Confirmé',
            'Confirme'
        )
        """

    query = f"""
        SELECT {", ".join(select_cols)}
        FROM demandes
        {status_filter}
        ORDER BY COALESCE(date_debut, date_evenement, created_at), COALESCE(heure_evenement, '')
    """

    rows = cur.execute(query).fetchall()
    conn.close()

    for row in rows:
        r = dict(row)

        start = parse_date(r.get("date_debut")) or parse_date(r.get("date_evenement"))
        end = parse_date(r.get("date_fin")) or parse_date(r.get("date_evenement")) or start

        if not start:
            continue

        titre = clean(r.get("motif")) or f"Demande #{r.get('id')}"
        demandeur = clean(r.get("demandeur"))
        statut = clean(r.get("statut")) or "Validée"

        events.append({
            "id": r.get("id"),
            "source": "Demande",
            "titre": titre,
            "type": "Demande logistique",
            "demandeur": demandeur,
            "date_start": start,
            "date_end": end,
            "heure": clean(r.get("heure_evenement")),
            "lieu": clean(r.get("lieu")) or clean(r.get("adresse_livraison")),
            "statut": statut,
            "livraison_statut": clean(r.get("livraison_statut")),
            "retour_statut": clean(r.get("retour_statut")),
            "description": "",
        })

    return events


def load_from_evenements_table():
    events = []

    if not MAIN_DB.exists():
        return events

    conn = sqlite3.connect(MAIN_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if not table_exists(cur, "evenements"):
        conn.close()
        return events

    cols = get_columns(cur, "evenements")

    wanted = [
        "id",
        "titre",
        "description",
        "date_debut",
        "date_fin",
        "lieu",
        "type",
        "created_at",
    ]

    select_cols = [c for c in wanted if c in cols]

    if not select_cols:
        conn.close()
        return events

    rows = cur.execute(
        f"""
        SELECT {", ".join(select_cols)}
        FROM evenements
        ORDER BY COALESCE(date_debut, created_at)
        """
    ).fetchall()

    conn.close()

    for row in rows:
        r = dict(row)

        start = parse_date(r.get("date_debut"))
        end = parse_date(r.get("date_fin")) or start

        if not start:
            continue

        events.append({
            "id": r.get("id"),
            "source": "Événement",
            "titre": clean(r.get("titre")) or f"Événement #{r.get('id')}",
            "type": clean(r.get("type")) or "Autre",
            "demandeur": "",
            "date_start": start,
            "date_end": end,
            "heure": "",
            "lieu": clean(r.get("lieu")),
            "statut": "Planifié",
            "livraison_statut": "",
            "retour_statut": "",
            "description": clean(r.get("description")),
        })

    return events


def load_events():
    events = []
    events.extend(load_from_demandes())
    events.extend(load_from_evenements_table())

    events.sort(key=lambda e: (e["date_start"], e.get("heure") or "", e.get("titre") or ""))

    return events


def filter_by_period(events, periode):
    today = date.today()

    if periode == "Cette semaine":
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
    elif periode == "Ce mois":
        start = date(today.year, today.month, 1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        end = date(today.year, today.month, last_day)
    elif periode == "30 prochains jours":
        start = today
        end = today + timedelta(days=30)
    else:
        return events

    return [
        e for e in events
        if e["date_start"] <= end and e["date_end"] >= start
    ]


def filter_events(events, search, periode, selected_types, selected_status):
    filtered = filter_by_period(events, periode)

    if selected_types:
        filtered = [
            e for e in filtered
            if e.get("type") in selected_types
        ]

    if selected_status and selected_status != "Tous":
        filtered = [
            e for e in filtered
            if e.get("statut") == selected_status
        ]

    if search:
        s = search.lower().strip()

        def match(e):
            fields = [
                e.get("titre", ""),
                e.get("type", ""),
                e.get("demandeur", ""),
                e.get("lieu", ""),
                e.get("statut", ""),
                e.get("description", ""),
            ]
            return any(s in str(v).lower() for v in fields)

        filtered = [e for e in filtered if match(e)]

    return filtered


def build_month_calendar(events, year, month):
    cal = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdatescalendar(year, month)

    html = """
    <style>
    .cal-table { width:100%; border-collapse:collapse; table-layout:fixed; font-family:Arial, sans-serif; }
    .cal-table th { background:#003366; color:white; padding:8px; text-align:center; }
    .cal-table td { vertical-align:top; height:135px; border:1px solid #dbe3ec; padding:6px; background:white; }
    .cal-muted { background:#f8fafc !important; color:#94a3b8; }
    .cal-day { font-weight:bold; margin-bottom:4px; color:#0f172a; }
    .cal-event { color:white; padding:4px 6px; border-radius:7px; margin:4px 0; font-size:12px; line-height:1.25; }
    .cal-small { font-size:11px; opacity:0.95; }
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

            day_events = [
                e for e in events
                if e["date_start"] <= d <= e["date_end"]
            ]

            for event in day_events[:4]:
                color = event_color(event.get("statut"))
                title = event.get("titre", "Événement")
                lieu = event.get("lieu", "")
                heure = event.get("heure", "")

                html += f"""
                <div class="cal-event" style="background:{color};">
                    <b>{title}</b><br>
                    <span class="cal-small">{heure} {lieu}</span>
                </div>
                """

            if len(day_events) > 4:
                html += f"<div class='cal-small'>+ {len(day_events) - 4} autre(s)</div>"

            html += "</td>"

        html += "</tr>"

    html += "</table>"
    return html


def rows_for_display(events):
    rows = []

    for e in events:
        rows.append({
            "ID": e.get("id", ""),
            "Source": e.get("source", ""),
            "Date début": format_date(e.get("date_start")),
            "Date fin": format_date(e.get("date_end")),
            "Heure": e.get("heure", ""),
            "Événement": e.get("titre", ""),
            "Type": e.get("type", ""),
            "Demandeur": e.get("demandeur", ""),
            "Lieu": e.get("lieu", ""),
            "Statut": e.get("statut", ""),
        })

    return rows


def events_to_csv(events):
    output = io.StringIO()
    fieldnames = [
        "id",
        "source",
        "titre",
        "type",
        "demandeur",
        "date_debut",
        "date_fin",
        "heure",
        "lieu",
        "statut",
        "livraison_statut",
        "retour_statut",
        "description",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=";")
    writer.writeheader()

    for e in events:
        writer.writerow({
            "id": e.get("id", ""),
            "source": e.get("source", ""),
            "titre": e.get("titre", ""),
            "type": e.get("type", ""),
            "demandeur": e.get("demandeur", ""),
            "date_debut": format_date(e.get("date_start")),
            "date_fin": format_date(e.get("date_end")),
            "heure": e.get("heure", ""),
            "lieu": e.get("lieu", ""),
            "statut": e.get("statut", ""),
            "livraison_statut": e.get("livraison_statut", ""),
            "retour_statut": e.get("retour_statut", ""),
            "description": e.get("description", ""),
        })

    return output.getvalue().encode("utf-8-sig")


def render_alerts(events):
    today = date.today()
    alerts = []

    for e in events:
        start = e.get("date_start")
        end = e.get("date_end")
        statut = clean(e.get("statut")).lower()

        if start and today <= start <= today + timedelta(days=2):
            alerts.append({
                "Type": "Événement proche",
                "Date": format_date(start),
                "Événement": e.get("titre", ""),
                "Lieu": e.get("lieu", ""),
                "Statut": e.get("statut", ""),
            })

        if end and end < today and statut not in ["clôturée", "cloturee", "terminé", "termine"]:
            alerts.append({
                "Type": "Événement passé non clôturé",
                "Date": format_date(end),
                "Événement": e.get("titre", ""),
                "Lieu": e.get("lieu", ""),
                "Statut": e.get("statut", ""),
            })

    if not alerts:
        st.success("Aucune alerte événement.")
    else:
        st.dataframe(alerts, width="stretch", hide_index=True)


def show() -> None:
    st.title("📅 Calendrier des Événements")
    st.caption("Vue réelle des événements programmés")

    user = st.session_state.get("user")

    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    events = load_events()

    st.info("Mode réel actif : cette page n’utilise plus les données de démonstration.")

    if not events:
        st.warning("Aucun événement réel trouvé.")
        st.info("Les événements apparaîtront ici après validation des demandes ou ajout dans la table evenements.")
        return

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        search = st.text_input("🔍 Recherche", placeholder="Nom, lieu, demandeur...")

    with col2:
        periode = st.selectbox(
            "Période",
            ["Cette semaine", "Ce mois", "30 prochains jours", "Tout"],
            index=2,
        )

    all_types = sorted(set(clean(e.get("type")) for e in events if clean(e.get("type"))))
    with col3:
        selected_types = st.multiselect(
            "Type d'événement",
            all_types,
            default=all_types,
        )

    all_status = sorted(set(clean(e.get("statut")) for e in events if clean(e.get("statut"))))
    with col4:
        selected_status = st.selectbox(
            "Statut",
            ["Tous"] + all_status,
        )

    filtered = filter_events(events, search, periode, selected_types, selected_status)

    st.divider()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Événements", len(filtered))
    c2.metric("Demandes", len([e for e in filtered if e.get("source") == "Demande"]))
    c3.metric("Événements directs", len([e for e in filtered if e.get("source") == "Événement"]))
    c4.metric("Alertes", len([
        e for e in filtered
        if e.get("date_start") and date.today() <= e.get("date_start") <= date.today() + timedelta(days=2)
    ]))

    tab_calendar, tab_list, tab_weather, tab_alerts = st.tabs([
        "🗓️ Calendrier",
        "📋 Liste",
        "🌤️ Météo",
        "⚠️ Alertes",
    ])

    with tab_calendar:
        today = date.today()

        c_month, c_year = st.columns(2)

        with c_month:
            selected_month = st.selectbox(
                "Mois",
                list(range(1, 13)),
                index=today.month - 1,
                format_func=lambda m: calendar.month_name[m].capitalize(),
            )

        with c_year:
            selected_year = st.number_input(
                "Année",
                min_value=2024,
                max_value=2035,
                value=today.year,
                step=1,
            )

        month_start = date(int(selected_year), int(selected_month), 1)
        month_end = date(
            int(selected_year),
            int(selected_month),
            calendar.monthrange(int(selected_year), int(selected_month))[1],
        )

        month_events = [
            e for e in filtered
            if e["date_start"] <= month_end and e["date_end"] >= month_start
        ]

        components.html(
            build_month_calendar(month_events, int(selected_year), int(selected_month)),
            height=900,
            scrolling=True,
        )

        st.caption("Couleurs : orange = validé/confirmé, bleu = livré, vert = retourné, gris = clôturé.")

    with tab_list:
        if not filtered:
            st.warning("Aucun événement avec ces filtres.")
        else:
            total_pages = max(1, (len(filtered) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

            if "cal_evt_page" not in st.session_state:
                st.session_state["cal_evt_page"] = 1

            page = int(st.session_state["cal_evt_page"])

            if page < 1:
                page = 1
            if page > total_pages:
                page = total_pages

            st.session_state["cal_evt_page"] = page

            start = (page - 1) * ITEMS_PER_PAGE
            end = start + ITEMS_PER_PAGE

            page_events = filtered[start:end]

            st.dataframe(
                rows_for_display(page_events),
                width="stretch",
                hide_index=True,
            )

            st.caption(
                f"Affichage de {start + 1} à {min(end, len(filtered))} "
                f"sur {len(filtered)} événement(s). Maximum {ITEMS_PER_PAGE} par page."
            )

            p1, p2, p3 = st.columns([1, 2, 1])

            with p1:
                if st.button("⬅️ Précédent", disabled=page <= 1, width="stretch"):
                    st.session_state["cal_evt_page"] = page - 1
                    st.rerun()

            with p2:
                st.markdown(
                    f"<div style='text-align:center; padding-top:0.5rem;'>"
                    f"Page <b>{page}</b> / <b>{total_pages}</b>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            with p3:
                if st.button("Suivant ➡️", disabled=page >= total_pages, width="stretch"):
                    st.session_state["cal_evt_page"] = page + 1
                    st.rerun()

            st.download_button(
                "📥 Télécharger les événements filtrés CSV",
                data=events_to_csv(filtered),
                file_name="calendrier_evenements.csv",
                mime="text/csv",
                width="stretch",
            )

    with tab_weather:
        st.subheader("🌤️ Météo")
        st.caption("Widget météo existant si le module est disponible.")

        try:
            import utils.weather as weather
            weather.display_weather_widget()
        except Exception as e:
            st.info(f"Module météo indisponible ou non configuré : {e}")

    with tab_alerts:
        render_alerts(filtered)
