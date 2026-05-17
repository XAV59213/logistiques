# -*- coding: utf-8 -*-
import sys
import streamlit as st

from administration_systeme.common import APP_DIR, DATA_DIR, run_cmd


def render():
    st.subheader("Diagnostic serveur")

    c1, c2, c3 = st.columns(3)
    c1.metric("Application", str(APP_DIR))
    c2.metric("Python", sys.version.split()[0])
    c3.metric("Data", "OK" if DATA_DIR.exists() else "Manquant")

    st.code(str(APP_DIR), language="bash")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("État mémoire serveur", width="stretch", key="diag_mem_mod"):
            ok, out = run_cmd(["free", "-h"], timeout=10)
            st.code(out, language="bash")

    with col2:
        if st.button("État service logistique", width="stretch", key="diag_service_mod"):
            ok, out = run_cmd(["systemctl", "status", "logistique.service", "--no-pager", "-l"], timeout=20)
            st.code(out, language="bash")

    if st.button("Logs récents", width="stretch", key="diag_logs_mod"):
        ok, out = run_cmd(["journalctl", "-u", "logistique.service", "-n", "80", "--no-pager"], timeout=30)
        st.code(out, language="bash")
