# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from datetime import datetime

import streamlit as st

from administration_systeme.common import DATA_DIR


MAINT_FILE = DATA_DIR / "maintenance.json"


def load_maintenance() -> dict:
    if not MAINT_FILE.exists():
        return {
            "enabled": False,
            "message": "Le site est temporairement en maintenance.",
            "updated_at": None,
        }

    try:
        return json.loads(MAINT_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {
            "enabled": False,
            "message": "Le site est temporairement en maintenance.",
            "updated_at": None,
        }


def save_maintenance(data: dict):
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    MAINT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def render():
    st.subheader("🚧 Maintenance")

    data = load_maintenance()

    enabled = st.toggle(
        "Activer le mode maintenance",
        value=bool(data.get("enabled", False)),
        key="maintenance_enabled",
    )

    message = st.text_area(
        "Message de maintenance",
        value=data.get("message", "Le site est temporairement en maintenance."),
        height=120,
        key="maintenance_message",
    )

    st.caption(f"Dernière modification : {data.get('updated_at') or 'Jamais'}")
    st.code(str(MAINT_FILE), language="bash")

    if st.button("Enregistrer le mode maintenance", type="primary", width="stretch", key="save_maintenance"):
        save_maintenance(
            {
                "enabled": enabled,
                "message": message,
            }
        )
        st.success("Paramètres de maintenance enregistrés.")
        st.info("Le fichier est prêt. On pourra ensuite le connecter dans main.py pour bloquer les utilisateurs non-admin.")
