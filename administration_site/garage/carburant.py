# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from .db import connect, init_db, load_table
from .vehicules import load_vehicules


def add_carburant(data: dict) -> None:
    init_db()

    litres = float(data.get("litres") or 0)
    prix_litre = float(data.get("prix_litre") or 0)
    montant_total = float(data.get("montant_total") or 0)

    if montant_total <= 0 and litres > 0 and prix_litre > 0:
        montant_total = litres * prix_litre

    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO vehicule_carburants (
                vehicule_id,
                date_plein,
                kilometrage,
                type_carburant,
                litres,
                prix_litre,
                montant_total,
                station,
                conducteur
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(data.get("vehicule_id")),
                data.get("date_plein"),
                int(data.get("kilometrage") or 0),
                data.get("type_carburant"),
                litres,
                prix_litre,
                montant_total,
                data.get("station"),
                data.get("conducteur"),
            ),
        )

        if int(data.get("kilometrage") or 0) > 0:
            conn.execute(
                """
                UPDATE vehicules
                SET kilometrage_actuel=MAX(COALESCE(kilometrage_actuel, 0), ?),
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (
                    int(data.get("kilometrage") or 0),
                    int(data.get("vehicule_id")),
                ),
            )

        conn.commit()
    finally:
        conn.close()


def delete_carburant(carburant_id: int) -> None:
    init_db()

    conn = connect()
    try:
        conn.execute("DELETE FROM vehicule_carburants WHERE id=?", (int(carburant_id),))
        conn.commit()
    finally:
        conn.close()


def render_carburant() -> None:
    st.markdown("### ⛽ Suivi carburant")

    vehicules = load_vehicules()

    if not vehicules:
        st.info("Ajoute d'abord un véhicule.")
        return

    options = {
        f"{v.get('immatriculation') or 'Sans immat'} — {v.get('marque') or ''} {v.get('modele') or ''}": v["id"]
        for v in vehicules
    }

    with st.expander("➕ Ajouter un plein", expanded=False):
        with st.form("garage_carburant_add_form"):
            c1, c2 = st.columns(2)

            with c1:
                selected = st.selectbox("Véhicule", list(options.keys()))
                date_plein = st.date_input("Date du plein", value=date.today())
                kilometrage = st.number_input("Kilométrage", min_value=0, step=100)
                type_carburant = st.selectbox(
                    "Type carburant",
                    ["", "Essence", "Diesel", "Électrique", "GPL", "AdBlue", "Autre"],
                )

            with c2:
                litres = st.number_input("Litres", min_value=0.0, step=1.0, format="%.2f")
                prix_litre = st.number_input("Prix / litre", min_value=0.0, step=0.01, format="%.3f")
                montant_total = st.number_input("Montant total", min_value=0.0, step=1.0, format="%.2f")
                station = st.text_input("Station")
                conducteur = st.text_input("Conducteur")

            submitted = st.form_submit_button("💾 Enregistrer le plein", width="stretch")

        if submitted:
            try:
                add_carburant(
                    {
                        "vehicule_id": options[selected],
                        "date_plein": date_plein.isoformat(),
                        "kilometrage": int(kilometrage),
                        "type_carburant": type_carburant,
                        "litres": float(litres),
                        "prix_litre": float(prix_litre),
                        "montant_total": float(montant_total),
                        "station": station,
                        "conducteur": conducteur,
                    }
                )
                st.success("Plein ajouté.")
                st.rerun()
            except Exception as exc:
                st.error("Erreur pendant l'ajout du plein.")
                st.exception(exc)

    st.divider()

    df = load_table("vehicule_carburants")

    if df.empty:
        st.warning("Aucun plein enregistré.")
        return

    veh_df = pd.DataFrame(load_vehicules(include_inactive=True))
    if not veh_df.empty:
        veh_df = veh_df[["id", "immatriculation", "marque", "modele"]].rename(columns={"id": "vehicule_id"})
        df = df.merge(veh_df, on="vehicule_id", how="left")

    df["vehicule"] = (
        df.get("immatriculation", "").fillna("").astype(str)
        + " — "
        + df.get("marque", "").fillna("").astype(str)
        + " "
        + df.get("modele", "").fillna("").astype(str)
    )

    c1, c2, c3, c4 = st.columns(4)

    total_litres = float(df["litres"].fillna(0).sum()) if "litres" in df else 0
    total_montant = float(df["montant_total"].fillna(0).sum()) if "montant_total" in df else 0
    prix_moyen = total_montant / total_litres if total_litres > 0 else 0

    c1.metric("Pleins", len(df))
    c2.metric("Litres", f"{total_litres:.2f}")
    c3.metric("Montant", f"{total_montant:.2f} €")
    c4.metric("Prix moyen", f"{prix_moyen:.3f} €/L")

    display_cols = [
        "id",
        "date_plein",
        "vehicule",
        "kilometrage",
        "type_carburant",
        "litres",
        "prix_litre",
        "montant_total",
        "station",
        "conducteur",
    ]
    display_cols = [c for c in display_cols if c in df.columns]

    st.dataframe(
        df.sort_values("id", ascending=False)[display_cols],
        width="stretch",
        hide_index=True,
    )

    with st.expander("🗑️ Supprimer un plein", expanded=False):
        ids = df.sort_values("id", ascending=False)["id"].tolist()
        selected_id = st.selectbox("ID du plein à supprimer", ids)
        confirm = st.checkbox("Je confirme la suppression du plein")

        if st.button("Supprimer ce plein", disabled=not confirm, width="stretch"):
            delete_carburant(int(selected_id))
            st.success("Plein supprimé.")
            st.rerun()

# ============================================================
# Compatibilité navigation Streamlit
# Patch 104
# Le routeur peut appeler render() ou show()
# ============================================================

def render(*args, **kwargs):
    """
    Point d'entrée standard attendu par le routeur Garage.
    """
    return render_carburant()

def show(*args, **kwargs):
    """
    Alias de compatibilité pour les anciens routeurs.
    """
    return render(*args, **kwargs)

