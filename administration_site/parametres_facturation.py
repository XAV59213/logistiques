# -*- coding: utf-8 -*-
"""
Administration - Paramètres Facturation

PATCH 40 :
- paramètres de facturation persistants en SQLite
- identité facturation
- TVA, numérotation, mentions légales
- export JSON
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_DIR = Path("/opt/logistique-pro")
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "parametres_facturation.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)


DEFAULTS = {
    "nom_structure": "Ville de Marly",
    "adresse": "",
    "code_postal": "",
    "ville": "Marly",
    "telephone": "",
    "email": "",
    "siret": "",
    "tva_intracom": "",
    "iban": "",
    "bic": "",
    "banque": "",
    "prefixe_devis": "DEV",
    "prefixe_facture": "FAC",
    "prochain_numero_devis": "1",
    "prochain_numero_facture": "1",
    "taux_tva_defaut": "20.0",
    "devise": "EUR",
    "delai_paiement_jours": "30",
    "conditions_paiement": "Paiement à réception de facture.",
    "mentions_legales": "",
    "pied_page_facture": "Merci pour votre confiance.",
}


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS parametres_facturation (
                cle TEXT PRIMARY KEY,
                valeur TEXT,
                updated_at TEXT
            )
            """
        )

        for key, value in DEFAULTS.items():
            conn.execute(
                """
                INSERT OR IGNORE INTO parametres_facturation (cle, valeur, updated_at)
                VALUES (?, ?, ?)
                """,
                (key, value, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )

        conn.commit()
    finally:
        conn.close()


def load_settings() -> dict[str, str]:
    init_db()

    conn = connect()
    try:
        rows = conn.execute("SELECT cle, valeur FROM parametres_facturation").fetchall()
        settings = {row["cle"]: row["valeur"] for row in rows}

        for key, value in DEFAULTS.items():
            settings.setdefault(key, value)

        return settings
    finally:
        conn.close()


def save_settings(settings: dict[str, str]) -> None:
    init_db()

    conn = connect()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for key, value in settings.items():
            conn.execute(
                """
                INSERT INTO parametres_facturation (cle, valeur, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(cle) DO UPDATE SET
                    valeur=excluded.valeur,
                    updated_at=excluded.updated_at
                """,
                (key, str(value), now),
            )

        conn.commit()
    finally:
        conn.close()


def reset_defaults() -> None:
    save_settings(DEFAULTS.copy())


def settings_dataframe() -> pd.DataFrame:
    settings = load_settings()
    return pd.DataFrame(
        [{"Paramètre": key, "Valeur": value} for key, value in settings.items()]
    )


def render_identite(settings: dict[str, str]) -> dict[str, str]:
    # PATCH76_DISABLED_ADMIN_MODULE_TITLE: st.markdown("### 🏢 Identité de facturation")

    c1, c2 = st.columns(2)

    with c1:
        settings["nom_structure"] = st.text_input("Nom structure", value=settings.get("nom_structure", ""))
        settings["adresse"] = st.text_area("Adresse", value=settings.get("adresse", ""))
        settings["code_postal"] = st.text_input("Code postal", value=settings.get("code_postal", ""))
        settings["ville"] = st.text_input("Ville", value=settings.get("ville", ""))

    with c2:
        settings["telephone"] = st.text_input("Téléphone", value=settings.get("telephone", ""))
        settings["email"] = st.text_input("Email", value=settings.get("email", ""))
        settings["siret"] = st.text_input("SIRET", value=settings.get("siret", ""))
        settings["tva_intracom"] = st.text_input("TVA intracommunautaire", value=settings.get("tva_intracom", ""))

    return settings


def render_numerotation(settings: dict[str, str]) -> dict[str, str]:
    st.markdown("### 🔢 Numérotation")

    c1, c2 = st.columns(2)

    with c1:
        settings["prefixe_devis"] = st.text_input("Préfixe devis", value=settings.get("prefixe_devis", "DEV"))
        settings["prochain_numero_devis"] = str(
            st.number_input(
                "Prochain numéro devis",
                min_value=1,
                value=int(float(settings.get("prochain_numero_devis", "1") or 1)),
                step=1,
            )
        )

    with c2:
        settings["prefixe_facture"] = st.text_input("Préfixe facture", value=settings.get("prefixe_facture", "FAC"))
        settings["prochain_numero_facture"] = str(
            st.number_input(
                "Prochain numéro facture",
                min_value=1,
                value=int(float(settings.get("prochain_numero_facture", "1") or 1)),
                step=1,
            )
        )

    st.info(
        f"Exemple devis : {settings['prefixe_devis']}-{int(float(settings['prochain_numero_devis'])):04d}  |  "
        f"Exemple facture : {settings['prefixe_facture']}-{int(float(settings['prochain_numero_facture'])):04d}"
    )

    return settings


def render_tva_paiement(settings: dict[str, str]) -> dict[str, str]:
    st.markdown("### 💶 TVA et paiement")

    c1, c2, c3 = st.columns(3)

    with c1:
        settings["taux_tva_defaut"] = str(
            st.number_input(
                "Taux TVA par défaut (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(settings.get("taux_tva_defaut", "20.0") or 20.0),
                step=0.1,
            )
        )

    with c2:
        settings["devise"] = st.selectbox(
            "Devise",
            ["EUR", "USD", "GBP", "CHF"],
            index=["EUR", "USD", "GBP", "CHF"].index(settings.get("devise", "EUR"))
            if settings.get("devise", "EUR") in ["EUR", "USD", "GBP", "CHF"]
            else 0,
        )

    with c3:
        settings["delai_paiement_jours"] = str(
            st.number_input(
                "Délai paiement jours",
                min_value=0,
                value=int(float(settings.get("delai_paiement_jours", "30") or 30)),
                step=1,
            )
        )

    settings["conditions_paiement"] = st.text_area(
        "Conditions de paiement",
        value=settings.get("conditions_paiement", ""),
    )

    return settings


def render_banque(settings: dict[str, str]) -> dict[str, str]:
    st.markdown("### 🏦 Coordonnées bancaires")

    c1, c2 = st.columns(2)

    with c1:
        settings["banque"] = st.text_input("Banque", value=settings.get("banque", ""))
        settings["iban"] = st.text_input("IBAN", value=settings.get("iban", ""))

    with c2:
        settings["bic"] = st.text_input("BIC", value=settings.get("bic", ""))

    return settings


def render_mentions(settings: dict[str, str]) -> dict[str, str]:
    st.markdown("### 📄 Mentions et pied de page")

    settings["mentions_legales"] = st.text_area(
        "Mentions légales",
        value=settings.get("mentions_legales", ""),
        height=140,
    )

    settings["pied_page_facture"] = st.text_area(
        "Pied de page facture",
        value=settings.get("pied_page_facture", ""),
        height=100,
    )

    return settings


def render_export(settings: dict[str, str]) -> None:
    st.markdown("### 📥 Export / diagnostic")

    st.dataframe(settings_dataframe(), width="stretch", hide_index=True)

    json_data = json.dumps(settings, indent=2, ensure_ascii=False).encode("utf-8")

    st.download_button(
        "📥 Télécharger les paramètres JSON",
        data=json_data,
        file_name="parametres_facturation.json",
        mime="application/json",
        width="stretch",
    )

    st.caption(f"Base utilisée : {DB_PATH}")


def render() -> None:
    init_db()

    st.subheader("🧾 Paramètres facturation")
    st.caption("Configuration centralisée des devis, factures, TVA et mentions légales.")

    settings = load_settings()

    tabs = st.tabs(
        [
            "🏢 Identité",
            "🔢 Numérotation",
            "💶 TVA / Paiement",
            "🏦 Banque",
            "📄 Mentions",
            "📥 Export",
        ]
    )

    with tabs[0]:
        settings = render_identite(settings)

    with tabs[1]:
        settings = render_numerotation(settings)

    with tabs[2]:
        settings = render_tva_paiement(settings)

    with tabs[3]:
        settings = render_banque(settings)

    with tabs[4]:
        settings = render_mentions(settings)

    with tabs[5]:
        render_export(settings)

    st.divider()

    c1, c2 = st.columns(2)

    with c1:
        if st.button("💾 Enregistrer les paramètres", width="stretch"):
            save_settings(settings)
            st.success("Paramètres de facturation enregistrés.")
            st.rerun()

    with c2:
        confirm_reset = st.checkbox("Confirmer la réinitialisation")
        if st.button("♻️ Réinitialiser par défaut", disabled=not confirm_reset, width="stretch"):
            reset_defaults()
            st.success("Paramètres réinitialisés.")
            st.rerun()


def show() -> None:
    render()
