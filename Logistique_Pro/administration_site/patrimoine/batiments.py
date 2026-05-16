# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from .db import (
    add_column_if_missing,
    connect,
    count_table,
    diagnostics,
    find_table,
    get_db_path,
    get_tables,
    read_table,
    table_columns,
)


# ============================================================
# Helpers sûrs NaN - Patch 112
# ============================================================

def _pat_is_nan(value):
    try:
        return value != value
    except Exception:
        return False


def _pat_clean(value, default=""):
    """
    Nettoie None / NaN / 'nan' pour éviter l'affichage de nan.
    """
    if value is None:
        return default

    if _pat_is_nan(value):
        return default

    value = str(value)

    if value.strip().lower() in ("", "nan", "none", "null", "<na>", "nat"):
        return default

    return value


def _pat_safe_float(value, default=0.0):
    """
    Convertit en float sans planter sur NaN / vide / None.
    """
    try:
        if value is None:
            return default

        if _pat_is_nan(value):
            return default

        value = str(value).strip().replace(",", ".")

        if value.lower() in ("", "nan", "none", "null", "<na>", "nat"):
            return default

        return float(value)
    except Exception:
        return default


def _pat_safe_int(value, default=0):
    """
    Convertit en int sans planter sur NaN / vide / None.
    """
    try:
        if value is None:
            return default

        if _pat_is_nan(value):
            return default

        value = str(value).strip().replace(",", ".")

        if value.lower() in ("", "nan", "none", "null", "<na>", "nat"):
            return default

        return int(float(value))
    except Exception:
        return default


PROJECT_DIR = Path("/opt/logistique-pro")
PHOTOS_DIR = PROJECT_DIR / "data" / "patrimoine_photos"
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)


BATIMENT_TABLE_CANDIDATES = [
    "batiments",
    "patrimoine_batiments",
    "batiment",
    "buildings",
    "locaux",
]


def _current_table() -> str:
    table = find_table(BATIMENT_TABLE_CANDIDATES, prefer_non_empty=True)

    if table:
        return table

    conn = connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS batiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT,
                type_batiment TEXT,
                adresse TEXT,
                code_postal TEXT,
                ville TEXT,
                surface REAL DEFAULT 0,
                valeur_estimee REAL DEFAULT 0,
                annee_construction INTEGER,
                etat TEXT DEFAULT 'Bon',
                responsable TEXT,
                telephone TEXT,
                email TEXT,
                photo_path TEXT,
                actif INTEGER DEFAULT 1,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    return "batiments"


def _ensure_schema() -> None:
    table = _current_table()

    required = {
        "nom": "nom TEXT",
        "type_batiment": "type_batiment TEXT",
        "adresse": "adresse TEXT",
        "code_postal": "code_postal TEXT",
        "ville": "ville TEXT",
        "surface": "surface REAL DEFAULT 0",
        "valeur_estimee": "valeur_estimee REAL DEFAULT 0",
        "annee_construction": "annee_construction INTEGER",
        "etat": "etat TEXT DEFAULT 'Bon'",
        "responsable": "responsable TEXT",
        "telephone": "telephone TEXT",
        "email": "email TEXT",
        "photo_path": "photo_path TEXT",
        "image_path": "image_path TEXT",
        "actif": "actif INTEGER DEFAULT 1",
        "notes": "notes TEXT",
        "created_at": "created_at TEXT DEFAULT CURRENT_TIMESTAMP",
        "updated_at": "updated_at TEXT",
    }

    for col, sql in required.items():
        try:
            add_column_if_missing(table, col, sql)
        except Exception:
            pass

    conn = connect()
    try:
        cols = table_columns(table)

        if "actif" in cols:
            conn.execute(f'UPDATE "{table}" SET actif=1 WHERE actif IS NULL')
        if "surface" in cols:
            conn.execute(f'UPDATE "{table}" SET surface=0 WHERE surface IS NULL')
        if "valeur_estimee" in cols:
            conn.execute(f'UPDATE "{table}" SET valeur_estimee=0 WHERE valeur_estimee IS NULL')

        conn.commit()
    finally:
        conn.close()


def _save_uploaded_photo(uploaded_file, batiment_id: int | None = None) -> str:
    if uploaded_file is None:
        return ""

    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in [".jpg", ".jpeg", ".png", ".webp"]:
        suffix = ".jpg"

    safe_id = batiment_id or "new"
    filename = f"batiment_{safe_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{suffix}"
    target = PHOTOS_DIR / filename

    with open(target, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return str(target)


def _get_photo_value(row: dict[str, Any]) -> str:
    for key in ["photo_path", "image_path", "photo", "image"]:
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


def _display_photo(row: dict[str, Any], width: int = 420) -> None:
    photo = _get_photo_value(row)

    if not photo:
        st.info("Aucune image enregistrée pour ce bâtiment.")
        return

    path = Path(photo)

    if not path.is_absolute():
        path = PROJECT_DIR / photo

    if path.exists():
        st.image(str(path), width=width)
    else:
        st.warning(f"Image introuvable : {photo}")


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()

    aliases = {
        "designation": "nom",
        "libelle": "nom",
        "libellé": "nom",
        "nom_batiment": "nom",
        "batiment": "nom",
        "bâtiment": "nom",
        "nom_site": "nom",
        "site": "nom",
        "titre": "nom",
        "type": "type_batiment",
        "categorie": "type_batiment",
        "catégorie": "type_batiment",
        "surface_m2": "surface",
        "surface_totale": "surface",
        "valeur": "valeur_estimee",
        "valeur_patrimoniale": "valeur_estimee",
        "statut": "etat",
        "etat_general": "etat",
        "photo": "photo_path",
        "image": "photo_path",
    }

    for old, new in aliases.items():
        if old in df.columns and new not in df.columns:
            df[new] = df[old]

    defaults = {
        "nom": "",
        "type_batiment": "",
        "adresse": "",
        "code_postal": "",
        "ville": "",
        "surface": 0,
        "valeur_estimee": 0,
        "annee_construction": "",
        "etat": "",
        "responsable": "",
        "telephone": "",
        "email": "",
        "photo_path": "",
        "image_path": "",
        "actif": 1,
        "notes": "",
    }

    for col, val in defaults.items():
        if col not in df.columns:
            df[col] = val

    if "id" not in df.columns:
        df["id"] = range(1, len(df) + 1)

    df["surface"] = pd.to_numeric(df["surface"], errors="coerce").fillna(0)
    df["valeur_estimee"] = pd.to_numeric(df["valeur_estimee"], errors="coerce").fillna(0)
    df["actif"] = pd.to_numeric(df["actif"], errors="coerce").fillna(1).astype(int)

    return df


def init_db() -> None:
    _ensure_schema()


def load_batiments(include_inactive: bool = False) -> pd.DataFrame:
    _ensure_schema()
    table = _current_table()

    try:
        df = read_table(table)
    except Exception:
        return pd.DataFrame()

    df = _normalize(df)

    if not include_inactive and "actif" in df.columns:
        df = df[df["actif"] == 1]

    return df.sort_values(["nom", "id"], na_position="last")


def get_batiment(batiment_id: int) -> dict[str, Any] | None:
    df = load_batiments(include_inactive=True)
    if df.empty:
        return None

    row = df[df["id"] == int(batiment_id)]
    if row.empty:
        return None

    return row.iloc[0].to_dict()


def add_batiment(data: dict[str, Any]) -> int:
    _ensure_schema()
    table = _current_table()
    cols = table_columns(table)

    payload = {
        "nom": data.get("nom"),
        "type_batiment": data.get("type_batiment"),
        "adresse": data.get("adresse"),
        "code_postal": data.get("code_postal"),
        "ville": data.get("ville"),
        "surface": float(data.get("surface") or 0),
        "valeur_estimee": float(data.get("valeur_estimee") or 0),
        "annee_construction": _pat_safe_int(data.get("annee_construction")) if _pat_safe_int(data.get("annee_construction")) else None,
        "etat": data.get("etat"),
        "responsable": data.get("responsable"),
        "telephone": data.get("telephone"),
        "email": data.get("email"),
        "photo_path": data.get("photo_path") or "",
        "image_path": data.get("photo_path") or "",
        "actif": 1,
        "notes": data.get("notes"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    payload = {k: v for k, v in payload.items() if k in cols}

    conn = connect()
    try:
        columns = ", ".join([f'"{k}"' for k in payload.keys()])
        placeholders = ", ".join(["?"] * len(payload))

        cur = conn.execute(
            f'INSERT INTO "{table}" ({columns}) VALUES ({placeholders})',
            tuple(payload.values()),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def update_batiment(batiment_id: int, data: dict[str, Any]) -> None:
    _ensure_schema()
    table = _current_table()
    cols = table_columns(table)

    payload = {
        "nom": data.get("nom"),
        "type_batiment": data.get("type_batiment"),
        "adresse": data.get("adresse"),
        "code_postal": data.get("code_postal"),
        "ville": data.get("ville"),
        "surface": float(data.get("surface") or 0),
        "valeur_estimee": float(data.get("valeur_estimee") or 0),
        "annee_construction": _pat_safe_int(data.get("annee_construction")) if _pat_safe_int(data.get("annee_construction")) else None,
        "etat": data.get("etat"),
        "responsable": data.get("responsable"),
        "telephone": data.get("telephone"),
        "email": data.get("email"),
        "actif": 1 if data.get("actif", True) else 0,
        "notes": data.get("notes"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    if data.get("photo_path"):
        payload["photo_path"] = data.get("photo_path")
        payload["image_path"] = data.get("photo_path")

    payload = {k: v for k, v in payload.items() if k in cols}

    conn = connect()
    try:
        set_clause = ", ".join([f'"{k}"=?' for k in payload.keys()])
        conn.execute(
            f'UPDATE "{table}" SET {set_clause} WHERE id=?',
            tuple(payload.values()) + (int(batiment_id),),
        )
        conn.commit()
    finally:
        conn.close()


def delete_batiment(batiment_id: int, hard_delete: bool = False) -> None:
    _ensure_schema()
    table = _current_table()
    cols = table_columns(table)

    conn = connect()
    try:
        if hard_delete:
            conn.execute(f'DELETE FROM "{table}" WHERE id=?', (int(batiment_id),))
        elif "actif" in cols:
            conn.execute(f'UPDATE "{table}" SET actif=0 WHERE id=?', (int(batiment_id),))
        else:
            conn.execute(f'DELETE FROM "{table}" WHERE id=?', (int(batiment_id),))

        conn.commit()
    finally:
        conn.close()


def _options(df: pd.DataFrame) -> dict[str, int]:
    opts = {}
    for _, row in df.iterrows():
        label = f"#{_pat_clean(row.get('id'))} — {_pat_clean(row.get('nom'), 'Sans nom')} — {_pat_clean(row.get('ville'))}"
        opts[label] = int(row["id"])
    return opts



def _first_existing_value(row: dict, keys: list[str], default: str = "") -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip() not in ["", "None", "nan"]:
            return str(value)
    return default



# PATCH 53 - Helpers prochain contrôle / entretien
def _safe_read_candidate_table(candidates: list[str]) -> pd.DataFrame:
    table = find_table(candidates, prefer_non_empty=True)
    if not table:
        return pd.DataFrame()

    try:
        return read_table(table)
    except Exception:
        return pd.DataFrame()


def _normalize_linked_dates(df: pd.DataFrame, aliases: dict[str, str]) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()

    for old, new in aliases.items():
        if old in df.columns and new not in df.columns:
            df[new] = df[old]

    if "batiment_id" not in df.columns:
        for candidate in ["id_batiment", "building_id", "id_building", "site_id"]:
            if candidate in df.columns:
                df["batiment_id"] = df[candidate]
                break

    if "date_prochain" not in df.columns:
        df["date_prochain"] = ""

    df["date_prochain_parsed"] = pd.to_datetime(df["date_prochain"], errors="coerce")

    return df


def _get_next_controle_for_batiment(batiment_id: int) -> dict | None:
    df = _safe_read_candidate_table(
        [
            "controle_batiments",
            "patrimoine_controles",
            "controles_batiments",
            "batiment_controles",
            "controles",
            "controle",
        ]
    )

    if df.empty:
        return None

    df = _normalize_linked_dates(
        df,
        {
            "controle": "type_controle",
            "type": "type_controle",
            "libelle": "type_controle",
            "libellé": "type_controle",
            "nom": "type_controle",
            "date_echeance": "date_prochain",
            "echeance": "date_prochain",
            "échéance": "date_prochain",
            "prochaine_date": "date_prochain",
            "date_validite": "date_prochain",
            "prestataire": "organisme",
            "societe": "organisme",
            "société": "organisme",
            "etat": "statut",
            "observations": "commentaire",
            "notes": "commentaire",
        },
    )

    if "batiment_id" not in df.columns:
        return None

    df["batiment_id"] = pd.to_numeric(df["batiment_id"], errors="coerce")
    filtered = df[df["batiment_id"] == int(batiment_id)].copy()

    if filtered.empty:
        return None

    if "statut" in filtered.columns:
        filtered = filtered[
            ~filtered["statut"].fillna("").astype(str).str.lower().isin(
                ["réalisé", "realise", "annulé", "annule", "terminé", "termine"]
            )
        ]

    if filtered.empty:
        return None

    upcoming = filtered[filtered["date_prochain_parsed"].notna()].copy()

    if upcoming.empty:
        return filtered.iloc[0].to_dict()

    upcoming = upcoming.sort_values("date_prochain_parsed", ascending=True)

    return upcoming.iloc[0].to_dict()


def _get_next_entretien_for_batiment(batiment_id: int) -> dict | None:
    df = _safe_read_candidate_table(
        [
            "batiment_entretiens",
            "patrimoine_entretiens",
            "entretiens_batiments",
            "batiment_maintenance",
            "entretiens",
            "maintenance",
        ]
    )

    if df.empty:
        return None

    df = _normalize_linked_dates(
        df,
        {
            "entretien": "type_entretien",
            "type": "type_entretien",
            "libelle": "type_entretien",
            "libellé": "type_entretien",
            "nom": "type_entretien",
            "date_echeance": "date_prochain",
            "echeance": "date_prochain",
            "échéance": "date_prochain",
            "prochaine_date": "date_prochain",
            "date_prevue": "date_prochain",
            "date_planifiee": "date_prochain",
            "prestataire": "fournisseur",
            "societe": "fournisseur",
            "société": "fournisseur",
            "garage": "fournisseur",
            "cout": "montant",
            "prix": "montant",
            "etat": "statut",
            "observations": "commentaire",
            "notes": "commentaire",
        },
    )

    if "batiment_id" not in df.columns:
        return None

    df["batiment_id"] = pd.to_numeric(df["batiment_id"], errors="coerce")
    filtered = df[df["batiment_id"] == int(batiment_id)].copy()

    if filtered.empty:
        return None

    if "statut" in filtered.columns:
        filtered = filtered[
            ~filtered["statut"].fillna("").astype(str).str.lower().isin(
                ["réalisé", "realise", "annulé", "annule", "terminé", "termine"]
            )
        ]

    if filtered.empty:
        return None

    upcoming = filtered[filtered["date_prochain_parsed"].notna()].copy()

    if upcoming.empty:
        return filtered.iloc[0].to_dict()

    upcoming = upcoming.sort_values("date_prochain_parsed", ascending=True)

    return upcoming.iloc[0].to_dict()


def _format_date_value(value) -> str:
    if value is None or str(value).strip() in ["", "None", "NaT", "nan"]:
        return "Non renseigné"

    try:
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            return str(value)
        return parsed.strftime("%d/%m/%Y")
    except Exception:
        return str(value)



def _get_first_value(data: dict, keys: list[str], default: str = "Non renseigné") -> str:
    for key in keys:
        value = data.get(key)
        if value is None:
            continue
        value = str(value).strip()
        if value and value.lower() not in ["none", "nan", "nat", ""]:
            return value
    return default


def _format_control_date_from_data(data: dict, keys: list[str]) -> str:
    value = _get_first_value(data, keys, "")

    if not value:
        return "Non renseigné"

    try:
        parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
        if pd.isna(parsed):
            return value
        return parsed.strftime("%d/%m/%Y")
    except Exception:
        return value


def _render_next_items_for_batiment(batiment_id: int) -> None:
    controle = _get_next_controle_for_batiment(batiment_id)
    entretien = _get_next_entretien_for_batiment(batiment_id)

    st.markdown("---")
    st.markdown("#### 📅 Suivi lié au bâtiment")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("##### ✅ Prochain contrôle")

        if not controle:
            st.info("Aucun contrôle lié ou à venir.")
        else:
            type_court = _get_first_value(
                controle,
                [
                    "type_controle",
                    "domaine",
                    "controle",
                    "contrôle",
                    "type",
                    "categorie",
                    "catégorie",
                ],
                "",
            )

            prestation = _get_first_value(
                controle,
                [
                    "detail_controle",
                    "libelle_prestation",
                    "prestation",
                    "libelle",
                    "libellé",
                    "designation",
                    "désignation",
                    "nom",
                ],
                "",
            )

            if type_court and prestation and type_court != prestation:
                type_affiche = f"{type_court} — {prestation}"
            elif prestation:
                type_affiche = prestation
            elif type_court:
                type_affiche = type_court
            else:
                type_affiche = "Non renseigné"

            date_affiche = _format_control_date_from_data(
                controle,
                [
                    "date_prochain",
                    "date_intervention",
                    "date_debut",
                    "date_controle",
                    "date_echeance",
                    "date_échéance",
                    "echeance",
                    "échéance",
                    "date_limite",
                    "date_validite",
                    "date_validité",
                ],
            )

            st.markdown(f"**Type :** {type_affiche}")
            st.markdown(f"**Date prévue :** {date_affiche}")
            st.markdown(
                f"**Statut :** {_get_first_value(controle, ['statut', 'etat', 'état'], 'Non renseigné')}"
            )
            st.markdown(
                f"**Organisme :** {_get_first_value(controle, ['organisme', 'prestataire', 'societe', 'société', 'entreprise'], 'Non renseigné')}"
            )

            reference = _get_first_value(controle, ["reference", "référence", "identifiant_activite"], "")
            if reference:
                st.caption(f"Référence : {reference}")

            commentaire = _get_first_value(controle, ["commentaire", "notes", "observations", "observation"], "")
            if commentaire:
                st.caption(commentaire)

    with c2:
        st.markdown("##### 🛠️ Prochain entretien")

        if not entretien:
            st.info("Aucun entretien lié ou à venir.")
        else:
            type_entretien = _get_first_value(
                entretien,
                [
                    "type_entretien",
                    "entretien",
                    "type",
                    "libelle",
                    "libellé",
                    "designation",
                    "désignation",
                    "nom",
                ],
                "Non renseigné",
            )

            date_entretien = _format_control_date_from_data(
                entretien,
                [
                    "date_prochain",
                    "date_intervention",
                    "date_debut",
                    "date_entretien",
                    "date_prevue",
                    "date_prévue",
                    "date_echeance",
                    "echeance",
                ],
            )

            st.markdown(f"**Type :** {type_entretien}")
            st.markdown(f"**Date prévue :** {date_entretien}")
            st.markdown(
                f"**Statut :** {_get_first_value(entretien, ['statut', 'etat', 'état'], 'Non renseigné')}"
            )
            st.markdown(
                f"**Fournisseur :** {_get_first_value(entretien, ['fournisseur', 'prestataire', 'societe', 'société', 'garage'], 'Non renseigné')}"
            )

            montant = _get_first_value(entretien, ["montant", "cout", "coût", "prix"], "")
            if montant:
                st.markdown(f"**Montant :** {montant} €")

            commentaire = _get_first_value(entretien, ["commentaire", "observations", "notes"], "")
            if commentaire:
                st.caption(commentaire)

def _render_batiment_detail_card(row: dict) -> None:
    title = _first_existing_value(row, ["nom", "designation", "libelle", "nom_batiment"], "Bâtiment sans nom")
    ref = _first_existing_value(row, ["reference", "code", "immatriculation", "numero", "id"], "")
    ville = _first_existing_value(row, ["ville", "commune"], "")
    type_bat = _first_existing_value(row, ["type_batiment", "type", "categorie"], "")

    expander_title = title
    if ref:
        expander_title = f"{ref} — {title}"
    if ville:
        expander_title = f"{expander_title} — {ville}"

    with st.expander(expander_title, expanded=False):
        img_col, info_col = st.columns([1, 2])

        with img_col:
            _display_photo(row, width=420)

        with info_col:
            c1, c2 = st.columns(2)

            with c1:
                st.markdown(f"**Nom :** {title}")
                st.markdown(f"**Type :** {type_bat}")
                st.markdown(f"**Adresse :** {_first_existing_value(row, ['adresse', 'address'])}")
                st.markdown(f"**Code postal :** {_first_existing_value(row, ['code_postal', 'cp'])}")
                st.markdown(f"**Ville :** {ville}")
                st.markdown(f"**État :** {_first_existing_value(row, ['etat', 'etat_general', 'statut'])}")

            with c2:
                st.markdown(f"**Surface :** {_first_existing_value(row, ['surface', 'surface_m2', 'surface_totale'], '0')} m²")
                st.markdown(f"**Valeur estimée :** {_first_existing_value(row, ['valeur_estimee', 'valeur', 'valeur_patrimoniale'], '0')} €")
                st.markdown(f"**Année construction :** {_first_existing_value(row, ['annee_construction', 'annee', 'construction'])}")
                st.markdown(f"**Responsable :** {_first_existing_value(row, ['responsable', 'agent', 'service'])}")
                st.markdown(f"**Téléphone :** {_first_existing_value(row, ['telephone', 'tel'])}")
                st.markdown(f"**Email :** {_first_existing_value(row, ['email', 'mail'])}")

            notes = _first_existing_value(row, ["notes", "commentaire", "commentaires", "observations"])
            if notes:
                st.markdown("**Notes :**")
                st.info(notes)

        try:
            batiment_id = int(row.get("id"))
            _render_next_items_for_batiment(batiment_id)
        except Exception as exc:
            st.warning(f"Impossible de charger le prochain contrôle / entretien : {exc}")

def render_liste() -> None:
    st.markdown("### 📋 Liste des bâtiments")

    df = load_batiments(include_inactive=True)

    if df.empty:
        st.info("Aucun bâtiment enregistré dans la table connectée.")
        return

    c1, c2, c3 = st.columns(3)

    with c1:
        search = st.text_input("🔍 Recherche", key="patrimoine_batiments_search")

    with c2:
        types = sorted([x for x in df["type_batiment"].fillna("").unique().tolist() if str(x).strip()])
        type_filter = st.selectbox("Type", ["Tous"] + types, key="patrimoine_batiments_type")

    with c3:
        statut = st.selectbox("Statut", ["Tous", "Actifs", "Inactifs"], key="patrimoine_batiments_statut")

    filtered = df.copy()

    if search:
        q = search.lower()
        mask = pd.Series(False, index=filtered.index)
        for col in filtered.columns:
            mask = mask | filtered[col].astype(str).str.lower().str.contains(q, na=False)
        filtered = filtered[mask]

    if type_filter != "Tous":
        filtered = filtered[filtered["type_batiment"] == type_filter]

    if statut == "Actifs":
        filtered = filtered[filtered["actif"] == 1]
    elif statut == "Inactifs":
        filtered = filtered[filtered["actif"] == 0]

    cols = [
        "id",
        "nom",
        "type_batiment",
        "adresse",
        "code_postal",
        "ville",
        "surface",
        "valeur_estimee",
        "etat",
        "responsable",
        "actif",
    ]
    cols = [c for c in cols if c in filtered.columns]

    st.dataframe(filtered[cols], width="stretch", hide_index=True)

    st.markdown("### 🔎 Détail bâtiments")

    if filtered.empty:
        st.info("Aucun bâtiment à afficher.")
        return

    max_items = st.slider(
        "Nombre de détails affichés",
        min_value=5,
        max_value=min(60, max(5, len(filtered))),
        value=min(10, len(filtered)),
        step=5,
        key="patrimoine_batiments_detail_count",
    )

    detail_df = filtered.head(max_items)

    for _, row in detail_df.iterrows():
        _render_batiment_detail_card(row.to_dict())

def render_ajouter() -> None:
    st.markdown("### ➕ Ajouter un bâtiment")

    with st.form("patrimoine_add_batiment"):
        c1, c2 = st.columns(2)

        with c1:
            nom = st.text_input("Nom du bâtiment *")
            type_batiment = st.text_input("Type")
            adresse = st.text_input("Adresse")
            code_postal = st.text_input("Code postal")
            ville = st.text_input("Ville", value="Marly")

        with c2:
            surface = st.number_input("Surface m²", min_value=0.0, step=10.0)
            valeur_estimee = st.number_input("Valeur estimée €", min_value=0.0, step=1000.0)
            annee_construction = st.number_input("Année construction", min_value=0, max_value=2100, step=1)
            etat = st.text_input("État", value="Bon")
            responsable = st.text_input("Responsable")

        c3, c4 = st.columns(2)

        with c3:
            telephone = st.text_input("Téléphone")

        with c4:
            email = st.text_input("Email")

        uploaded = st.file_uploader(
            "Image du bâtiment",
            type=["jpg", "jpeg", "png", "webp"],
            key="patrimoine_add_photo",
        )

        notes = st.text_area("Notes")
        submitted = st.form_submit_button("💾 Ajouter le bâtiment", width="stretch")

    if submitted:
        if not nom.strip():
            st.error("Le nom du bâtiment est obligatoire.")
            return

        photo_path = ""
        if uploaded is not None:
            photo_path = _save_uploaded_photo(uploaded)

        new_id = add_batiment(
            {
                "nom": nom.strip(),
                "type_batiment": type_batiment,
                "adresse": adresse,
                "code_postal": code_postal,
                "ville": ville,
                "surface": surface,
                "valeur_estimee": valeur_estimee,
                "annee_construction": annee_construction if annee_construction else None,
                "etat": etat,
                "responsable": responsable,
                "telephone": telephone,
                "email": email,
                "photo_path": photo_path,
                "notes": notes,
            }
        )

        if uploaded is not None and photo_path:
            fixed_photo_path = _save_uploaded_photo(uploaded, new_id)
            update_batiment(new_id, {"photo_path": fixed_photo_path})

        st.success("Bâtiment ajouté.")
        st.rerun()


def render_modifier() -> None:
    st.markdown("### ✏️ Modifier / supprimer un bâtiment")

    df = load_batiments(include_inactive=True)

    if df.empty:
        st.info("Aucun bâtiment disponible.")
        return

    opts = _options(df)
    selected = st.selectbox("Bâtiment", list(opts.keys()))
    batiment_id = opts[selected]

    row = df[df["id"] == batiment_id].iloc[0].to_dict()

    st.markdown("#### Image actuelle")
    _display_photo(row, width=300)

    with st.form(f"patrimoine_edit_batiment_{batiment_id}"):
        c1, c2 = st.columns(2)

        with c1:
            nom = st.text_input("Nom du bâtiment *", value=_pat_clean(row.get("nom")))
            type_batiment = st.text_input("Type", value=_pat_clean(row.get("type_batiment")))
            adresse = st.text_input("Adresse", value=_pat_clean(row.get("adresse")))
            code_postal = st.text_input("Code postal", value=_pat_clean(row.get("code_postal")))
            ville = st.text_input("Ville", value=_pat_clean(row.get("ville")))

        with c2:
            surface = st.number_input("Surface m²", value=_pat_safe_float(row.get("surface")), step=10.0)
            valeur_estimee = st.number_input("Valeur estimée €", value=_pat_safe_float(row.get("valeur_estimee")), step=1000.0)
            annee_val = _pat_safe_int(row.get("annee_construction"))
            annee_construction = st.number_input("Année construction", value=annee_val, min_value=0, max_value=2100, step=1)
            etat = st.text_input("État", value=_pat_clean(row.get("etat")))
            responsable = st.text_input("Responsable", value=_pat_clean(row.get("responsable")))

        c3, c4 = st.columns(2)

        with c3:
            telephone = st.text_input("Téléphone", value=_pat_clean(row.get("telephone")))

        with c4:
            email = st.text_input("Email", value=_pat_clean(row.get("email")))

        uploaded = st.file_uploader(
            "Nouvelle image du bâtiment",
            type=["jpg", "jpeg", "png", "webp"],
            key=f"patrimoine_edit_photo_{batiment_id}",
        )

        actif = st.checkbox("Actif", value=bool(row.get("actif", 1)))
        notes = st.text_area("Notes", value=_pat_clean(row.get("notes")))

        submitted = st.form_submit_button("💾 Enregistrer les modifications", width="stretch")

    if submitted:
        if not nom.strip():
            st.error("Le nom est obligatoire.")
            return

        photo_path = ""
        if uploaded is not None:
            photo_path = _save_uploaded_photo(uploaded, batiment_id)

        update_batiment(
            batiment_id,
            {
                "nom": nom.strip(),
                "type_batiment": type_batiment,
                "adresse": adresse,
                "code_postal": code_postal,
                "ville": ville,
                "surface": surface,
                "valeur_estimee": valeur_estimee,
                "annee_construction": annee_construction if annee_construction else None,
                "etat": etat,
                "responsable": responsable,
                "telephone": telephone,
                "email": email,
                "actif": actif,
                "photo_path": photo_path,
                "notes": notes,
            },
        )
        st.success("Bâtiment modifié.")
        st.rerun()

    st.divider()
    st.markdown("### 🗑️ Suppression")

    c1, c2 = st.columns(2)

    with c1:
        confirm_soft = st.checkbox("Confirmer la désactivation", key=f"pat_bat_soft_{batiment_id}")
        if st.button("Désactiver", disabled=not confirm_soft, width="stretch"):
            delete_batiment(batiment_id, hard_delete=False)
            st.success("Bâtiment désactivé.")
            st.rerun()

    with c2:
        confirm_hard = st.checkbox("Confirmer suppression définitive", key=f"pat_bat_hard_{batiment_id}")
        if st.button("Supprimer définitivement", disabled=not confirm_hard, width="stretch"):
            delete_batiment(batiment_id, hard_delete=True)
            st.success("Bâtiment supprimé.")
            st.rerun()


def render_export() -> None:
    st.markdown("### 📥 Export bâtiments")

    df = load_batiments(include_inactive=True)

    if df.empty:
        st.info("Aucun bâtiment à exporter.")
        return

    st.download_button(
        "📥 Export CSV bâtiments",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name="patrimoine_batiments.csv",
        mime="text/csv",
        width="stretch",
    )


def render_diagnostic() -> None:
    st.markdown("### 🔍 Diagnostic bâtiments")

    st.write(f"**Base utilisée :** `{get_db_path()}`")
    st.write(f"**Table bâtiments utilisée :** `{_current_table()}`")
    st.write(f"**Nombre de lignes table :** `{count_table(_current_table())}`")
    st.write(f"**Dossier photos :** `{PHOTOS_DIR}`")
    st.write("**Tables détectées :**", get_tables())

    st.dataframe(diagnostics(), width="stretch", hide_index=True)


def render() -> None:
    init_db()

    st.markdown("### 🏢 Gestion des bâtiments")
    st.caption(f"Base : {get_db_path()} — table : {_current_table()}")

    tabs = st.tabs(
        [
            "📋 Liste / Détail",
            "➕ Ajouter",
            "✏️ Modifier / Supprimer",
            "📥 Export",
            "🔍 Diagnostic",
        ]
    )

    with tabs[0]:
        render_liste()

    with tabs[1]:
        render_ajouter()

    with tabs[2]:
        render_modifier()

    with tabs[3]:
        render_export()

    with tabs[4]:
        render_diagnostic()


def show() -> None:
    render()
