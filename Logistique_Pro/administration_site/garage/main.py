# -*- coding: utf-8 -*-
from __future__ import annotations

import streamlit as st
import importlib

from .alertes import render_alertes
from .attributions import render_attributions
from .carburant import render_carburant
from .dashboard import render_dashboard
from .db import DB_PATH, init_db, list_columns, list_tables
from .entretiens import render_entretiens
from .export import render_export
from .import_csv import render_import_csv
from .kilometrage import render_kilometrage
from .recherche import render_recherche
from .vehicules import render_ajouter, render_liste, render_modifier_supprimer



def _patch79_render_garage_module(module_name: str) -> None:
    try:
        module = importlib.import_module(module_name)
        if hasattr(module, "render"):
            try:
                module.render(show_title=False)
            except TypeError:
                module.render()
        elif hasattr(module, "show"):
            module.show()
        else:
            st.error(f"Le module `{module_name}` ne contient pas render() ou show().")
    except Exception as exc:
        st.error(f"Erreur pendant le chargement du module `{module_name}` : {exc}")

def render_debug() -> None:
    with st.expander("🔧 Diagnostic base Garage", expanded=False):
        st.write(f"**Base utilisée :** `{DB_PATH}`")
        st.write(f"**Existe :** `{DB_PATH.exists()}`")
        st.write("**Tables :**", list_tables())
        st.write("**Colonnes véhicules :**", list_columns("vehicules"))


def render() -> None:
    init_db()

    # PATCH66B_DISABLED_DUPLICATE_TITLE: st.subheader("🚗 Garage / Véhicules")
    st.caption("Connecté à la vraie base : data/garage_vehicules.db")

    render_debug()

    tabs = st.tabs(
        [
            "📊 Tableau de bord",
            "🔎 Recherche",
            "📋 Liste véhicules",
            "➕ Ajouter",
            "✏️ Modifier / Supprimer",
            "📈 Kilométrage",
            "⛽ Carburant",
            "🛠️ Entretiens",
            "👤 Attributions",
            "🚨 Alertes",
            "📤 Import CSV",
            "📥 Export",
        ]
    )

    with tabs[0]:
        render_dashboard()

    with tabs[1]:
        render_recherche()

    with tabs[2]:
        render_liste()

    with tabs[3]:
        render_ajouter()

    with tabs[4]:
        render_modifier_supprimer()

    with tabs[5]:
        render_kilometrage()

    with tabs[6]:
        render_carburant()

    with tabs[7]:
        render_entretiens()

    with tabs[8]:
        render_attributions()

    with tabs[9]:
        render_alertes()

    with tabs[10]:
        render_import_csv()

    with tabs[11]:
        render_export()


def show() -> None:
    render(show_title=True)



def render(show_title: bool = True) -> None:
    if show_title:
        st.markdown("### 🚗 Garage / Véhicules")
        st.caption("Gestion du parc véhicules : kilométrage, carburant, entretiens, attributions et exports.")

    modules = {
        "📋 Liste véhicules": "administration_site.garage.vehicules",
        "➕ Ajouter": "administration_site.garage.vehicules",
        "✏️ Modifier / Supprimer": "administration_site.garage.vehicules",
        "📈 Kilométrage": "administration_site.garage.kilometrage",
        "⛽ Carburant": "administration_site.garage.carburant",
        "🛠️ Entretiens": "administration_site.garage.entretiens",
        "👤 Attributions": "administration_site.garage.attributions",
        "📸 Photos": "administration_site.garage.photos",
        "🔍 Recherche": "administration_site.garage.recherche",
        "🚨 Alertes": "administration_site.garage.alertes",
        "📥 Import CSV": "administration_site.garage.import_csv",
        "📤 Export": "administration_site.garage.export",
    }

    selected = st.radio(
        "Module Garage",
        list(modules.keys()),
        horizontal=True,
        label_visibility="collapsed",
        key="patch79_garage_module",
    )

    st.divider()
    # PATCH103_DISABLED_DUPLICATE_MODULE_TITLE: st.markdown(f"### {selected}")
    module_name = modules[selected]
    module = None

    try:
        module = importlib.import_module(module_name)

        # Compatibilité spéciale pour vehicules.py si les fonctions dédiées existent.
        if module_name.endswith(".vehicules"):
            if selected.startswith("📋") and hasattr(module, "render_liste"):
                module.render_liste()
                return
            if selected.startswith("➕") and hasattr(module, "render_ajouter"):
                module.render_ajouter()
                return
            if selected.startswith("✏️") and hasattr(module, "render_modifier_supprimer"):
                module.render_modifier_supprimer()
                return

        if hasattr(module, "render"):
            try:
                module.render(show_title=False)
            except TypeError:
                module.render()
        elif hasattr(module, "show"):
            module.show()
        else:
            st.error(f"Le module `{module_name}` ne contient pas render() ou show().")

    except Exception as exc:
        st.error(f"Erreur pendant le chargement du module `{module_name}` : {exc}")
