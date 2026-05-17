# -*- coding: utf-8 -*-
import streamlit as st


def render():
    st.subheader("Commandes utiles")

    st.code("systemctl status logistique.service --no-pager -l", language="bash")
    st.code("journalctl -u logistique.service -n 120 --no-pager", language="bash")
    st.code("systemctl restart logistique.service", language="bash")
    st.code("free -h", language="bash")
