# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import shutil
from pathlib import Path

import streamlit as st

from administration_systeme.common import APP_DIR, fmt_size, run_cmd


def read_proc_meminfo() -> dict[str, int]:
    data = {}

    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            number = int(value.strip().split()[0]) * 1024
            data[key] = number
    except Exception:
        pass

    return data


def loadavg() -> str:
    try:
        return Path("/proc/loadavg").read_text().strip()
    except Exception:
        return "N/A"


def uptime() -> str:
    ok, out = run_cmd(["uptime", "-p"], timeout=10)
    return out if ok else "N/A"


def service_status() -> str:
    ok, out = run_cmd(["systemctl", "is-active", "logistique.service"], timeout=10)
    return out.strip() if out else "N/A"


def render():
    st.subheader("🩺 Santé serveur")

    st.info("Surveillance rapide du conteneur / serveur qui exécute Logistique Pro.")

    mem = read_proc_meminfo()

    total = mem.get("MemTotal", 0)
    available = mem.get("MemAvailable", 0)
    used = max(total - available, 0) if total else 0

    swap_total = mem.get("SwapTotal", 0)
    swap_free = mem.get("SwapFree", 0)
    swap_used = max(swap_total - swap_free, 0) if swap_total else 0

    disk = shutil.disk_usage(str(APP_DIR))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("RAM utilisée", fmt_size(used))
    c2.metric("RAM totale", fmt_size(total))
    c3.metric("Swap utilisée", fmt_size(swap_used))
    c4.metric("Service", service_status())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Disque utilisé", fmt_size(disk.used))
    c2.metric("Disque libre", fmt_size(disk.free))
    c3.metric("Disque total", fmt_size(disk.total))
    c4.metric("Load average", loadavg().split()[0] if loadavg() != "N/A" else "N/A")

    st.progress(min(int((disk.used / disk.total) * 100), 100), text=f"Disque utilisé : {(disk.used / disk.total) * 100:.1f}%")

    if total:
        st.progress(min(int((used / total) * 100), 100), text=f"RAM utilisée : {(used / total) * 100:.1f}%")

    if swap_total:
        st.progress(min(int((swap_used / swap_total) * 100), 100), text=f"Swap utilisée : {(swap_used / swap_total) * 100:.1f}%")
    else:
        st.warning("Aucun swap détecté. En cas de pic mémoire, le système peut tuer Streamlit avec OOM-kill.")

    st.divider()

    st.markdown("### Commandes de contrôle")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Voir free -h", width="stretch", key="health_free"):
            ok, out = run_cmd(["free", "-h"], timeout=10)
            st.code(out, language="bash")

        if st.button("Voir df -h", width="stretch", key="health_df"):
            ok, out = run_cmd(["df", "-h"], timeout=10)
            st.code(out, language="bash")

    with col2:
        if st.button("Voir processus Streamlit", width="stretch", key="health_ps"):
            ok, out = run_cmd(["bash", "-lc", "ps aux | grep streamlit | grep -v grep"], timeout=10)
            st.code(out, language="bash")

        if st.button("Voir statut service", width="stretch", key="health_service"):
            ok, out = run_cmd(["systemctl", "status", "logistique.service", "--no-pager", "-l"], timeout=20)
            st.code(out, language="bash")

    st.divider()

    if disk.free < 2 * 1024 * 1024 * 1024:
        st.error("Attention : moins de 2 Go libres sur le disque.")

    if total and available < 300 * 1024 * 1024:
        st.error("Attention : mémoire disponible très faible.")

    if swap_total == 0:
        st.warning("Recommandation : ajouter un swap de 2 Go pour éviter les OOM-kill.")
        st.code(
            "fallocate -l 2G /swapfile\n"
            "chmod 600 /swapfile\n"
            "mkswap /swapfile\n"
            "swapon /swapfile\n"
            "echo '/swapfile none swap sw 0 0' >> /etc/fstab",
            language="bash",
        )
