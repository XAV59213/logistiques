# -*- coding: utf-8 -*-
"""
Page Inventaire

Wrapper compatible avec l'application principale.
L'application appelle show().
Le code métier est dans administration_site/inventaire.py
"""

import importlib
import traceback

import streamlit as st


def _run_module():
    try:
        module = importlib.import_module("administration_site.inventaire")
    except Exception as exc:
        st.error("Erreur de chargement du module administration_site.inventaire")
        with st.expander("Voir le détail de l'erreur"):
            st.code("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
        return

    render_func = getattr(module, "render", None)

    if callable(render_func):
        try:
            render_func()
        except Exception as exc:
            st.error("Erreur pendant l'affichage de Inventaire")
            with st.expander("Voir le détail de l'erreur"):
                st.code("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    else:
        st.error("Le module administration_site.inventaire ne contient pas de fonction render().")
        st.info("Il faut ajouter une fonction render() dans administration_site/inventaire.py")


def show():
    _run_module()


def render():
    _run_module()


if __name__ == "__main__":
    show()
