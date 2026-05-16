# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from .db import init_db, load_table
from .entretiens import ensure_entretiens_schema
from .kilometrage import ensure_kilometrage_schema
from .attributions import ensure_attributions_schema
from .vehicules import load_vehicules


def _safe_table(table_name: str) -> pd.DataFrame:
    try:
        return load_table(table_name)
    except Exception:
        return pd.DataFrame()


def _to_date(value):
    if value is None or value == "":
        return None

    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _prepare_data():
    init_db()
    ensure_entretiens_schema()
    ensure_kilometrage_schema()
    ensure_attributions_schema()

    vehicules = pd.DataFrame(load_vehicules(include_inactive=True))
    carburants = _safe_table("vehicule_carburants")
    entretiens = _safe_table("vehicule_entretiens")
    attributions = _safe_table("vehicule_attributions")
    kilometrages = _safe_table("vehicule_kilometrages")

    if not vehicules.empty:
        if "actif" not in vehicules.columns:
            vehicules["actif"] = 1

        vehicules["actif"] = pd.to_numeric(vehicules["actif"], errors="coerce").fillna(1).astype(int)

        if "kilometrage_actuel" not in vehicules.columns:
            vehicules["kilometrage_actuel"] = 0

        vehicules["kilometrage_actuel"] = pd.to_numeric(
            vehicules["kilometrage_actuel"],
            errors="coerce",
        ).fillna(0).astype(int)

    return vehicules, carburants, entretiens, attributions, kilometrages


def _build_alerts(vehicules: pd.DataFrame, entretiens: pd.DataFrame) -> list[dict]:
    today = date.today()
    limit = today + timedelta(days=30)
    alerts = []

    if not vehicules.empty:
        for _, row in vehicules.iterrows():
            actif = int(row.get("actif") or 0)
            if actif != 1:
                continue

            vehicule = f"{row.get('immatriculation') or ''} — {row.get('marque') or ''} {row.get('modele') or ''}".strip()
            ct_date = _to_date(row.get("date_ct"))

            if ct_date:
                if ct_date < today:
                    alerts.append(
                        {
                            "niveau": "🔴 Urgent",
                            "type": "Contrôle technique dépassé",
                            "vehicule": vehicule,
                            "echeance": ct_date.isoformat(),
                            "detail": f"Dépassé depuis {(today - ct_date).days} jours",
                        }
                    )
                elif ct_date <= limit:
                    alerts.append(
                        {
                            "niveau": "🟠 À venir",
                            "type": "Contrôle technique",
                            "vehicule": vehicule,
                            "echeance": ct_date.isoformat(),
                            "detail": f"Dans {(ct_date - today).days} jours",
                        }
                    )

    if not entretiens.empty:
        veh_df = vehicules.copy()

        if not veh_df.empty:
            cols = [c for c in ["id", "immatriculation", "marque", "modele", "kilometrage_actuel"] if c in veh_df.columns]
            veh_df = veh_df[cols].rename(columns={"id": "vehicule_id"})
            entretiens = entretiens.merge(veh_df, on="vehicule_id", how="left")

        for _, row in entretiens.iterrows():
            statut = str(row.get("statut") or "")
            if statut in ["Réalisé", "Annulé"]:
                continue

            vehicule = f"{row.get('immatriculation') or ''} — {row.get('marque') or ''} {row.get('modele') or ''}".strip()
            date_prochain = _to_date(row.get("date_prochain"))

            if date_prochain and date_prochain <= limit:
                alerts.append(
                    {
                        "niveau": "🟠 À venir" if date_prochain >= today else "🔴 Urgent",
                        "type": row.get("type_entretien") or "Entretien",
                        "vehicule": vehicule,
                        "echeance": date_prochain.isoformat(),
                        "detail": f"Échéance entretien",
                    }
                )

            try:
                km_prochain = int(row.get("km_prochain") or 0)
                km_actuel = int(row.get("kilometrage_actuel") or 0)
            except Exception:
                km_prochain = 0
                km_actuel = 0

            if km_prochain > 0 and km_actuel > 0 and (km_prochain - km_actuel) <= 2000:
                alerts.append(
                    {
                        "niveau": "🟠 À venir" if km_prochain >= km_actuel else "🔴 Urgent",
                        "type": row.get("type_entretien") or "Entretien kilométrique",
                        "vehicule": vehicule,
                        "echeance": f"{km_prochain} km",
                        "detail": f"Reste {km_prochain - km_actuel} km",
                    }
                )

    return alerts


def render_dashboard() -> None:
    st.markdown("### 📊 Tableau de bord Garage")

    vehicules, carburants, entretiens, attributions, kilometrages = _prepare_data()

    if vehicules.empty:
        st.info("Aucun véhicule enregistré.")
        return

    total_vehicules = len(vehicules)
    actifs = int((vehicules["actif"] == 1).sum()) if "actif" in vehicules.columns else total_vehicules
    inactifs = total_vehicules - actifs
    km_total = int(vehicules["kilometrage_actuel"].fillna(0).sum()) if "kilometrage_actuel" in vehicules.columns else 0

    cout_carburant = 0.0
    if not carburants.empty and "montant_total" in carburants.columns:
        cout_carburant = float(pd.to_numeric(carburants["montant_total"], errors="coerce").fillna(0).sum())

    cout_entretiens = 0.0
    if not entretiens.empty and "montant" in entretiens.columns:
        cout_entretiens = float(pd.to_numeric(entretiens["montant"], errors="coerce").fillna(0).sum())

    attributions_actives = 0
    if not attributions.empty and "actif" in attributions.columns:
        attributions_actives = int(pd.to_numeric(attributions["actif"], errors="coerce").fillna(0).sum())

    alerts = _build_alerts(vehicules, entretiens)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Véhicules", total_vehicules)
    c2.metric("Actifs", actifs)
    c3.metric("Inactifs", inactifs)
    c4.metric("Alertes", len(alerts))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Kilométrage total", f"{km_total:,}".replace(",", " "))
    c6.metric("Carburant", f"{cout_carburant:.2f} €")
    c7.metric("Entretiens", f"{cout_entretiens:.2f} €")
    c8.metric("Attributions actives", attributions_actives)

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### ⚡ Alertes principales")

        if not alerts:
            st.success("Aucune alerte importante.")
        else:
            alert_df = pd.DataFrame(alerts)
            st.dataframe(alert_df.head(10), width="stretch", hide_index=True)

    with col_right:
        st.markdown("#### 🚗 Top kilométrage")

        top_cols = [c for c in ["immatriculation", "marque", "modele", "service", "kilometrage_actuel"] if c in vehicules.columns]
        top_df = vehicules[top_cols].sort_values("kilometrage_actuel", ascending=False).head(10)

        st.dataframe(top_df, width="stretch", hide_index=True)

    st.divider()

    col_energy, col_status = st.columns(2)

    with col_energy:
        st.markdown("#### ⛽ Répartition par énergie")

        if "energie" in vehicules.columns:
            energy_df = vehicules["energie"].fillna("Non renseigné").replace("", "Non renseigné").value_counts().reset_index()
            energy_df.columns = ["Énergie", "Nombre"]
            st.bar_chart(energy_df.set_index("Énergie"))
        else:
            st.info("Aucune colonne énergie.")

    with col_status:
        st.markdown("#### 📌 Répartition par statut")

        if "statut" in vehicules.columns:
            status_df = vehicules["statut"].fillna("Non renseigné").replace("", "Non renseigné").value_counts().reset_index()
            status_df.columns = ["Statut", "Nombre"]
            st.bar_chart(status_df.set_index("Statut"))
        else:
            st.info("Aucune colonne statut.")

    st.divider()

    col_service, col_cost = st.columns(2)

    with col_service:
        st.markdown("#### 🏢 Véhicules par service")

        if "service" in vehicules.columns:
            service_df = vehicules["service"].fillna("Non renseigné").replace("", "Non renseigné").value_counts().reset_index()
            service_df.columns = ["Service", "Nombre"]
            st.dataframe(service_df, width="stretch", hide_index=True)
        else:
            st.info("Aucun service renseigné.")

    with col_cost:
        st.markdown("#### 💶 Coûts synthétiques")

        cost_df = pd.DataFrame(
            [
                {"Poste": "Carburant", "Montant": cout_carburant},
                {"Poste": "Entretiens", "Montant": cout_entretiens},
                {"Poste": "Total", "Montant": cout_carburant + cout_entretiens},
            ]
        )
        st.dataframe(cost_df, width="stretch", hide_index=True)

# ============================================================
# Compatibilité navigation Streamlit
# Patch 104
# Le routeur peut appeler render() ou show()
# ============================================================

def render(*args, **kwargs):
    """
    Point d'entrée standard attendu par le routeur Garage.
    """
    return render_dashboard()

def show(*args, **kwargs):
    """
    Alias de compatibilité pour les anciens routeurs.
    """
    return render(*args, **kwargs)

