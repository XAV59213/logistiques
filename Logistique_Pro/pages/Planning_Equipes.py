# pages/08_Planning_Equipes.py
"""
Page Planning Équipes
Planning opérationnel avec clôture réelle des missions.
"""

import sqlite3
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "planning_equipes.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_planning_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS planning_equipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            heure TEXT NOT NULL,
            equipe TEXT NOT NULL,
            mission TEXT NOT NULL,
            lieu TEXT,
            vehicule TEXT,
            statut TEXT DEFAULT 'Planifiée',
            date_cloture TEXT,
            cloture_par TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("SELECT COUNT(*) AS total FROM planning_equipes")
    total = cur.fetchone()["total"]

    if total == 0:
        missions = [
            ("21/04/2026", "08:00", "Équipe Alpha", "Montage barnum", "Salle des Fêtes", "Renault Master", "Planifiée"),
            ("21/04/2026", "13:30", "Équipe Beta", "Livraison chaises et tables", "Parc communal", "Peugeot Boxer", "En cours"),
            ("22/04/2026", "09:00", "Équipe Technique", "Installation sonorisation", "Place de l'Église", "Citroën Jumper", "Planifiée"),
            ("23/04/2026", "14:00", "Équipe Logistique", "Contrôle inventaire", "Entrepôt A", "Aucun", "Terminée"),
        ]

        cur.executemany("""
            INSERT INTO planning_equipes (
                date, heure, equipe, mission, lieu, vehicule, statut
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, missions)

    conn.commit()
    conn.close()


def load_planning(equipe_filter="Toutes", statut_filter="Tous"):
    conn = get_connection()

    query = """
        SELECT id, date, heure, equipe, mission, lieu, vehicule, statut, date_cloture, cloture_par
        FROM planning_equipes
        WHERE 1 = 1
    """

    params = []

    if equipe_filter != "Toutes":
        query += " AND equipe = ?"
        params.append(equipe_filter)

    if statut_filter != "Tous":
        query += " AND statut = ?"
        params.append(statut_filter)

    query += " ORDER BY date, heure"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def get_equipes():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT equipe FROM planning_equipes ORDER BY equipe")
    rows = cur.fetchall()
    conn.close()

    equipes = [row["equipe"] for row in rows]
    return ["Toutes"] + equipes


def add_intervention(date, heure, equipe, mission, lieu, vehicule, statut):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO planning_equipes (
            date, heure, equipe, mission, lieu, vehicule, statut
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        date,
        heure,
        equipe,
        mission,
        lieu,
        vehicule,
        statut,
    ))

    conn.commit()
    conn.close()


def terminer_missions(ids, user_email):
    conn = get_connection()
    cur = conn.cursor()

    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    for mission_id in ids:
        cur.execute("""
            UPDATE planning_equipes
            SET statut = 'Terminée',
                date_cloture = ?,
                cloture_par = ?
            WHERE id = ?
        """, (now, user_email, int(mission_id)))

    conn.commit()
    conn.close()


def show() -> None:
    init_planning_db()

    st.title("📅 Planning Équipes")
    st.caption("Organisation des interventions et suivi opérationnel")

    user = st.session_state.get("user")

    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    role = str(user.get("role", "")).lower()

    if role not in ["admin", "interne", "equipe_interne"]:
        st.error("Accès réservé aux équipes internes et administrateurs.")
        st.stop()

    col1, col2, col3 = st.columns(3)

    with col1:
        equipe = st.selectbox("Équipe", get_equipes(), key="planning_filter_equipe")

    with col2:
        periode = st.selectbox(
            "Période",
            ["Toutes", "Aujourd'hui", "Cette semaine", "Ce mois"],
            key="planning_filter_periode"
        )

    with col3:
        statut = st.selectbox(
            "Statut",
            ["Tous", "Planifiée", "En cours", "Terminée"],
            key="planning_filter_statut"
        )

    df = load_planning(equipe, statut)

    st.subheader("📋 Planning des interventions")

    if df.empty:
        st.info("Aucune intervention trouvée.")
    else:
        df_display = df.drop(columns=["id"])
        st.dataframe(df_display, width="stretch", hide_index=True)

    st.divider()

    st.subheader("⚡ Actions rapides")

    tab_add, tab_done, tab_export = st.tabs([
        "➕ Ajouter une intervention",
        "✅ Terminer une mission",
        "📤 Exporter le planning"
    ])

    with tab_add:
        with st.form("form_add_intervention"):
            c1, c2, c3 = st.columns(3)

            with c1:
                date = st.text_input("Date", value=datetime.now().strftime("%d/%m/%Y"))
                heure = st.text_input("Heure", value="08:00")

            with c2:
                equipe_new = st.text_input("Équipe", value="Équipe Logistique")
                statut_new = st.selectbox("Statut initial", ["Planifiée", "En cours", "Terminée"], key="planning_add_statut")

            with c3:
                lieu = st.text_input("Lieu")
                vehicule = st.text_input("Véhicule", value="Aucun")

            mission = st.text_input("Mission")

            submitted = st.form_submit_button("Ajouter l’intervention", width="stretch")

            if submitted:
                if not mission.strip():
                    st.error("La mission est obligatoire.")
                elif not equipe_new.strip():
                    st.error("L’équipe est obligatoire.")
                else:
                    add_intervention(
                        date.strip(),
                        heure.strip(),
                        equipe_new.strip(),
                        mission.strip(),
                        lieu.strip(),
                        vehicule.strip(),
                        statut_new,
                    )
                    st.success("Intervention ajoutée avec succès.")
                    st.rerun()

    with tab_done:
        df_todo = load_planning(equipe, "Tous")
        df_todo = df_todo[df_todo["statut"] != "Terminée"]

        if df_todo.empty:
            st.info("Aucune mission à clôturer.")
        else:
            st.write("Coche une ou plusieurs missions, puis clique sur le bouton de clôture.")

            selected_ids = []

            for _, row in df_todo.iterrows():
                label = (
                    f"{row['date']} - {row['heure']} | "
                    f"{row['equipe']} | {row['mission']} | "
                    f"{row['lieu'] or '-'} | Statut : {row['statut']}"
                )

                checked = st.checkbox(label, key=f"finish_mission_{row['id']}")

                if checked:
                    selected_ids.append(row["id"])

            if st.button("✅ Marquer les missions sélectionnées comme terminées", width="stretch"):
                if not selected_ids:
                    st.warning("Sélectionne au moins une mission.")
                else:
                    user_email = user.get("email", "admin")
                    terminer_missions(selected_ids, user_email)
                    st.success(f"{len(selected_ids)} mission(s) clôturée(s) avec succès.")
                    st.rerun()

    with tab_export:
        if df.empty:
            st.info("Aucune donnée à exporter.")
        else:
            csv_data = df.drop(columns=["id"]).to_csv(index=False).encode("utf-8")

            st.download_button(
                "📤 Télécharger planning_equipes.csv",
                data=csv_data,
                file_name="planning_equipes.csv",
                mime="text/csv",
                width="stretch",
                key="download_planning_equipes",
            )

    st.divider()

    st.subheader("📌 Résumé")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Missions affichées", len(df))

    with c2:
        st.metric("En cours", int((df["statut"] == "En cours").sum()) if not df.empty else 0)

    with c3:
        st.metric("Planifiées", int((df["statut"] == "Planifiée").sum()) if not df.empty else 0)

    with c4:
        st.metric("Terminées", int((df["statut"] == "Terminée").sum()) if not df.empty else 0)



