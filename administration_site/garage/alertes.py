# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from .db import init_db, load_table
from .entretiens import ensure_entretiens_schema
from .vehicules import load_vehicules


def _to_date(value):
    if value is None or value == "":
        return None

    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _prepare_vehicules_df() -> pd.DataFrame:
    vehicules = load_vehicules(include_inactive=True)

    if not vehicules:
        return pd.DataFrame()

    df = pd.DataFrame(vehicules)

    if "date_ct" in df.columns:
        df["date_ct_parsed"] = df["date_ct"].apply(_to_date)
    else:
        df["date_ct_parsed"] = None

    if "kilometrage_actuel" in df.columns:
        df["kilometrage_actuel"] = pd.to_numeric(df["kilometrage_actuel"], errors="coerce").fillna(0).astype(int)
    else:
        df["kilometrage_actuel"] = 0

    if "actif" in df.columns:
        df["actif"] = pd.to_numeric(df["actif"], errors="coerce").fillna(1).astype(int)
    else:
        df["actif"] = 1

    return df


def _prepare_entretiens_df() -> pd.DataFrame:
    ensure_entretiens_schema()

    df = load_table("vehicule_entretiens")

    if df.empty:
        return df

    veh_df = pd.DataFrame(load_vehicules(include_inactive=True))

    if not veh_df.empty:
        cols = [c for c in ["id", "immatriculation", "marque", "modele", "kilometrage_actuel"] if c in veh_df.columns]
        veh_df = veh_df[cols].rename(columns={"id": "vehicule_id"})
        df = df.merge(veh_df, on="vehicule_id", how="left")

    df["vehicule"] = (
        df.get("immatriculation", "").fillna("").astype(str)
        + " — "
        + df.get("marque", "").fillna("").astype(str)
        + " "
        + df.get("modele", "").fillna("").astype(str)
    )

    if "date_prochain" in df.columns:
        df["date_prochain_parsed"] = df["date_prochain"].apply(_to_date)
    else:
        df["date_prochain_parsed"] = None

    for col in ["km_prochain", "kilometrage_actuel"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        else:
            df[col] = 0

    if "statut" not in df.columns:
        df["statut"] = ""

    return df


def render_alertes() -> None:
    init_db()
    ensure_entretiens_schema()

    st.markdown("### 🚨 Alertes Garage")

    today = date.today()

    seuil_jours = st.slider(
        "Afficher les échéances dans les prochains jours",
        min_value=7,
        max_value=180,
        value=30,
        step=7,
        key="garage_alertes_seuil_jours",
    )

    seuil_km = st.slider(
        "Afficher les entretiens dans les prochains kilomètres",
        min_value=500,
        max_value=10000,
        value=2000,
        step=500,
        key="garage_alertes_seuil_km",
    )

    limite_date = today + timedelta(days=int(seuil_jours))

    veh_df = _prepare_vehicules_df()
    ent_df = _prepare_entretiens_df()

    if veh_df.empty:
        st.info("Aucun véhicule enregistré.")
        return

    ct_depasse = veh_df[
        veh_df["date_ct_parsed"].notna()
        & (veh_df["date_ct_parsed"] < today)
        & (veh_df["actif"] == 1)
    ].copy()

    ct_a_venir = veh_df[
        veh_df["date_ct_parsed"].notna()
        & (veh_df["date_ct_parsed"] >= today)
        & (veh_df["date_ct_parsed"] <= limite_date)
        & (veh_df["actif"] == 1)
    ].copy()

    inactifs = veh_df[veh_df["actif"] == 0].copy()

    entretiens_date = pd.DataFrame()
    entretiens_km = pd.DataFrame()

    if not ent_df.empty:
        ent_actifs = ent_df[~ent_df["statut"].isin(["Réalisé", "Annulé"])].copy()

        entretiens_date = ent_actifs[
            ent_actifs["date_prochain_parsed"].notna()
            & (ent_actifs["date_prochain_parsed"] <= limite_date)
        ].copy()

        entretiens_km = ent_actifs[
            (ent_actifs["km_prochain"] > 0)
            & (ent_actifs["kilometrage_actuel"] > 0)
            & ((ent_actifs["km_prochain"] - ent_actifs["kilometrage_actuel"]) <= int(seuil_km))
        ].copy()

        if not entretiens_km.empty:
            entretiens_km["km_restant"] = entretiens_km["km_prochain"] - entretiens_km["kilometrage_actuel"]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("CT dépassés", len(ct_depasse))
    c2.metric("CT à venir", len(ct_a_venir))
    c3.metric("Entretiens date", len(entretiens_date))
    c4.metric("Entretiens km", len(entretiens_km))
    c5.metric("Inactifs", len(inactifs))

    st.divider()

    with st.expander("🔴 Contrôles techniques dépassés", expanded=len(ct_depasse) > 0):
        if ct_depasse.empty:
            st.success("Aucun contrôle technique dépassé.")
        else:
            ct_depasse["retard_jours"] = ct_depasse["date_ct_parsed"].apply(lambda d: (today - d).days if d else None)
            cols = [
                "id",
                "immatriculation",
                "marque",
                "modele",
                "service",
                "date_ct",
                "retard_jours",
                "statut",
            ]
            cols = [c for c in cols if c in ct_depasse.columns]
            st.dataframe(ct_depasse[cols].sort_values("retard_jours", ascending=False), width="stretch", hide_index=True)

    with st.expander("🟠 Contrôles techniques à venir", expanded=len(ct_a_venir) > 0):
        if ct_a_venir.empty:
            st.success("Aucun contrôle technique proche.")
        else:
            ct_a_venir["jours_restants"] = ct_a_venir["date_ct_parsed"].apply(lambda d: (d - today).days if d else None)
            cols = [
                "id",
                "immatriculation",
                "marque",
                "modele",
                "service",
                "date_ct",
                "jours_restants",
                "statut",
            ]
            cols = [c for c in cols if c in ct_a_venir.columns]
            st.dataframe(ct_a_venir[cols].sort_values("jours_restants"), width="stretch", hide_index=True)

    with st.expander("🛠️ Entretiens à venir par date", expanded=len(entretiens_date) > 0):
        if entretiens_date.empty:
            st.success("Aucun entretien proche par date.")
        else:
            entretiens_date["jours_restants"] = entretiens_date["date_prochain_parsed"].apply(
                lambda d: (d - today).days if d else None
            )
            cols = [
                "id",
                "vehicule",
                "type_entretien",
                "date_prochain",
                "jours_restants",
                "fournisseur",
                "montant",
                "statut",
                "commentaire",
            ]
            cols = [c for c in cols if c in entretiens_date.columns]
            st.dataframe(entretiens_date[cols].sort_values("jours_restants"), width="stretch", hide_index=True)

    with st.expander("📈 Entretiens à venir par kilométrage", expanded=len(entretiens_km) > 0):
        if entretiens_km.empty:
            st.success("Aucun entretien proche par kilométrage.")
        else:
            cols = [
                "id",
                "vehicule",
                "type_entretien",
                "kilometrage_actuel",
                "km_prochain",
                "km_restant",
                "fournisseur",
                "statut",
                "commentaire",
            ]
            cols = [c for c in cols if c in entretiens_km.columns]
            st.dataframe(entretiens_km[cols].sort_values("km_restant"), width="stretch", hide_index=True)

    with st.expander("⚫ Véhicules inactifs / supprimés", expanded=False):
        if inactifs.empty:
            st.success("Aucun véhicule inactif.")
        else:
            cols = [
                "id",
                "immatriculation",
                "marque",
                "modele",
                "service",
                "statut",
                "updated_at",
            ]
            cols = [c for c in cols if c in inactifs.columns]
            st.dataframe(inactifs[cols], width="stretch", hide_index=True)

# ============================================================
# Compatibilité navigation Streamlit
# Patch 104
# Le routeur peut appeler render() ou show()
# ============================================================

def render(*args, **kwargs):
    """
    Point d'entrée standard attendu par le routeur Garage.
    """
    return render_alertes()

def show(*args, **kwargs):
    """
    Alias de compatibilité pour les anciens routeurs.
    """
    return render(*args, **kwargs)

