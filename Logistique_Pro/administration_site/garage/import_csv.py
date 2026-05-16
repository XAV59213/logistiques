# -*- coding: utf-8 -*-
from __future__ import annotations

from io import StringIO

import pandas as pd
import streamlit as st

from .db import init_db
from .vehicules import add_vehicule, load_vehicules


EXPECTED_COLUMNS = [
    "nom",
    "immatriculation",
    "marque",
    "modele",
    "categorie",
    "service",
    "energie",
    "kilometrage_actuel",
    "date_mise_en_service",
    "date_ct",
    "assurance",
    "statut",
    "notes",
]


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {}

    for col in df.columns:
        clean = str(col).strip().lower()
        clean = clean.replace(" ", "_")
        clean = clean.replace("-", "_")
        clean = clean.replace("é", "e")
        clean = clean.replace("è", "e")
        clean = clean.replace("ê", "e")
        clean = clean.replace("à", "a")
        clean = clean.replace("ç", "c")

        aliases = {
            "immatriculation": "immatriculation",
            "immat": "immatriculation",
            "plaque": "immatriculation",
            "vehicule": "nom",
            "véhicule": "nom",
            "modele": "modele",
            "modèle": "modele",
            "energie": "energie",
            "énergie": "energie",
            "carburant": "energie",
            "kilometrage": "kilometrage_actuel",
            "kilometrage_actuel": "kilometrage_actuel",
            "km": "kilometrage_actuel",
            "date_ct": "date_ct",
            "controle_technique": "date_ct",
            "contrôle_technique": "date_ct",
            "ct": "date_ct",
        }

        mapping[col] = aliases.get(clean, clean)

    return df.rename(columns=mapping)


def _safe_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _safe_int(value) -> int:
    if pd.isna(value) or value == "":
        return 0
    try:
        return int(float(str(value).replace(" ", "").replace(",", ".")))
    except Exception:
        return 0


def _existing_immat_set() -> set[str]:
    vehicules = load_vehicules(include_inactive=True)
    return {
        str(v.get("immatriculation") or "").strip().upper()
        for v in vehicules
        if str(v.get("immatriculation") or "").strip()
    }


def _prepare_import(df: pd.DataFrame) -> pd.DataFrame:
    df = _normalize_columns(df)

    for col in EXPECTED_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[EXPECTED_COLUMNS].copy()

    df["immatriculation"] = df["immatriculation"].apply(lambda x: _safe_text(x).upper())
    df["kilometrage_actuel"] = df["kilometrage_actuel"].apply(_safe_int)

    for col in df.columns:
        if col not in ["kilometrage_actuel"]:
            df[col] = df[col].apply(_safe_text)

    return df


def render_import_csv() -> None:
    st.markdown("### 📤 Import CSV véhicules")

    init_db()

    st.info(
        "Importe un fichier CSV contenant une liste de véhicules. "
        "La colonne `immatriculation` est obligatoire."
    )

    with st.expander("📋 Modèle de colonnes CSV", expanded=False):
        st.code(",".join(EXPECTED_COLUMNS), language="text")

        example = pd.DataFrame(
            [
                {
                    "nom": "Camion benne",
                    "immatriculation": "AB-123-CD",
                    "marque": "Renault",
                    "modele": "Maxity",
                    "categorie": "Poids lourd / benne",
                    "service": "Technique",
                    "energie": "Diesel",
                    "kilometrage_actuel": 125000,
                    "date_mise_en_service": "2020-01-15",
                    "date_ct": "2026-01-15",
                    "assurance": "Assurance X",
                    "statut": "Actif",
                    "notes": "Exemple",
                }
            ]
        )

        csv_model = example.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📥 Télécharger un modèle CSV",
            data=csv_model,
            file_name="modele_import_garage_vehicules.csv",
            mime="text/csv",
            width="stretch",
        )

    uploaded = st.file_uploader(
        "Choisir un fichier CSV",
        type=["csv"],
        key="garage_import_csv_file",
    )

    if uploaded is None:
        return

    try:
        content = uploaded.getvalue().decode("utf-8-sig")
    except UnicodeDecodeError:
        content = uploaded.getvalue().decode("latin-1")

    try:
        df_raw = pd.read_csv(StringIO(content), sep=None, engine="python")
    except Exception as exc:
        st.error("Impossible de lire le fichier CSV.")
        st.exception(exc)
        return

    if df_raw.empty:
        st.warning("Le fichier CSV est vide.")
        return

    df = _prepare_import(df_raw)

    st.markdown("#### Aperçu avant import")
    st.dataframe(df.head(50), width="stretch", hide_index=True)

    existing = _existing_immat_set()
    duplicates = df[df["immatriculation"].isin(existing)]
    missing_immat = df[df["immatriculation"] == ""]

    c1, c2, c3 = st.columns(3)
    c1.metric("Lignes CSV", len(df))
    c2.metric("Déjà existantes", len(duplicates))
    c3.metric("Sans immatriculation", len(missing_immat))

    import_mode = st.radio(
        "Mode d'import",
        [
            "Ignorer les immatriculations existantes",
            "Importer uniquement les nouvelles lignes",
        ],
        horizontal=True,
        key="garage_import_mode",
    )

    rows_to_import = df.copy()
    rows_to_import = rows_to_import[rows_to_import["immatriculation"] != ""]

    if import_mode in [
        "Ignorer les immatriculations existantes",
        "Importer uniquement les nouvelles lignes",
    ]:
        rows_to_import = rows_to_import[~rows_to_import["immatriculation"].isin(existing)]

    st.write(f"**Lignes prêtes à importer :** {len(rows_to_import)}")

    confirm = st.checkbox("Je confirme l'import CSV", key="garage_import_confirm")

    if st.button("📤 Importer les véhicules", disabled=not confirm, width="stretch"):
        inserted = 0
        errors = []

        for idx, row in rows_to_import.iterrows():
            try:
                add_vehicule(
                    {
                        "nom": row.get("nom", ""),
                        "immatriculation": row.get("immatriculation", ""),
                        "marque": row.get("marque", ""),
                        "modele": row.get("modele", ""),
                        "categorie": row.get("categorie", ""),
                        "service": row.get("service", ""),
                        "energie": row.get("energie", ""),
                        "kilometrage_actuel": int(row.get("kilometrage_actuel") or 0),
                        "date_mise_en_service": row.get("date_mise_en_service", ""),
                        "date_ct": row.get("date_ct", ""),
                        "assurance": row.get("assurance", ""),
                        "statut": row.get("statut", "") or "Actif",
                        "actif": True,
                        "photo_path": "",
                        "notes": row.get("notes", ""),
                    }
                )
                inserted += 1
            except Exception as exc:
                errors.append(f"Ligne {idx + 1} : {exc}")

        if inserted:
            st.success(f"{inserted} véhicule(s) importé(s).")

        if errors:
            st.error(f"{len(errors)} erreur(s) pendant l'import.")
            with st.expander("Voir les erreurs"):
                st.code("\n".join(errors))

        if inserted and not errors:
            st.rerun()

# ============================================================
# Compatibilité navigation Streamlit
# Patch 104
# Le routeur peut appeler render() ou show()
# ============================================================

def render(*args, **kwargs):
    """
    Point d'entrée standard attendu par le routeur Garage.
    """
    return render_import_csv()

def show(*args, **kwargs):
    """
    Alias de compatibilité pour les anciens routeurs.
    """
    return render(*args, **kwargs)

