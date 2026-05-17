# -*- coding: utf-8 -*-
"""
Administration - Inventaire

PATCH 39 :
- Gestion Stock activé ;
- Inventaire QR conservé ;
- Inventaire classique désactivé s'il est instable.
"""

from __future__ import annotations

import importlib
import runpy
import traceback
from pathlib import Path

import streamlit as st


PROJECT_DIR = Path("/opt/logistique-pro")


MODULES = [
    {
        "label": "📦 Gestion Stock",
        "module": "pages.02_Gestion_Stock",
        "file": PROJECT_DIR / "pages" / "02_Gestion_Stock.py",
        "description": "Gestion complète du stock, articles et mouvements.",
        "status": "ready",
        "mode": "module",
    },
    {
        "label": "📋 Inventaire QR",
        "module": "pages.17_Inventaire_QR",
        "file": PROJECT_DIR / "pages" / "17_Inventaire_QR.py",
        "description": "Inventaire avec QR code / contrôle terrain.",
        "status": "ready",
        "mode": "legacy",
    },
    {
        "label": "📋 Inventaire classique",
        "module": "pages.Inventaire",
        "file": PROJECT_DIR / "pages" / "Inventaire.py",
        "description": "Page inventaire classique détectée mais instable dans Administration.",
        "status": "disabled",
        "mode": "info",
    },
]


def _file_state(path: Path) -> str:
    return "✅ Présent" if path.exists() else "❌ Absent"


def _run_module(module_name: str) -> None:
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        st.error(f"Impossible de charger le module : {module_name}")
        with st.expander("Voir le détail de l'erreur"):
            st.code("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
        return

    for func_name in ["show", "render", "render_page"]:
        func = getattr(module, func_name, None)
        if callable(func):
            try:
                func()
            except Exception as exc:
                st.error(f"Erreur pendant l'affichage du module : {module_name}")
                with st.expander("Voir le détail de l'erreur"):
                    st.code("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
            return

    st.warning(f"Le module {module_name} ne contient pas show(), render() ou render_page().")


def _run_legacy_page(path: Path) -> None:
    if not path.exists():
        st.error(f"Fichier introuvable : {path}")
        return

    original_set_page_config = getattr(st, "set_page_config", None)

    def _safe_set_page_config(*args, **kwargs):
        return None

    try:
        if original_set_page_config is not None:
            st.set_page_config = _safe_set_page_config

        runpy.run_path(str(path), run_name="__main__")

    except Exception as exc:
        st.error(f"Erreur pendant l'exécution de : {path.name}")
        with st.expander("Voir le détail de l'erreur"):
            st.code("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))

    finally:
        if original_set_page_config is not None:
            st.set_page_config = original_set_page_config


def render_diagnostic() -> None:
    rows = []
    for module in MODULES:
        rows.append(
            {
                "Module": module["label"],
                "Fichier": str(module["file"].relative_to(PROJECT_DIR)),
                "État": _file_state(module["file"]),
                "Statut": module["status"],
                "Description": module["description"],
            }
        )

    # PATCH76_DISABLED_ADMIN_MODULE_TITLE: st.markdown("### 🔍 Diagnostic Inventaire")
    st.dataframe(rows, width="stretch", hide_index=True)


def render(show_title: bool = True) -> None:
    if show_title:  # PATCH74B_TITLE_GUARDED
        # PATCH76_DISABLED_ADMIN_MODULE_TITLE: st.subheader("📋 Inventaire")
    st.caption("Point d'entrée sécurisé vers les modules Inventaire.")

    available = [m for m in MODULES if m["file"].exists()]

    if not available:
        st.error("Aucun module Inventaire trouvé.")
        render_diagnostic()
        return

    labels = [m["label"] for m in available]

    selected_label = st.radio(
        "Choisir le module Inventaire à ouvrir",
        labels,
        horizontal=True,
        key="admin_inventaire_choice_patch39",
    )

    selected = next(m for m in available if m["label"] == selected_label)

    with st.expander("ℹ️ Informations module", expanded=False):
        st.write(f"**Fichier :** `{selected['file']}`")
        st.write(f"**Statut :** `{selected['status']}`")
        st.write(f"**Description :** {selected['description']}")

    st.divider()

    if selected["status"] != "ready":
        st.warning("Ce module est désactivé temporairement.")
        render_diagnostic()
        return

    if selected["mode"] == "module":
        _run_module(selected["module"])
    elif selected["mode"] == "legacy":
        _run_legacy_page(selected["file"])
    else:
        render_diagnostic()


def show() -> None:
    render(show_title=True)
