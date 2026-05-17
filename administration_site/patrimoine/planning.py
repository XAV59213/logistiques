# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
import streamlit as st

from .controles import load_controles
from .entretiens import load_entretiens
from .db import get_db_path


def _clean(value: Any) -> str:
    if value is None:
        return ""
    value = str(value)
    if value.lower() in ["none", "nan", "nat"]:
        return ""
    return value.strip()


def _to_date(value: Any):
    value = _clean(value)

    if not value:
        return None

    try:
        parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
        if pd.isna(parsed):
            return None
        return parsed.date()
    except Exception:
        return None


def _format_date(value: Any) -> str:
    d = _to_date(value)
    if not d:
        return _clean(value)
    return d.strftime("%d/%m/%Y")


def _is_closed(value: Any) -> bool:
    value = _clean(value).lower()

    closed = [
        "réalisé",
        "realise",
        "réalisée",
        "realisee",
        "terminé",
        "termine",
        "terminée",
        "terminee",
        "annulé",
        "annule",
        "annulée",
        "annulee",
        "clos",
        "clôturé",
        "cloture",
    ]

    return value in closed



def _download_key(prefix: str, df: pd.DataFrame) -> str:
    try:
        size = len(df)
    except Exception:
        size = 0
    return f"{prefix}_{size}_{datetime.now().strftime('%H%M%S%f')}"


def _status_from_date(d) -> str:
    if not d:
        return "Sans date"

    today = date.today()

    if d < today:
        return "🔴 En retard"

    if d == today:
        return "🟡 Aujourd'hui"

    if d <= today + timedelta(days=30):
        return "🟠 À venir 30j"

    return "🟢 Planifié"


def build_planning() -> pd.DataFrame:
    rows = []

    controles = load_controles()

    if not controles.empty:
        for _, row in controles.iterrows():
            statut = _clean(row.get("statut"))

            if _is_closed(statut):
                continue

            d = _to_date(row.get("date_prochain") or row.get("date_intervention") or row.get("date_debut"))

            rows.append(
                {
                    "date": d,
                    "date_affichee": d.strftime("%d/%m/%Y") if d else "",
                    "type_suivi": "Contrôle",
                    "categorie": _clean(row.get("type_controle") or row.get("domaine")),
                    "detail": _clean(row.get("detail_controle") or row.get("libelle_prestation")),
                    "batiment": _clean(row.get("batiment_nom") or row.get("nom_site")),
                    "organisme_fournisseur": _clean(row.get("organisme")),
                    "statut": statut,
                    "etat_planning": _status_from_date(d),
                    "source_id": _clean(row.get("id")),
                }
            )

    entretiens = load_entretiens()

    if not entretiens.empty:
        for _, row in entretiens.iterrows():
            statut = _clean(row.get("statut"))

            if _is_closed(statut):
                continue

            d = _to_date(row.get("date_prochain") or row.get("date_entretien"))

            rows.append(
                {
                    "date": d,
                    "date_affichee": d.strftime("%d/%m/%Y") if d else "",
                    "type_suivi": "Entretien",
                    "categorie": _clean(row.get("type_entretien")),
                    "detail": _clean(row.get("commentaire")),
                    "batiment": _clean(row.get("batiment_nom")),
                    "organisme_fournisseur": _clean(row.get("fournisseur")),
                    "statut": statut,
                    "etat_planning": _status_from_date(d),
                    "source_id": _clean(row.get("id")),
                }
            )

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    df["_sort_date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values(["_sort_date", "type_suivi", "batiment"], na_position="last")

    return df


def _filter_planning(df: pd.DataFrame, horizon_days: int, type_filter: str, status_filter: str, search: str) -> pd.DataFrame:
    if df.empty:
        return df

    filtered = df.copy()
    today = date.today()
    limit = today + timedelta(days=horizon_days)

    filtered = filtered[
        filtered["date"].notna()
        & (filtered["date"] <= limit)
    ]

    if type_filter != "Tous":
        filtered = filtered[filtered["type_suivi"] == type_filter]

    if status_filter != "Tous":
        filtered = filtered[filtered["etat_planning"] == status_filter]

    if search:
        q = search.lower()
        mask = pd.Series(False, index=filtered.index)

        for col in filtered.columns:
            mask = mask | filtered[col].astype(str).str.lower().str.contains(q, na=False)

        filtered = filtered[mask]

    return filtered


def render_synthese(df: pd.DataFrame) -> None:
    st.markdown("### 📊 Synthèse planning")

    if df.empty:
        st.info("Aucun élément de planning.")
        return

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total", len(df))
    c2.metric("Contrôles", int((df["type_suivi"] == "Contrôle").sum()))
    c3.metric("Entretiens", int((df["type_suivi"] == "Entretien").sum()))
    c4.metric("En retard", int((df["etat_planning"] == "🔴 En retard").sum()))

    c5, c6, c7, c8 = st.columns(4)

    c5.metric("Aujourd'hui", int((df["etat_planning"] == "🟡 Aujourd'hui").sum()))
    c6.metric("À venir 30j", int((df["etat_planning"] == "🟠 À venir 30j").sum()))
    c7.metric("Planifiés", int((df["etat_planning"] == "🟢 Planifié").sum()))
    c8.metric("Bâtiments concernés", df["batiment"].replace("", pd.NA).dropna().nunique())


def render_table(df: pd.DataFrame) -> None:
    st.markdown("### 📅 Planning global")

    if df.empty:
        st.info("Aucun élément à afficher.")
        return

    display = df.copy()

    cols = [
        "date_affichee",
        "etat_planning",
        "type_suivi",
        "batiment",
        "categorie",
        "detail",
        "organisme_fournisseur",
        "statut",
        "source_id",
    ]

    cols = [c for c in cols if c in display.columns]

    display = display[cols].rename(
        columns={
            "date_affichee": "Date",
            "etat_planning": "État",
            "type_suivi": "Type",
            "batiment": "Bâtiment",
            "categorie": "Catégorie",
            "detail": "Détail",
            "organisme_fournisseur": "Organisme / fournisseur",
            "statut": "Statut",
            "source_id": "ID",
        }
    )

    st.dataframe(display, width="stretch", hide_index=True)

    st.download_button(
        "📥 Export CSV planning",
        data=display.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"planning_patrimoine_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        width="stretch",
        key=_download_key("planning_csv", display),
    )


def render_par_mois(df: pd.DataFrame) -> None:
    st.markdown("### 🗓️ Vue par mois")

    if df.empty:
        st.info("Aucun élément à afficher.")
        return

    work = df.copy()
    work = work[work["date"].notna()].copy()

    if work.empty:
        st.info("Aucun élément daté.")
        return

    work["mois"] = work["date"].apply(lambda d: d.strftime("%Y-%m"))

    months = sorted(work["mois"].unique().tolist())

    for month in months:
        month_df = work[work["mois"] == month].copy()

        with st.expander(f"{month} — {len(month_df)} élément(s)", expanded=False):
            render_table(month_df)


def render_par_batiment(df: pd.DataFrame) -> None:
    st.markdown("### 🏢 Vue par bâtiment")

    if df.empty:
        st.info("Aucun élément à afficher.")
        return

    work = df.copy()
    work["batiment"] = work["batiment"].replace("", "Non renseigné")

    bats = sorted(work["batiment"].unique().tolist())

    for bat in bats:
        bat_df = work[work["batiment"] == bat].copy()

        with st.expander(f"{bat} — {len(bat_df)} élément(s)", expanded=False):
            render_table(bat_df)


def render() -> None:
    st.markdown("### 🗓️ Planning patrimoine bâti")
    st.caption(f"Base : {get_db_path()}")

    df = build_planning()

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        horizon = st.selectbox(
            "Horizon",
            [30, 60, 90, 180, 365, 730],
            index=2,
            format_func=lambda x: f"{x} jours",
        )

    with c2:
        type_filter = st.selectbox("Type", ["Tous", "Contrôle", "Entretien"])

    with c3:
        statuses = ["Tous"]

        if not df.empty:
            statuses += sorted(df["etat_planning"].dropna().unique().tolist())

        status_filter = st.selectbox("État", statuses)

    with c4:
        search = st.text_input("Recherche")

    filtered = _filter_planning(df, horizon, type_filter, status_filter, search)

    tabs = st.tabs(
        [
            "📊 Synthèse",
            "📅 Planning",
            "🗓️ Par mois",
            "🏢 Par bâtiment",
        ]
    )

    with tabs[0]:
        render_synthese(filtered)

    with tabs[1]:
        render_table(filtered)

    with tabs[2]:
        render_par_mois(filtered)

    with tabs[3]:
        render_par_batiment(filtered)


def show() -> None:
    render()
