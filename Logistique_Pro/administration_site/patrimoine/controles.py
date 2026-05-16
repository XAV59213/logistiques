# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
import streamlit as st

from .batiments import load_batiments
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


CONTROLE_TABLE_CANDIDATES = [
    "controle_batiments",
    "patrimoine_controles",
    "controles",
    "controle",
    "batiment_controles",
]


def _current_table() -> str:
    table = find_table(CONTROLE_TABLE_CANDIDATES, prefer_non_empty=True)

    if table:
        return table

    conn = connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS controle_batiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campagne_id INTEGER,
                batiment_id INTEGER,
                identifiant_activite TEXT DEFAULT '',
                reference TEXT DEFAULT '',
                domaine TEXT DEFAULT '',
                date_debut TEXT DEFAULT '',
                date_intervention TEXT DEFAULT '',
                statut TEXT DEFAULT '',
                nom_site TEXT DEFAULT '',
                ville_site TEXT DEFAULT '',
                libelle_prestation TEXT DEFAULT '',
                livrables INTEGER DEFAULT 0,
                nombre_documents INTEGER DEFAULT 0,
                organisme TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                actif INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    return "controle_batiments"


def _ensure_schema() -> None:
    table = _current_table()

    required = {
        "type_controle": "type_controle TEXT",
        "date_controle": "date_controle TEXT",
        "date_prochain": "date_prochain TEXT",
        "resultat": "resultat TEXT",
        "commentaire": "commentaire TEXT",
        "updated_at": "updated_at TEXT",
    }

    for col, sql in required.items():
        try:
            add_column_if_missing(table, col, sql)
        except Exception:
            pass


def init_db() -> None:
    _ensure_schema()


def _clean_text(value) -> str:
    if value is None:
        return ""
    value = str(value)
    if value.lower() in ["none", "nan", "nat"]:
        return ""
    return value.strip()


def _is_empty_series(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().isin(["", "None", "nan", "NaT"])


def _to_date(value):
    value = _clean_text(value)

    if not value:
        return None

    try:
        parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
        if pd.isna(parsed):
            return None
        return parsed.date()
    except Exception:
        return None


def _format_date(value) -> str:
    d = _to_date(value)
    if not d:
        return _clean_text(value)
    return d.strftime("%d/%m/%Y")


def _normalize_controles(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()

    if "id" not in df.columns:
        df["id"] = range(1, len(df) + 1)

    if "batiment_id" not in df.columns:
        df["batiment_id"] = None

    # IMPORTANT :
    # ta vraie base contient les infos dans domaine/libelle_prestation/date_intervention,
    # tandis que type_controle/date_controle/date_prochain existent mais sont vides.
    if "type_controle" not in df.columns:
        df["type_controle"] = ""

    if "domaine" in df.columns:
        mask = _is_empty_series(df["type_controle"])
        df.loc[mask, "type_controle"] = df.loc[mask, "domaine"]

    if "libelle_prestation" in df.columns:
        if "detail_controle" not in df.columns:
            df["detail_controle"] = df["libelle_prestation"]
        mask = _is_empty_series(df["type_controle"])
        df.loc[mask, "type_controle"] = df.loc[mask, "libelle_prestation"]

    if "date_controle" not in df.columns:
        df["date_controle"] = ""

    if "date_intervention" in df.columns:
        mask = _is_empty_series(df["date_controle"])
        df.loc[mask, "date_controle"] = df.loc[mask, "date_intervention"]

    if "date_debut" in df.columns:
        mask = _is_empty_series(df["date_controle"])
        df.loc[mask, "date_controle"] = df.loc[mask, "date_debut"]

    if "date_prochain" not in df.columns:
        df["date_prochain"] = ""

    if "date_intervention" in df.columns:
        mask = _is_empty_series(df["date_prochain"])
        df.loc[mask, "date_prochain"] = df.loc[mask, "date_intervention"]

    if "date_debut" in df.columns:
        mask = _is_empty_series(df["date_prochain"])
        df.loc[mask, "date_prochain"] = df.loc[mask, "date_debut"]

    if "organisme" not in df.columns:
        df["organisme"] = ""

    if "statut" not in df.columns:
        df["statut"] = ""

    if "resultat" not in df.columns:
        df["resultat"] = ""

    if "commentaire" not in df.columns:
        df["commentaire"] = ""

    if "notes" in df.columns:
        mask = _is_empty_series(df["commentaire"])
        df.loc[mask, "commentaire"] = df.loc[mask, "notes"]

    if "reference" not in df.columns:
        df["reference"] = ""

    if "identifiant_activite" not in df.columns:
        df["identifiant_activite"] = ""

    if "nom_site" not in df.columns:
        df["nom_site"] = ""

    if "ville_site" not in df.columns:
        df["ville_site"] = ""

    df["date_prochain_parsed"] = df["date_prochain"].apply(_to_date)
    df["_col_type_detectee"] = "domaine / libelle_prestation"
    df["_col_date_controle_detectee"] = "date_intervention / date_debut"
    df["_col_date_prochain_detectee"] = "date_intervention / date_debut"

    return df


def _join_batiments(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    batiments = load_batiments(include_inactive=True)

    if not batiments.empty and "batiment_id" in df.columns:
        df["batiment_id"] = pd.to_numeric(df["batiment_id"], errors="coerce")

        bdf = batiments.copy()

        if "id" not in bdf.columns:
            bdf["id"] = range(1, len(bdf) + 1)

        if "nom" not in bdf.columns:
            bdf["nom"] = ""

        if "type_batiment" not in bdf.columns:
            bdf["type_batiment"] = ""

        if "ville" not in bdf.columns:
            bdf["ville"] = ""

        bdf = bdf[["id", "nom", "type_batiment", "ville"]].rename(
            columns={"id": "batiment_id", "nom": "batiment_nom"}
        )

        df = df.merge(bdf, on="batiment_id", how="left")

    if "batiment_nom" not in df.columns:
        df["batiment_nom"] = ""

    # Si la liaison ID ne trouve rien, on garde le nom importé depuis Veritas.
    if "nom_site" in df.columns:
        mask = df["batiment_nom"].fillna("").astype(str).str.strip().isin(["", "None", "nan"])
        df.loc[mask, "batiment_nom"] = df.loc[mask, "nom_site"]

    if "ville" not in df.columns:
        df["ville"] = ""

    if "ville_site" in df.columns:
        mask = df["ville"].fillna("").astype(str).str.strip().isin(["", "None", "nan"])
        df.loc[mask, "ville"] = df.loc[mask, "ville_site"]

    df["batiment_nom"] = df["batiment_nom"].fillna("Non lié").replace("", "Non lié")

    return df


def load_controles() -> pd.DataFrame:
    _ensure_schema()
    table = _current_table()

    try:
        df = read_table(table)
    except Exception:
        return pd.DataFrame()

    if df.empty:
        return df

    df = _normalize_controles(df)
    df = _join_batiments(df)

    return df.sort_values("id", ascending=False)


def get_controle(controle_id: int) -> dict[str, Any] | None:
    df = load_controles()

    if df.empty:
        return None

    row = df[df["id"] == int(controle_id)]

    if row.empty:
        return None

    return row.iloc[0].to_dict()


def add_controle(data: dict[str, Any]) -> None:
    _ensure_schema()
    table = _current_table()
    cols = table_columns(table)

    payload = {
        "batiment_id": int(data.get("batiment_id")) if data.get("batiment_id") else None,
        "domaine": data.get("type_controle"),
        "libelle_prestation": data.get("detail_controle") or data.get("type_controle"),
        "date_debut": data.get("date_controle"),
        "date_intervention": data.get("date_prochain") or data.get("date_controle"),
        "organisme": data.get("organisme"),
        "statut": data.get("statut"),
        "notes": data.get("commentaire"),
        "type_controle": data.get("type_controle"),
        "date_controle": data.get("date_controle"),
        "date_prochain": data.get("date_prochain"),
        "resultat": data.get("resultat"),
        "commentaire": data.get("commentaire"),
        "actif": 1,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    payload = {k: v for k, v in payload.items() if k in cols}

    conn = connect()
    try:
        columns = ", ".join([f'"{k}"' for k in payload.keys()])
        placeholders = ", ".join(["?"] * len(payload))
        conn.execute(
            f'INSERT INTO "{table}" ({columns}) VALUES ({placeholders})',
            tuple(payload.values()),
        )
        conn.commit()
    finally:
        conn.close()


def update_controle(controle_id: int, data: dict[str, Any]) -> None:
    _ensure_schema()
    table = _current_table()
    cols = table_columns(table)

    payload = {
        "batiment_id": int(data.get("batiment_id")) if data.get("batiment_id") else None,
        "domaine": data.get("type_controle"),
        "libelle_prestation": data.get("detail_controle") or data.get("type_controle"),
        "date_debut": data.get("date_controle"),
        "date_intervention": data.get("date_prochain") or data.get("date_controle"),
        "organisme": data.get("organisme"),
        "statut": data.get("statut"),
        "notes": data.get("commentaire"),
        "type_controle": data.get("type_controle"),
        "date_controle": data.get("date_controle"),
        "date_prochain": data.get("date_prochain"),
        "resultat": data.get("resultat"),
        "commentaire": data.get("commentaire"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    payload = {k: v for k, v in payload.items() if k in cols}

    conn = connect()
    try:
        set_clause = ", ".join([f'"{k}"=?' for k in payload.keys()])
        conn.execute(
            f'UPDATE "{table}" SET {set_clause} WHERE id=?',
            tuple(payload.values()) + (int(controle_id),),
        )
        conn.commit()
    finally:
        conn.close()


def delete_controle(controle_id: int) -> None:
    _ensure_schema()
    table = _current_table()

    conn = connect()
    try:
        conn.execute(f'DELETE FROM "{table}" WHERE id=?', (int(controle_id),))
        conn.commit()
    finally:
        conn.close()


def _batiment_options() -> dict[str, int]:
    df = load_batiments(include_inactive=False)
    options = {}

    for _, row in df.iterrows():
        label = f"#{row['id']} — {row.get('nom') or 'Sans nom'} — {row.get('ville') or ''}"
        options[label] = int(row["id"])

    return options


def _controle_options(df: pd.DataFrame) -> dict[str, int]:
    options = {}

    for _, row in df.iterrows():
        label = f"#{row['id']} — {row.get('batiment_nom') or 'Non lié'} — {row.get('type_controle') or ''} — {_format_date(row.get('date_prochain'))}"
        options[label] = int(row["id"])

    return options


def render_liste() -> None:
    st.markdown("### 📋 Liste des contrôles")

    df = load_controles()

    if df.empty:
        st.info("Aucun contrôle enregistré dans la table connectée.")
        render_diagnostic()
        return

    c1, c2, c3 = st.columns(3)

    with c1:
        search = st.text_input("🔍 Recherche", key="patrimoine_controles_search")

    with c2:
        only_linked = st.checkbox("Afficher seulement les contrôles liés", value=False)

    with c3:
        show_columns = st.checkbox("Voir colonnes techniques", value=False)

    filtered = df.copy()

    if only_linked:
        filtered = filtered[filtered["batiment_nom"].fillna("").astype(str) != "Non lié"]

    if search:
        q = search.lower()
        mask = pd.Series(False, index=filtered.index)
        for col in filtered.columns:
            mask = mask | filtered[col].astype(str).str.lower().str.contains(q, na=False)
        filtered = filtered[mask]

    display = filtered.copy()
    display["date_controle"] = display["date_controle"].apply(_format_date)
    display["date_prochain"] = display["date_prochain"].apply(_format_date)

    cols = [
        "id",
        "batiment_nom",
        "type_controle",
        "detail_controle",
        "date_controle",
        "date_prochain",
        "organisme",
        "statut",
        "reference",
        "identifiant_activite",
        "commentaire",
    ]

    if show_columns:
        cols = list(display.columns)

    cols = [c for c in cols if c in display.columns]

    st.caption(f"{len(display)} contrôle(s) affiché(s) sur {len(df)}")
    st.dataframe(display[cols], width="stretch", hide_index=True)

    st.markdown("### 🔎 Détail contrôle")

    opts = _controle_options(filtered)

    if not opts:
        st.info("Aucun contrôle à détailler.")
        return

    selected = st.selectbox("Sélectionner un contrôle", list(opts.keys()), key="patrimoine_controle_detail_select")
    controle = get_controle(opts[selected])

    if not controle:
        st.warning("Contrôle introuvable.")
        return

    c1, c2, c3 = st.columns(3)

    with c1:
        st.write(f"**Domaine :** {controle.get('type_controle', '')}")
        st.write(f"**Prestation :** {controle.get('detail_controle', '')}")
        st.write(f"**Bâtiment :** {controle.get('batiment_nom', 'Non lié')}")

    with c2:
        st.write(f"**Date début :** {_format_date(controle.get('date_controle', ''))}")
        st.write(f"**Date intervention :** {_format_date(controle.get('date_prochain', ''))}")
        st.write(f"**Organisme :** {controle.get('organisme', '')}")

    with c3:
        st.write(f"**Statut :** {controle.get('statut', '')}")
        st.write(f"**Référence :** {controle.get('reference', '')}")
        st.write(f"**Activité :** {controle.get('identifiant_activite', '')}")

    commentaire = _clean_text(controle.get("commentaire"))
    if commentaire:
        st.info(commentaire)

    with st.expander("🔍 Données brutes du contrôle", expanded=False):
        st.json({k: str(v) for k, v in controle.items()})


def render_ajouter() -> None:
    st.markdown("### ➕ Ajouter un contrôle")

    options = _batiment_options()

    if not options:
        st.warning("Tu dois d'abord avoir au moins un bâtiment.")
        return

    with st.form("patrimoine_add_controle"):
        selected_bat = st.selectbox("Bâtiment", list(options.keys()))

        c1, c2 = st.columns(2)

        with c1:
            type_controle = st.text_input("Domaine", value="Électricité")
            detail_controle = st.text_input("Prestation", value="Vérification périodique annuelle")
            date_controle = st.date_input("Date début", value=date.today())
            date_prochain = st.date_input("Date intervention", value=None)

        with c2:
            organisme = st.text_input("Organisme")
            statut = st.selectbox("Statut", ["Planifiée", "Réalisée", "À surveiller", "En retard", "Annulée"])
            resultat = st.text_input("Résultat")

        commentaire = st.text_area("Commentaire")
        submitted = st.form_submit_button("💾 Enregistrer le contrôle", width="stretch")

    if submitted:
        add_controle(
            {
                "batiment_id": options[selected_bat],
                "type_controle": type_controle,
                "detail_controle": detail_controle,
                "date_controle": date_controle.isoformat() if date_controle else "",
                "date_prochain": date_prochain.isoformat() if date_prochain else "",
                "organisme": organisme,
                "statut": statut,
                "resultat": resultat,
                "commentaire": commentaire,
            }
        )
        st.success("Contrôle ajouté.")
        st.rerun()


def render_modifier() -> None:
    st.markdown("### ✏️ Modifier / supprimer un contrôle")

    df = load_controles()
    options_bat = _batiment_options()

    if df.empty:
        st.info("Aucun contrôle disponible.")
        return

    if not options_bat:
        st.warning("Aucun bâtiment disponible.")
        return

    controle_options = _controle_options(df)
    selected_controle = st.selectbox("Contrôle", list(controle_options.keys()))
    controle_id = controle_options[selected_controle]
    row = df[df["id"] == controle_id].iloc[0].to_dict()

    batiment_id_actuel = row.get("batiment_id")
    bat_labels = list(options_bat.keys())
    bat_values = list(options_bat.values())

    try:
        default_index = bat_values.index(int(float(batiment_id_actuel)))
    except Exception:
        default_index = 0

    with st.form(f"patrimoine_edit_controle_{controle_id}"):
        selected_bat = st.selectbox("Bâtiment", bat_labels, index=default_index)

        c1, c2 = st.columns(2)

        with c1:
            type_controle = st.text_input("Domaine", value=str(row.get("type_controle") or ""))
            detail_controle = st.text_input("Prestation", value=str(row.get("detail_controle") or ""))
            date_controle = st.text_input("Date début", value=str(row.get("date_controle") or ""))
            date_prochain = st.text_input("Date intervention", value=str(row.get("date_prochain") or ""))

        with c2:
            organisme = st.text_input("Organisme", value=str(row.get("organisme") or ""))
            current_statut = str(row.get("statut") or "Planifiée")
            statuts = ["Planifiée", "Réalisée", "À surveiller", "En retard", "Annulée"]
            index_statut = statuts.index(current_statut) if current_statut in statuts else 0
            statut = st.selectbox("Statut", statuts, index=index_statut)
            resultat = st.text_input("Résultat", value=str(row.get("resultat") or ""))

        commentaire = st.text_area("Commentaire", value=str(row.get("commentaire") or ""))
        submitted = st.form_submit_button("💾 Enregistrer les modifications", width="stretch")

    if submitted:
        update_controle(
            controle_id,
            {
                "batiment_id": options_bat[selected_bat],
                "type_controle": type_controle,
                "detail_controle": detail_controle,
                "date_controle": date_controle,
                "date_prochain": date_prochain,
                "organisme": organisme,
                "statut": statut,
                "resultat": resultat,
                "commentaire": commentaire,
            },
        )
        st.success("Contrôle modifié.")
        st.rerun()

    confirm = st.checkbox("Confirmer la suppression", key=f"delete_controle_{controle_id}")

    if st.button("🗑️ Supprimer le contrôle", disabled=not confirm, width="stretch"):
        delete_controle(controle_id)
        st.success("Contrôle supprimé.")
        st.rerun()


def render_alertes() -> None:
    st.markdown("### 🚨 Alertes contrôles")

    df = load_controles()

    if df.empty:
        st.info("Aucun contrôle enregistré.")
        return

    today = date.today()
    limit = today + timedelta(days=30)

    df = df.copy()
    df["date_prochain_parsed"] = df["date_prochain"].apply(_to_date)

    statuts = df["statut"].fillna("").astype(str) if "statut" in df.columns else pd.Series([""] * len(df))
    active = ~statuts.str.lower().isin(["réalisé", "realise", "réalisée", "realisee", "annulé", "annule", "annulée", "annulee", "terminé", "termine"])

    retard = df[
        df["date_prochain_parsed"].notna()
        & (df["date_prochain_parsed"] < today)
        & active
    ]

    avenir = df[
        df["date_prochain_parsed"].notna()
        & (df["date_prochain_parsed"] >= today)
        & (df["date_prochain_parsed"] <= limit)
        & active
    ]

    c1, c2, c3 = st.columns(3)
    c1.metric("Contrôles", len(df))
    c2.metric("En retard", len(retard))
    c3.metric("À venir 30j", len(avenir))

    if not retard.empty:
        st.error("Contrôles en retard")
        st.dataframe(retard, width="stretch", hide_index=True)
    else:
        st.success("Aucun contrôle en retard.")

    if not avenir.empty:
        st.warning("Contrôles à venir")
        st.dataframe(avenir, width="stretch", hide_index=True)


def render_diagnostic() -> None:
    st.markdown("### 🔍 Diagnostic contrôles")

    table = _current_table()

    st.write(f"**Base utilisée :** `{get_db_path()}`")
    st.write(f"**Table contrôles utilisée :** `{table}`")
    st.write(f"**Nombre de lignes table contrôles :** `{count_table(table)}`")
    st.write(f"**Colonnes contrôles :** `{table_columns(table)}`")

    df_raw = read_table(table)
    st.markdown("#### Aperçu brut")
    st.dataframe(df_raw.head(20), width="stretch", hide_index=True)

    df = load_controles()
    st.markdown("#### Aperçu corrigé")
    cols = [
        "id",
        "batiment_id",
        "batiment_nom",
        "type_controle",
        "detail_controle",
        "date_controle",
        "date_prochain",
        "organisme",
        "statut",
        "reference",
        "identifiant_activite",
    ]
    cols = [c for c in cols if c in df.columns]
    st.dataframe(df[cols].head(20), width="stretch", hide_index=True)

    st.markdown("#### Toutes les tables")
    st.dataframe(diagnostics(), width="stretch", hide_index=True)


def render() -> None:
    init_db()

    st.markdown("### ✅ Contrôles patrimoine")
    st.caption(f"Base : {get_db_path()} — table : {_current_table()} — lignes : {count_table(_current_table())}")

    tabs = st.tabs(
        [
            "📋 Liste / Détail",
            "➕ Ajouter",
            "✏️ Modifier / Supprimer",
            "🚨 Alertes",
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
        render_alertes()

    with tabs[4]:
        render_diagnostic()


def show() -> None:
    render()
