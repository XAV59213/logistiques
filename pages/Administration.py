# -*- coding: utf-8 -*-
"""
Page Administration Site

Version propre :
- compatible avec l'application principale via show()
- charge un seul module administration à la fois
- stoppe l'affichage après la page pour éviter le bloc parasite Utilisateurs
"""

from __future__ import annotations

import importlib
import traceback

import streamlit as st

# PATCH66_NO_ROUTER_DUPLICATE_TITLE
# Les modules Administration affichent eux-mêmes leur titre.
# Le routeur ne doit donc pas réafficher le titre de l'onglet sélectionné.


MODULES = {
    "🎨 Thème & identité": ("theme_identite", "🎨 Thème & identité"),
    "👥 Utilisateurs": ("gestion_utilisateurs", "👥 Utilisateurs"),
    "✅ Validation comptes": ("validation_comptes", "✅ Validation comptes"),
    "📦 Articles / Catégories": ("articles_categories", "📦 Articles / Catégories"),
    "📋 Inventaire": ("inventaire", "📋 Inventaire"),
    "🚗 Garage / Véhicules": ("garage_vehicules", "🚗 Garage / Véhicules"),
    "🏢 Patrimoine bâti": ("patrimoine_bati", "🏢 Patrimoine bâti"),
    "🧾 Facturation": ("parametres_facturation", "🧾 Facturation"),
    "❓ Aide": ("aide_administration", "❓ Aide"),
}



def _patch79_render_admin_module(module_name: str) -> None:
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

def _render_module(module_name: str, title: str) -> None:
    try:
        module = importlib.import_module(f"administration_site.{module_name}")
    except Exception as exc:
        st.error(f"Impossible de charger le module : administration_site.{module_name}")
        with st.expander("Voir le détail de l'erreur"):
            st.code("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
        return

    render_func = getattr(module, "render", None)
    show_func = getattr(module, "show", None)

    try:
        if callable(render_func):
            render_func()
        elif callable(show_func):
            show_func()
        else:
            st.warning(f"Le module {module_name} ne contient pas render() ou show().")
    except Exception as exc:
        st.error(f"Erreur pendant l'affichage du module : {title}")
        with st.expander("Voir le détail de l'erreur"):
            st.code("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))


def render_administration() -> None:
    st.title("⚙️ Administration du site")
    st.caption(
        "Administration centralisée : identité visuelle, utilisateurs, "
        "inventaire, patrimoine, garage et paramètres."
    )

    labels = list(MODULES.keys())

    choix = st.radio(
        "Section administration",
        labels,
        horizontal=True,
        label_visibility="collapsed",
        key="admin_site_section",
    )

    st.divider()

    module_name, title = MODULES[choix]
    st.markdown(f"## {title}")
    _render_module(module_name, title)


def show() -> None:
    render_administration()
    st.stop()


def render() -> None:
    render_administration()
    st.stop()


if __name__ == "__main__":
    render_administration()



def show() -> None:
    st.title("⚙️ Administration du site")
    st.caption("Administration centralisée : identité visuelle, utilisateurs, inventaire, patrimoine, garage et paramètres.")

    user = st.session_state.get("user")
    if not user or str(user.get("role", "")).lower() != "admin":
        st.error("Accès réservé aux administrateurs.")
        st.stop()

    modules = {
        "🎨 Thème & identité": "administration_site.theme_identite",
        "👥 Utilisateurs": "administration_site.gestion_utilisateurs",
        "✅ Comptes de validation": "administration_site.validation_comptes",
        "📦 Articles / Catégories": "administration_site.articles_categories",
        "📋 Inventaire": "administration_site.inventaire",
        "🚗 Garage / Véhicules": "administration_site.garage.main",
        "🏢 Patrimoine bâti": "administration_site.patrimoine.main",
        "🧾 Facturation": "administration_site.parametres_facturation",
        "❓ Aide": "administration_site.aide_administration",
    }

    selected = st.radio(
        "Module Administration",
        list(modules.keys()),
        horizontal=True,
        label_visibility="collapsed",
        key="patch79_admin_site_module",
    )

    st.divider()

    st.markdown(f"### {selected}")
    _patch79_render_admin_module(modules[selected])
