# pages/08_Planning_Equipes.py
"""
Page Planning Équipes
Vue simple du planning des interventions pour les équipes internes.
"""

from datetime import datetime
import pandas as pd
import streamlit as st


def show() -> None:
    st.title("📅 Planning Équipes")
    st.caption("Organisation des interventions et suivi opérationnel")

    user = st.session_state.user
    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    role = user.get("role")
    if role not in ["admin", "interne", "equipe_interne"]:
        st.error("Accès réservé aux équipes internes et administrateurs.")
        st.stop()

    col1, col2, col3 = st.columns(3)
    with col1:
        equipe = st.selectbox(
            "Équipe",
            ["Toutes", "Équipe Alpha", "Équipe Beta", "Équipe Technique", "Équipe Logistique"]
        )
    with col2:
        periode = st.selectbox(
            "Période",
            ["Aujourd'hui", "Cette semaine", "Ce mois"]
        )
    with col3:
        statut = st.selectbox(
            "Statut",
            ["Tous", "Planifiée", "En cours", "Terminée"]
        )

    planning_data = [
        {
            "Date": "21/04/2026",
            "Heure": "08:00",
            "Équipe": "Équipe Alpha",
            "Mission": "Montage barnum",
            "Lieu": "Salle des Fêtes",
            "Véhicule": "Renault Master",
            "Statut": "Planifiée",
        },
        {
            "Date": "21/04/2026",
            "Heure": "13:30",
            "Équipe": "Équipe Beta",
            "Mission": "Livraison chaises et tables",
            "Lieu": "Parc communal",
            "Véhicule": "Peugeot Boxer",
            "Statut": "En cours",
        },
        {
            "Date": "22/04/2026",
            "Heure": "09:00",
            "Équipe": "Équipe Technique",
            "Mission": "Installation sonorisation",
            "Lieu": "Place de l'Église",
            "Véhicule": "Citroën Jumper",
            "Statut": "Planifiée",
        },
        {
            "Date": "23/04/2026",
            "Heure": "14:00",
            "Équipe": "Équipe Logistique",
            "Mission": "Contrôle inventaire",
            "Lieu": "Entrepôt A",
            "Véhicule": "Aucun",
            "Statut": "Terminée",
        },
    ]

    df = pd.DataFrame(planning_data)

    if equipe != "Toutes":
        df = df[df["Équipe"] == equipe]

    if statut != "Tous":
        df = df[df["Statut"] == statut]

    st.subheader("📋 Planning des interventions")
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.subheader("⚡ Actions rapides")
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        if st.button("➕ Ajouter une intervention", use_container_width=True):
            st.success("Formulaire d'ajout d'intervention à connecter à la base de données.")

    with col_b:
        if st.button("✅ Marquer une mission terminée", use_container_width=True):
            st.success("Action de clôture à relier au planning réel.")

    with col_c:
        if st.button("📤 Exporter le planning", use_container_width=True):
            csv_data = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Télécharger planning_equipes.csv",
                data=csv_data,
                file_name="planning_equipes.csv",
                mime="text/csv",
                use_container_width=True,
                key="download_planning_equipes",
            )

    st.subheader("📌 Résumé")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Missions affichées", len(df))
    with c2:
        st.metric("En cours", len(df[df["Statut"] == "En cours"]))
    with c3:
        st.metric("Planifiées", len(df[df["Statut"] == "Planifiée"]))

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
