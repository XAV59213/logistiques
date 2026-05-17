# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib
import traceback
from pathlib import Path

import streamlit as st


PROJECT_DIR = Path("/opt/logistique-pro")
PATRIMOINE_DIR = PROJECT_DIR / "administration_site" / "patrimoine"


MODULES = [
    {
        "label": "📊 Tableau de bord",
        "module": "administration_site.patrimoine.dashboard",
        "file": PATRIMOINE_DIR / "dashboard.py",
        "description": "Synthèse du patrimoine bâti.",
    },
    {
        "label": "🏢 Bâtiments",
        "module": "administration_site.patrimoine.batiments",
        "file": PATRIMOINE_DIR / "batiments.py",
        "description": "Gestion des bâtiments, détails et modifications.",
    },
    {
        "label": "✅ Contrôles",
        "module": "administration_site.patrimoine.controles",
        "file": PATRIMOINE_DIR / "controles.py",
        "description": "Gestion des contrôles, détails et alertes.",
    },
    {
        "label": "🛠️ Entretiens",
        "module": "administration_site.patrimoine.entretiens",
        "file": PATRIMOINE_DIR / "entretiens.py",
        "description": "Entretiens, interventions et maintenance.",
    },
    {
        "label": "📤 Imports CSV",
        "module": "administration_site.patrimoine.imports_csv",
        "file": PATRIMOINE_DIR / "imports_csv.py",
        "description": "Import de données patrimoine.",
    },

    {
        "label": "📄 Export PDF",
        "module": "administration_site.patrimoine.export_pdf",
        "file": PATRIMOINE_DIR / "export_pdf.py",
        "description": "Exports PDF des bâtiments, contrôles, entretiens et alertes.",
    },

    {
        "label": "🚨 Alertes",
        "module": "administration_site.patrimoine.alertes",
        "file": PATRIMOINE_DIR / "alertes.py",
        "description": "Centre d'alertes contrôles, entretiens et bâtiments sans suivi.",
    },

    {
        "label": "🔍 Diagnostic avancé",
        "module": "administration_site.patrimoine.diagnostic",
        "file": PATRIMOINE_DIR / "diagnostic.py",
        "description": "Diagnostic base, colonnes, images, doublons et liaisons.",
    },

    {
        "label": "🧬 Migration",
        "module": "administration_site.patrimoine.migration",
        "file": PATRIMOINE_DIR / "migration.py",
        "description": "Migration propre des anciennes tables vers des tables normalisées.",
    },

    {
        "label": "💾 Sauvegarde",
        "module": "administration_site.patrimoine.backup_restore",
        "file": PATRIMOINE_DIR / "backup_restore.py",
        "description": "Sauvegarde et restauration de la base patrimoine et des photos.",
    },

    {
        "label": "🗓️ Planning",
        "module": "administration_site.patrimoine.planning",
        "file": PATRIMOINE_DIR / "planning.py",
        "description": "Planning global des contrôles et entretiens patrimoine.",
    },

    {
        "label": "📎 Documents",
        "module": "administration_site.patrimoine.documents",
        "file": PATRIMOINE_DIR / "documents.py",
        "description": "Documents liés aux bâtiments : rapports, diagnostics, factures, plans.",
    },
]



def _patch79_render_patrimoine_module(module_name: str) -> None:
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

def _file_status(path: Path) -> str:
    return "✅ Présent" if path.exists() else "❌ Absent"


def _render_module(module_name: str) -> None:
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        st.error(f"Impossible de charger le module : {module_name}")
        with st.expander("Voir le détail de l'erreur"):
            st.code("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
        return

    for func_name in ["render", "show", "render_page"]:
        func = getattr(module, func_name, None)
        if callable(func):
            try:
                func()
            except Exception as exc:
                st.error(f"Erreur pendant l'affichage du module : {module_name}")
                with st.expander("Voir le détail de l'erreur"):
                    st.code("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
            return

    st.warning(f"Le module `{module_name}` ne contient pas render(), show() ou render_page().")


def render_diagnostic() -> None:

    rows = []
    for item in MODULES:
        rows.append(
            {
                "Onglet": item["label"],
                "Module": item["module"],
                "Fichier": str(item["file"].relative_to(PROJECT_DIR)),
                "État": _file_status(item["file"]),
                "Description": item["description"],
            }
        )

    st.dataframe(rows, width="stretch", hide_index=True)

    try:
        from .db import diagnostics, get_db_path, get_tables

        st.write(f"**Base utilisée :** `{get_db_path()}`")
        st.write("**Tables détectées :**", get_tables())
        st.dataframe(diagnostics(), width="stretch", hide_index=True)
    except Exception as exc:
        st.error(f"Diagnostic base impossible : {exc}")



def render(show_title: bool = True) -> None:
    if show_title:
        st.markdown("### 🏢 Patrimoine bâti")
        st.caption("Gestion du patrimoine, bâtiments, contrôles, entretiens, documents et sauvegardes.")

    modules = {
        "📊 Tableau de bord": "administration_site.patrimoine.dashboard",
        "🏢 Bâtiments": "administration_site.patrimoine.batiments",
        "✅ Contrôles": "administration_site.patrimoine.controles",
        "🛠️ Entretiens": "administration_site.patrimoine.entretiens",
        "📥 Imports CSV": "administration_site.patrimoine.imports_csv",
        "📄 Export PDF": "administration_site.patrimoine.export_pdf",
        "🚨 Alertes": "administration_site.patrimoine.alertes",
        "🔍 Diagnostic avancé": "administration_site.patrimoine.diagnostic",
        "🚀 Migration": "administration_site.patrimoine.migration",
        "💾 Sauvegarde": "administration_site.patrimoine.backup_restore",
        "📅 Planification": "administration_site.patrimoine.planning",
        "📎 Documents": "administration_site.patrimoine.documents",
    }

    selected = st.radio(
        "Module Patrimoine",
        list(modules.keys()),
        horizontal=True,
        label_visibility="collapsed",
        key="patch79_patrimoine_module",
    )

    st.divider()

    st.markdown(f"### {selected}")
    _patch79_render_patrimoine_module(modules[selected])


def show() -> None:
    render(show_title=True)
