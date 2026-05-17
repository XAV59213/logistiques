# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd
import streamlit as st

from .attributions import ensure_attributions_schema
from .db import init_db, load_table
from .entretiens import ensure_entretiens_schema
from .kilometrage import ensure_kilometrage_schema
from .vehicules import load_vehicules


def _safe_table(table_name: str) -> pd.DataFrame:
    try:
        return load_table(table_name)
    except Exception:
        return pd.DataFrame()


def _match_df(df: pd.DataFrame, query: str) -> pd.DataFrame:
    if df.empty or not query:
        return df

    q = query.lower().strip()
    mask = pd.Series(False, index=df.index)

    for col in df.columns:
        mask = mask | df[col].astype(str).str.lower().str.contains(q, na=False)

    return df[mask]


def _join_vehicle_name(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "vehicule_id" not in df.columns:
        return df

    vehicules = pd.DataFrame(load_vehicules(include_inactive=True))

    if vehicules.empty or "id" not in vehicules.columns:
        return df

    cols = [c for c in ["id", "immatriculation", "marque", "modele", "service"] if c in vehicules.columns]
    vehicules = vehicules[cols].rename(columns={"id": "vehicule_id"})

    merged = df.merge(vehicules, on="vehicule_id", how="left")

    merged["vehicule"] = (
        merged.get("immatriculation", "").fillna("").astype(str)
        + " — "
        + merged.get("marque", "").fillna("").astype(str)
        + " "
        + merged.get("modele", "").fillna("").astype(str)
    )

    return merged


def render_recherche() -> None:
    st.markdown("### 🔎 Recherche globale Garage")

    init_db()
    ensure_entretiens_schema()
    ensure_kilometrage_schema()
    ensure_attributions_schema()

    query = st.text_input(
        "Rechercher dans tout le module Garage",
        placeholder="immatriculation, agent, fournisseur, carburant, commentaire...",
        key="garage_global_search",
    )

    if not query.strip():
        st.info("Saisis un mot-clé pour lancer la recherche.")
        return

    vehicules = pd.DataFrame(load_vehicules(include_inactive=True))
    kilometrages = _join_vehicle_name(_safe_table("vehicule_kilometrages"))
    carburants = _join_vehicle_name(_safe_table("vehicule_carburants"))
    entretiens = _join_vehicle_name(_safe_table("vehicule_entretiens"))
    attributions = _join_vehicle_name(_safe_table("vehicule_attributions"))

    results = {
        "🚗 Véhicules": _match_df(vehicules, query),
        "📈 Kilométrages": _match_df(kilometrages, query),
        "⛽ Carburants": _match_df(carburants, query),
        "🛠️ Entretiens": _match_df(entretiens, query),
        "👤 Attributions": _match_df(attributions, query),
    }

    total = sum(len(df) for df in results.values())

    st.metric("Résultats trouvés", total)

    if total == 0:
        st.warning("Aucun résultat trouvé.")
        return

    for title, df in results.items():
        with st.expander(f"{title} — {len(df)} résultat(s)", expanded=len(df) > 0):
            if df.empty:
                st.info("Aucun résultat.")
            else:
                st.dataframe(df, width="stretch", hide_index=True)

# ============================================================
# Compatibilité navigation Streamlit
# Patch 104
# Le routeur peut appeler render() ou show()
# ============================================================

def render(*args, **kwargs):
    """
    Point d'entrée standard attendu par le routeur Garage.
    """
    return render_recherche()

def show(*args, **kwargs):
    """
    Alias de compatibilité pour les anciens routeurs.
    """
    return render(*args, **kwargs)

