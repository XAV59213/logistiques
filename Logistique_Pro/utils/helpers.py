import streamlit as st

def page_header(title: str, subtitle: str = ""):
    st.title(title)
    if subtitle:
        st.caption(subtitle)

def info_card(label: str, value):
    st.metric(label, value)
