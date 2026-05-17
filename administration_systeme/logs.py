# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import streamlit as st

from administration_systeme.common import APP_DIR, run_cmd


def render():
    st.subheader("📜 Logs avancés")

    st.info("Consultation des logs du service Logistique Pro et recherche rapide dans les erreurs.")

    col1, col2, col3 = st.columns(3)

    with col1:
        lines = st.number_input(
            "Nombre de lignes",
            min_value=20,
            max_value=1000,
            value=120,
            step=20,
            key="logs_lines",
        )

    with col2:
        level = st.selectbox(
            "Filtre rapide",
            ["Tous", "error", "exception", "warning", "oom", "traceback", "streamlit"],
            key="logs_filter",
        )

    with col3:
        since = st.selectbox(
            "Période",
            ["Aujourd'hui", "1 heure", "10 minutes", "Service complet"],
            key="logs_since",
        )

    if since == "Aujourd'hui":
        cmd = ["journalctl", "-u", "logistique.service", "--since", "today", "-n", str(lines), "--no-pager"]
    elif since == "1 heure":
        cmd = ["journalctl", "-u", "logistique.service", "--since", "1 hour ago", "-n", str(lines), "--no-pager"]
    elif since == "10 minutes":
        cmd = ["journalctl", "-u", "logistique.service", "--since", "10 minutes ago", "-n", str(lines), "--no-pager"]
    else:
        cmd = ["journalctl", "-u", "logistique.service", "-n", str(lines), "--no-pager"]

    if st.button("Actualiser les logs", width="stretch", key="refresh_logs"):
        st.session_state["logs_refresh"] = datetime.now().isoformat()

    ok, output = run_cmd(cmd, timeout=30)

    if level != "Tous":
        output = "\n".join([line for line in output.splitlines() if level.lower() in line.lower()])

    if not ok:
        st.error("Erreur lecture logs.")

    st.code(output or "Aucune ligne trouvée.", language="bash")

    st.download_button(
        "Télécharger les logs affichés",
        data=output.encode("utf-8"),
        file_name=f"logistique_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain",
        width="stretch",
        key="download_current_logs",
    )

    st.divider()

    st.markdown("### Recherche dans les fichiers .log du projet")

    log_files = []
    for p in APP_DIR.rglob("*.log"):
        if ".venv" in str(p) or "/.git/" in str(p):
            continue
        log_files.append(p)

    if not log_files:
        st.info("Aucun fichier .log trouvé dans le projet.")
        return

    selected = st.selectbox(
        "Fichier log",
        [str(p.relative_to(APP_DIR)) for p in log_files],
        key="selected_log_file",
    )

    selected_path = APP_DIR / selected

    search = st.text_input("Rechercher dans ce fichier", key="search_log_file")

    try:
        text = selected_path.read_text(encoding="utf-8", errors="ignore")
        file_lines = text.splitlines()[-500:]

        if search:
            file_lines = [line for line in file_lines if search.lower() in line.lower()]

        st.code("\n".join(file_lines) or "Aucun résultat.", language="bash")

    except Exception as exc:
        st.error(f"Impossible de lire le fichier : {exc}")
