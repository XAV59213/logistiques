# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
import streamlit as st

from .batiments import load_batiments
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


def _is_closed_status(value: Any) -> bool:
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


def _prepare_controles() -> pd.DataFrame:
    df = load_controles()

    if df.empty:
        return df

    df = df.copy()

    if "date_prochain" not in df.columns:
        df["date_prochain"] = ""

    if "statut" not in df.columns:
        df["statut"] = ""

    if "type_controle" not in df.columns:
        df["type_controle"] = ""

    if "detail_controle" not in df.columns:
        df["detail_controle"] = ""

    if "batiment_nom" not in df.columns:
        df["batiment_nom"] = "Non lié"

    df["_date"] = df["date_prochain"].apply(_to_date)
    df["_date_affichee"] = df["date_prochain"].apply(_format_date)
    df["_ferme"] = df["statut"].apply(_is_closed_status)

    return df


def _prepare_entretiens() -> pd.DataFrame:
    df = load_entretiens()

    if df.empty:
        return df

    df = df.copy()

    if "date_prochain" not in df.columns:
        df["date_prochain"] = ""

    if "statut" not in df.columns:
        df["statut"] = ""

    if "type_entretien" not in df.columns:
        df["type_entretien"] = ""

    if "batiment_nom" not in df.columns:
        df["batiment_nom"] = "Non lié"

    df["_date"] = df["date_prochain"].apply(_to_date)
    df["_date_affichee"] = df["date_prochain"].apply(_format_date)
    df["_ferme"] = df["statut"].apply(_is_closed_status)

    return df


def _filter_alerts(df: pd.DataFrame, horizon_days: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    if df.empty or "_date" not in df.columns:
        return pd.DataFrame(), pd.DataFrame()

    today = date.today()
    limit = today + timedelta(days=horizon_days)

    active = df[~df["_ferme"]].copy()

    overdue = active[
        active["_date"].notna()
        & (active["_date"] < today)
    ].copy()

    upcoming = active[
        active["_date"].notna()
        & (active["_date"] >= today)
        & (active["_date"] <= limit)
    ].copy()

    overdue = overdue.sort_values("_date")
    upcoming = upcoming.sort_values("_date")

    return overdue, upcoming


def _batiments_without_items(batiments: pd.DataFrame, linked_df: pd.DataFrame, label: str) -> pd.DataFrame:
    if batiments.empty:
        return pd.DataFrame()

    if linked_df.empty or "batiment_id" not in linked_df.columns:
        result = batiments.copy()
    else:
        linked_ids = (
            pd.to_numeric(linked_df["batiment_id"], errors="coerce")
            .dropna()
            .astype(int)
            .unique()
            .tolist()
        )

        result = batiments[
            ~pd.to_numeric(batiments["id"], errors="coerce").fillna(-1).astype(int).isin(linked_ids)
        ].copy()

    if result.empty:
        return result

    result["alerte"] = label

    cols = ["id", "nom", "type_batiment", "ville", "alerte"]
    cols = [c for c in cols if c in result.columns]

    return result[cols]


def _display_alert_table(df: pd.DataFrame, kind: str) -> None:
    if df.empty:
        st.success("Aucune alerte dans cette catégorie.")
        return

    display = df.copy()

    if kind == "controle":
        cols = [
            "id",
            "batiment_nom",
            "type_controle",
            "detail_controle",
            "_date_affichee",
            "organisme",
            "statut",
        ]
        rename = {
            "id": "ID",
            "batiment_nom": "Bâtiment",
            "type_controle": "Domaine",
            "detail_controle": "Prestation",
            "_date_affichee": "Date prévue",
            "organisme": "Organisme",
            "statut": "Statut",
        }
    else:
        cols = [
            "id",
            "batiment_nom",
            "type_entretien",
            "_date_affichee",
            "fournisseur",
            "montant",
            "statut",
        ]
        rename = {
            "id": "ID",
            "batiment_nom": "Bâtiment",
            "type_entretien": "Entretien",
            "_date_affichee": "Date prévue",
            "fournisseur": "Fournisseur",
            "montant": "Montant",
            "statut": "Statut",
        }

    cols = [c for c in cols if c in display.columns]
    display = display[cols].rename(columns=rename)

    st.dataframe(display, width="stretch", hide_index=True)


def _csv_download(df: pd.DataFrame, filename: str, label: str) -> None:
    if df.empty:
        return

    st.download_button(
        label,
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name=filename,
        mime="text/csv",
        width="stretch",
    )


def render_synthese(horizon_days: int) -> None:
    st.markdown("### 📊 Synthèse des alertes patrimoine")

    batiments = load_batiments(include_inactive=True)
    controles = _prepare_controles()
    entretiens = _prepare_entretiens()

    controles_retard, controles_avenir = _filter_alerts(controles, horizon_days)
    entretiens_retard, entretiens_avenir = _filter_alerts(entretiens, horizon_days)

    sans_controle = _batiments_without_items(
        batiments,
        controles,
        "Aucun contrôle lié",
    )

    sans_entretien = _batiments_without_items(
        batiments,
        entretiens,
        "Aucun entretien lié",
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Bâtiments", len(batiments))
    c2.metric("Contrôles en retard", len(controles_retard))
    c3.metric(f"Contrôles ≤ {horizon_days}j", len(controles_avenir))
    c4.metric("Sans contrôle", len(sans_controle))

    c5, c6, c7, c8 = st.columns(4)

    c5.metric("Entretiens", len(entretiens))
    c6.metric("Entretiens en retard", len(entretiens_retard))
    c7.metric(f"Entretiens ≤ {horizon_days}j", len(entretiens_avenir))
    c8.metric("Sans entretien", len(sans_entretien))

    st.caption(f"Base utilisée : {get_db_path()}")

    total_alerts = (
        len(controles_retard)
        + len(controles_avenir)
        + len(entretiens_retard)
        + len(entretiens_avenir)
        + len(sans_controle)
        + len(sans_entretien)
    )

    if total_alerts == 0:
        st.success("Aucune alerte patrimoine détectée.")
    else:
        st.warning(f"{total_alerts} alerte(s) patrimoine détectée(s).")


def render_controles(horizon_days: int) -> None:
    st.markdown("### ✅ Alertes contrôles bâtiments")

    controles = _prepare_controles()
    overdue, upcoming = _filter_alerts(controles, horizon_days)

    tab1, tab2, tab3 = st.tabs(
        [
            f"🔴 En retard ({len(overdue)})",
            f"🟠 À venir ({len(upcoming)})",
            "📋 Tous les contrôles",
        ]
    )

    with tab1:
        _display_alert_table(overdue, "controle")
        _csv_download(overdue, "alertes_controles_retard.csv", "📥 Export CSV contrôles en retard")

    with tab2:
        _display_alert_table(upcoming, "controle")
        _csv_download(upcoming, "alertes_controles_a_venir.csv", "📥 Export CSV contrôles à venir")

    with tab3:
        if controles.empty:
            st.info("Aucun contrôle.")
        else:
            display = controles.copy()
            display["_date_affichee"] = display["date_prochain"].apply(_format_date)

            cols = [
                "id",
                "batiment_nom",
                "type_controle",
                "detail_controle",
                "_date_affichee",
                "organisme",
                "statut",
            ]
            cols = [c for c in cols if c in display.columns]

            st.dataframe(display[cols], width="stretch", hide_index=True)
            _csv_download(display[cols], "controles_patrimoine.csv", "📥 Export CSV contrôles")


def render_entretiens(horizon_days: int) -> None:
    st.markdown("### 🛠️ Alertes entretiens bâtiments")

    entretiens = _prepare_entretiens()
    overdue, upcoming = _filter_alerts(entretiens, horizon_days)

    tab1, tab2, tab3 = st.tabs(
        [
            f"🔴 En retard ({len(overdue)})",
            f"🟠 À venir ({len(upcoming)})",
            "📋 Tous les entretiens",
        ]
    )

    with tab1:
        _display_alert_table(overdue, "entretien")
        _csv_download(overdue, "alertes_entretiens_retard.csv", "📥 Export CSV entretiens en retard")

    with tab2:
        _display_alert_table(upcoming, "entretien")
        _csv_download(upcoming, "alertes_entretiens_a_venir.csv", "📥 Export CSV entretiens à venir")

    with tab3:
        if entretiens.empty:
            st.info("Aucun entretien.")
        else:
            display = entretiens.copy()
            display["_date_affichee"] = display["date_prochain"].apply(_format_date)

            cols = [
                "id",
                "batiment_nom",
                "type_entretien",
                "_date_affichee",
                "fournisseur",
                "montant",
                "statut",
            ]
            cols = [c for c in cols if c in display.columns]

            st.dataframe(display[cols], width="stretch", hide_index=True)
            _csv_download(display[cols], "entretiens_patrimoine.csv", "📥 Export CSV entretiens")


def render_batiments_sans_suivi() -> None:
    st.markdown("### 🏢 Bâtiments sans suivi")

    batiments = load_batiments(include_inactive=True)
    controles = _prepare_controles()
    entretiens = _prepare_entretiens()

    sans_controle = _batiments_without_items(
        batiments,
        controles,
        "Aucun contrôle lié",
    )

    sans_entretien = _batiments_without_items(
        batiments,
        entretiens,
        "Aucun entretien lié",
    )

    tab1, tab2 = st.tabs(
        [
            f"Sans contrôle ({len(sans_controle)})",
            f"Sans entretien ({len(sans_entretien)})",
        ]
    )

    with tab1:
        if sans_controle.empty:
            st.success("Tous les bâtiments ont au moins un contrôle lié.")
        else:
            st.dataframe(sans_controle, width="stretch", hide_index=True)
            _csv_download(sans_controle, "batiments_sans_controle.csv", "📥 Export CSV bâtiments sans contrôle")

    with tab2:
        if sans_entretien.empty:
            st.success("Tous les bâtiments ont au moins un entretien lié.")
        else:
            st.dataframe(sans_entretien, width="stretch", hide_index=True)
            _csv_download(sans_entretien, "batiments_sans_entretien.csv", "📥 Export CSV bâtiments sans entretien")


def render_export_global(horizon_days: int) -> None:
    st.markdown("### 📥 Export global des alertes")

    batiments = load_batiments(include_inactive=True)
    controles = _prepare_controles()
    entretiens = _prepare_entretiens()

    controles_retard, controles_avenir = _filter_alerts(controles, horizon_days)
    entretiens_retard, entretiens_avenir = _filter_alerts(entretiens, horizon_days)

    sans_controle = _batiments_without_items(
        batiments,
        controles,
        "Aucun contrôle lié",
    )

    sans_entretien = _batiments_without_items(
        batiments,
        entretiens,
        "Aucun entretien lié",
    )

    alerts = []

    def add_rows(df: pd.DataFrame, categorie: str, type_suivi: str):
        if df.empty:
            return

        for _, row in df.iterrows():
            alerts.append(
                {
                    "categorie": categorie,
                    "type_suivi": type_suivi,
                    "batiment": _clean(row.get("batiment_nom") or row.get("nom")),
                    "objet": _clean(
                        row.get("type_controle")
                        or row.get("detail_controle")
                        or row.get("type_entretien")
                        or row.get("alerte")
                    ),
                    "date": _format_date(row.get("date_prochain") or row.get("_date")),
                    "statut": _clean(row.get("statut")),
                    "organisme_fournisseur": _clean(row.get("organisme") or row.get("fournisseur")),
                }
            )

    add_rows(controles_retard, "Retard", "Contrôle")
    add_rows(controles_avenir, "À venir", "Contrôle")
    add_rows(entretiens_retard, "Retard", "Entretien")
    add_rows(entretiens_avenir, "À venir", "Entretien")
    add_rows(sans_controle, "Sans suivi", "Contrôle")
    add_rows(sans_entretien, "Sans suivi", "Entretien")

    df_alerts = pd.DataFrame(alerts)

    if df_alerts.empty:
        st.success("Aucune alerte à exporter.")
        return

    st.dataframe(df_alerts, width="stretch", hide_index=True)

    _csv_download(
        df_alerts,
        f"alertes_patrimoine_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        "📥 Export CSV global des alertes",
    )


def render() -> None:
    st.markdown("### 🚨 Centre alertes patrimoine bâti")
    st.caption(f"Base : {get_db_path()}")

    c1, c2 = st.columns([1, 3])

    with c1:
        horizon_days = st.selectbox(
            "Horizon",
            [30, 60, 90, 180, 365],
            index=0,
            format_func=lambda x: f"{x} jours",
        )

    with c2:
        st.info("Les alertes utilisent les dates prévues des contrôles et entretiens non clôturés.")

    tabs = st.tabs(
        [
            "📊 Synthèse",
            "✅ Contrôles",
            "🛠️ Entretiens",
            "🏢 Sans suivi",
            "📥 Export global",
        ]
    )

    with tabs[0]:
        render_synthese(horizon_days)

    with tabs[1]:
        render_controles(horizon_days)

    with tabs[2]:
        render_entretiens(horizon_days)

    with tabs[3]:
        render_batiments_sans_suivi()

    with tabs[4]:
        render_export_global(horizon_days)


def show() -> None:
    render()
