# -*- coding: utf-8 -*-
from __future__ import annotations

import traceback

import streamlit as st


def render() -> None:
    try:
        from administration_site.patrimoine.main import render as patrimoine_render
        patrimoine_render()
    except Exception as exc:
        st.error("Erreur pendant le chargement du module Patrimoine bâti.")
        with st.expander("Voir le détail de l'erreur"):
            st.code("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))


def show() -> None:
    render()
