import streamlit as st
from pathlib import Path


def page_header(title: str, subtitle: str = "", icon_path: str | None = None):
    if icon_path and Path(icon_path).exists():
        col1, col2 = st.columns([1, 10])
        with col1:
            st.image(icon_path, width=42)
        with col2:
            st.title(title)
            if subtitle:
                st.caption(subtitle)
    else:
        st.title(title)
        if subtitle:
            st.caption(subtitle)


def info_card(label: str, value, delta=None):
    st.metric(label, value, delta=delta)


def section_title(title: str):
    st.subheader(title)


def empty_state(message: str = "Aucune donnée disponible."):
    st.info(message)
