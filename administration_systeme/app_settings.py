# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from datetime import datetime

import streamlit as st

from administration_systeme.common import DATA_DIR


SETTINGS_FILE = DATA_DIR / "app_settings.json"


DEFAULT_SETTINGS = {
    "app_name": "Logistique Pro - Ville de Marly",
    "version": "2.0",
    "theme_name": "Municipal Bleu",
    "footer_text": "© Ville de Marly",
    "contact_email": "",
    "server_url": "http://192.168.1.150:8501",
    "city_name": "Ville de Marly",
    "primary_color": "#003366",
    "updated_at": None,
}


def load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        return DEFAULT_SETTINGS.copy()

    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        result = DEFAULT_SETTINGS.copy()
        result.update(data)
        return result
    except Exception:
        return DEFAULT_SETTINGS.copy()


def save_settings(data: dict):
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def render():
    st.subheader("⚙️ Paramètres application")

    settings = load_settings()

    st.info("Ces paramètres sont enregistrés dans `data/app_settings.json`.")

    app_name = st.text_input("Nom de l'application", value=settings.get("app_name", ""), key="set_app_name")
    version = st.text_input("Version", value=settings.get("version", ""), key="set_version")
    city_name = st.text_input("Collectivité / Ville", value=settings.get("city_name", ""), key="set_city_name")
    theme_name = st.text_input("Nom du thème", value=settings.get("theme_name", ""), key="set_theme_name")
    primary_color = st.text_input("Couleur principale", value=settings.get("primary_color", "#003366"), key="set_primary_color")
    footer_text = st.text_input("Texte pied de page", value=settings.get("footer_text", ""), key="set_footer_text")
    contact_email = st.text_input("Email contact", value=settings.get("contact_email", ""), key="set_contact_email")
    server_url = st.text_input("URL serveur", value=settings.get("server_url", ""), key="set_server_url")

    st.caption(f"Dernière modification : {settings.get('updated_at') or 'Jamais'}")
    st.code(str(SETTINGS_FILE), language="bash")

    if st.button("Enregistrer les paramètres", type="primary", width="stretch", key="save_app_settings"):
        save_settings(
            {
                "app_name": app_name,
                "version": version,
                "city_name": city_name,
                "theme_name": theme_name,
                "primary_color": primary_color,
                "footer_text": footer_text,
                "contact_email": contact_email,
                "server_url": server_url,
            }
        )
        st.success("Paramètres enregistrés.")
        st.rerun()

    st.divider()

    st.markdown("### Aperçu")

    st.markdown(f"**Application :** {settings.get('app_name')}")
    st.markdown(f"**Ville :** {settings.get('city_name')}")
    st.markdown(f"**Version :** {settings.get('version')}")
    st.markdown(f"**Thème :** {settings.get('theme_name')}")
    st.markdown(f"**URL :** {settings.get('server_url')}")

    st.divider()

    st.markdown("### JSON actuel")
    st.json(load_settings())

    st.divider()

    st.markdown("### Code utile pour utiliser ces paramètres dans l'application")

    st.code(
        """
from pathlib import Path
import json

def load_app_settings():
    path = Path("data/app_settings.json")
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
""",
        language="python",
    )
