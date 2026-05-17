# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from .batiments import load_batiments
from .controles import load_controles
from .db import diagnostics, get_db_path, get_tables


def _to_date(value):
    if value is None or value == "":
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def render() -> None:
    # PATCH81_DISABLED_DASHBOARD_TITLE: st.markdown("### 📊 Tableau de bord patrimoine")
    st.caption(f"Base connectée : {get_db_path()}")

    batiments = load_batiments(include_inactive=True)
    controles = load_controles()

    if batiments.empty:
        st.info("Aucun bâtiment trouvé dans la table connectée.")
        with st.expander("🔍 Diagnostic base", expanded=True):
            st.write("Tables détectées :", get_tables())
            st.dataframe(diagnostics(), width="stretch", hide_index=True)
        return

    total = len(batiments)
    actifs = int((batiments["actif"] == 1).sum()) if "actif" in batiments.columns else total
    surface = float(pd.to_numeric(batiments["surface"], errors="coerce").fillna(0).sum()) if "surface" in batiments.columns else 0
    valeur = float(pd.to_numeric(batiments["valeur_estimee"], errors="coerce").fillna(0).sum()) if "valeur_estimee" in batiments.columns else 0

    today = date.today()
    limit = today + timedelta(days=30)

    controles_retard = 0
    controles_avenir = 0

    if not controles.empty and "date_prochain" in controles.columns:
        dates = controles["date_prochain"].apply(_to_date)
        statuts = controles["statut"].fillna("").astype(str) if "statut" in controles.columns else pd.Series([""] * len(controles))
        active = ~statuts.isin(["Réalisé", "Annulé"])
        controles_retard = int((dates.apply(lambda d: bool(d and d < today)) & active).sum())
        controles_avenir = int((dates.apply(lambda d: bool(d and today <= d <= limit)) & active).sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Bâtiments", total)
    c2.metric("Actifs", actifs)
    c3.metric("Surface totale", f"{surface:,.0f} m²".replace(",", " "))
    c4.metric("Valeur estimée", f"{valeur:,.2f} €".replace(",", " "))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Contrôles", len(controles))
    c6.metric("Contrôles retard", controles_retard)
    c7.metric("Contrôles à venir", controles_avenir)
    c8.metric("Tables", len(get_tables()))

    st.divider()

    col_alertes, col_top = st.columns(2)

    with col_alertes:
        st.markdown("#### 🚨 Contrôles proches / retard")

        if controles.empty:
            st.info("Aucun contrôle.")
        else:
            df = controles.copy()
            df["date_prochain_parsed"] = df["date_prochain"].apply(_to_date)
            alertes = df[
                df["date_prochain_parsed"].notna()
                & (df["date_prochain_parsed"] <= limit)
            ].copy()

            if alertes.empty:
                st.success("Aucune alerte contrôle.")
            else:
                cols = [c for c in ["id", "batiment_nom", "type_controle", "date_prochain", "statut"] if c in alertes.columns]
                st.dataframe(alertes[cols].head(10), width="stretch", hide_index=True)

    with col_top:
        st.markdown("#### 🏢 Bâtiments principaux")
        cols = [c for c in ["nom", "type_batiment", "ville", "surface", "etat"] if c in batiments.columns]
        st.dataframe(batiments[cols].sort_values("surface", ascending=False).head(10), width="stretch", hide_index=True)

    st.divider()

    col_type, col_etat = st.columns(2)

    with col_type:
        st.markdown("#### 🧱 Répartition par type")
        if "type_batiment" in batiments.columns:
            type_df = batiments["type_batiment"].fillna("Non renseigné").replace("", "Non renseigné").value_counts().reset_index()
            type_df.columns = ["Type", "Nombre"]
            st.bar_chart(type_df.set_index("Type"))

    with col_etat:
        st.markdown("#### 📌 Répartition par état")
        if "etat" in batiments.columns:
            etat_df = batiments["etat"].fillna("Non renseigné").replace("", "Non renseigné").value_counts().reset_index()
            etat_df.columns = ["État", "Nombre"]
            st.bar_chart(etat_df.set_index("État"))

    with st.expander("🔍 Diagnostic base Patrimoine", expanded=False):
        st.write("Tables détectées :", get_tables())
        st.dataframe(diagnostics(), width="stretch", hide_index=True)


def show() -> None:
    render()
