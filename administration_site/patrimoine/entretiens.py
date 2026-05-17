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


ENTRETIEN_TABLE_CANDIDATES = [
    "batiment_entretiens",
    "patrimoine_entretiens",
    "entretiens_batiments",
    "batiment_maintenance",
    "entretiens",
    "maintenance",
]

TYPE_TABLE_CANDIDATES = [
    "entretien_types",
    "types_entretiens",
    "maintenance_types",
    "patrimoine_entretien_types",
]


def _current_table() -> str:
    table = find_table(ENTRETIEN_TABLE_CANDIDATES, prefer_non_empty=True)

    if table:
        return table

    conn = connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS batiment_entretiens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batiment_id INTEGER,
                type_entretien TEXT DEFAULT '',
                type_id INTEGER,
                date_entretien TEXT DEFAULT '',
                date_prochain TEXT DEFAULT '',
                fournisseur TEXT DEFAULT '',
                montant REAL DEFAULT 0,
                statut TEXT DEFAULT 'Planifié',
                commentaire TEXT DEFAULT '',
                actif INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    return "batiment_entretiens"


def _type_table() -> str | None:
    return find_table(TYPE_TABLE_CANDIDATES, prefer_non_empty=False)


def _ensure_schema() -> None:
    table = _current_table()

    required = {
        "batiment_id": "batiment_id INTEGER",
        "type_entretien": "type_entretien TEXT DEFAULT ''",
        "type_id": "type_id INTEGER",
        "date_entretien": "date_entretien TEXT DEFAULT ''",
        "date_prochain": "date_prochain TEXT DEFAULT ''",
        "fournisseur": "fournisseur TEXT DEFAULT ''",
        "montant": "montant REAL DEFAULT 0",
        "statut": "statut TEXT DEFAULT 'Planifié'",
        "commentaire": "commentaire TEXT DEFAULT ''",
        "actif": "actif INTEGER DEFAULT 1",
        "created_at": "created_at TEXT DEFAULT CURRENT_TIMESTAMP",
        "updated_at": "updated_at TEXT",
    }

    for col, sql in required.items():
        try:
            add_column_if_missing(table, col, sql)
        except Exception:
            pass

    # Crée une table de types si aucune n'existe
    if not _type_table():
        conn = connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS entretien_types (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nom TEXT NOT NULL,
                    periodicite_mois INTEGER DEFAULT 12,
                    actif INTEGER DEFAULT 1
                )
                """
            )
            defaults = [
                ("Chauffage / chaudière", 12),
                ("Climatisation / ventilation", 12),
                ("Toiture / étanchéité", 24),
                ("Extincteurs", 12),
                ("Électricité", 12),
                ("Plomberie", 12),
                ("Ascenseur", 6),
                ("Sécurité incendie", 12),
                ("Nettoyage technique", 12),
                ("Contrôle général bâtiment", 12),
            ]
            existing = conn.execute("SELECT COUNT(*) FROM entretien_types").fetchone()[0]
            if existing == 0:
                conn.executemany(
                    "INSERT INTO entretien_types (nom, periodicite_mois, actif) VALUES (?, ?, 1)",
                    defaults,
                )
            conn.commit()
        finally:
            conn.close()


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


def _first_existing_col(cols: list[str], candidates: list[str]) -> str | None:
    lower_map = {c.lower(): c for c in cols}

    for candidate in candidates:
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]

    for col in cols:
        col_lower = col.lower()
        for candidate in candidates:
            if candidate.lower() in col_lower:
                return col

    return None


def load_entretien_types() -> pd.DataFrame:
    init_db()
    table = _type_table()

    if not table:
        return pd.DataFrame(columns=["id", "nom", "periodicite_mois"])

    try:
        df = read_table(table)
    except Exception:
        return pd.DataFrame(columns=["id", "nom", "periodicite_mois"])

    if df.empty:
        return pd.DataFrame(columns=["id", "nom", "periodicite_mois"])

    cols = list(df.columns)

    if "id" not in df.columns:
        df["id"] = range(1, len(df) + 1)

    label_col = _first_existing_col(
        cols,
        ["nom", "libelle", "libellé", "designation", "désignation", "type", "titre", "entretien"],
    )

    if label_col and "nom" not in df.columns:
        df["nom"] = df[label_col]

    if "nom" not in df.columns:
        df["nom"] = ""

    period_col = _first_existing_col(
        cols,
        ["periodicite_mois", "périodicité_mois", "periodicite", "périodicité", "mois"],
    )

    if period_col and "periodicite_mois" not in df.columns:
        df["periodicite_mois"] = df[period_col]

    if "periodicite_mois" not in df.columns:
        df["periodicite_mois"] = 12

    if "actif" in df.columns:
        df = df[pd.to_numeric(df["actif"], errors="coerce").fillna(1).astype(int) == 1]

    df["nom"] = df["nom"].fillna("").astype(str)
    df["periodicite_mois"] = pd.to_numeric(df["periodicite_mois"], errors="coerce").fillna(12).astype(int)

    return df[["id", "nom", "periodicite_mois"]].sort_values("nom")


def _type_map() -> dict[str, str]:
    df = load_entretien_types()

    if df.empty:
        return {}

    return {str(row["id"]): str(row["nom"]) for _, row in df.iterrows()}


def _normalize_entretiens(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    cols = list(df.columns)

    if "id" not in df.columns:
        df["id"] = range(1, len(df) + 1)

    # Liaison bâtiment
    bat_col = _first_existing_col(
        cols,
        [
            "batiment_id",
            "id_batiment",
            "id_bat",
            "building_id",
            "site_id",
            "id_site",
            "batiment",
            "bâtiment",
        ],
    )

    if bat_col and "batiment_id" not in df.columns:
        df["batiment_id"] = df[bat_col]

    if "batiment_id" not in df.columns:
        df["batiment_id"] = None

    # Type entretien
    type_col = _first_existing_col(
        cols,
        [
            "type_entretien",
            "entretien",
            "type",
            "categorie",
            "catégorie",
            "libelle",
            "libellé",
            "designation",
            "désignation",
            "nom",
            "titre",
            "objet",
        ],
    )

    if type_col:
        df["type_entretien"] = df[type_col]
    elif "type_entretien" not in df.columns:
        df["type_entretien"] = ""

    type_id_col = _first_existing_col(
        cols,
        [
            "type_id",
            "id_type",
            "entretien_type_id",
            "type_entretien_id",
            "id_type_entretien",
        ],
    )

    mapping = _type_map()

    if type_id_col and mapping:
        mapped = df[type_id_col].astype(str).map(mapping)
        mask = _is_empty_series(df["type_entretien"])
        df.loc[mask, "type_entretien"] = mapped

    # Dates
    date_entretien_col = _first_existing_col(
        cols,
        [
            "date_entretien",
            "date_intervention",
            "date_realisation",
            "date_réalisation",
            "date_debut",
            "date_début",
            "date",
        ],
    )

    if date_entretien_col:
        df["date_entretien"] = df[date_entretien_col]
    elif "date_entretien" not in df.columns:
        df["date_entretien"] = ""

    date_prochain_col = _first_existing_col(
        cols,
        [
            "date_prochain",
            "date_prochaine",
            "date_prevue",
            "date_prévue",
            "date_echeance",
            "date_échéance",
            "echeance",
            "échéance",
            "date_limite",
            "prochain_entretien",
            "prochaine_intervention",
        ],
    )

    if date_prochain_col:
        df["date_prochain"] = df[date_prochain_col]
    elif "date_prochain" not in df.columns:
        df["date_prochain"] = ""

    # Si pas de prochaine date, mais une date entretien + type avec périodicité, on peut laisser vide pour éviter une fausse donnée.
    # Fournisseur
    fournisseur_col = _first_existing_col(
        cols,
        [
            "fournisseur",
            "prestataire",
            "societe",
            "société",
            "entreprise",
            "garage",
            "organisme",
        ],
    )

    if fournisseur_col:
        df["fournisseur"] = df[fournisseur_col]
    elif "fournisseur" not in df.columns:
        df["fournisseur"] = ""

    # Montant
    montant_col = _first_existing_col(
        cols,
        ["montant", "cout", "coût", "prix", "tarif", "total"],
    )

    if montant_col:
        df["montant"] = df[montant_col]
    elif "montant" not in df.columns:
        df["montant"] = 0

    # Statut
    statut_col = _first_existing_col(cols, ["statut", "etat", "état", "status", "avancement"])

    if statut_col:
        df["statut"] = df[statut_col]
    elif "statut" not in df.columns:
        df["statut"] = "Planifié"

    # Commentaire
    commentaire_col = _first_existing_col(
        cols,
        ["commentaire", "commentaires", "notes", "note", "observations", "observation", "remarque"],
    )

    if commentaire_col:
        df["commentaire"] = df[commentaire_col]
    elif "commentaire" not in df.columns:
        df["commentaire"] = ""

    if "actif" not in df.columns:
        df["actif"] = 1

    df["montant"] = pd.to_numeric(df["montant"], errors="coerce").fillna(0)
    df["date_prochain_parsed"] = df["date_prochain"].apply(_to_date)
    df["date_entretien_parsed"] = df["date_entretien"].apply(_to_date)

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

        if "ville" not in bdf.columns:
            bdf["ville"] = ""

        if "type_batiment" not in bdf.columns:
            bdf["type_batiment"] = ""

        bdf = bdf[["id", "nom", "type_batiment", "ville"]].rename(
            columns={"id": "batiment_id", "nom": "batiment_nom"}
        )

        df = df.merge(bdf, on="batiment_id", how="left")

    if "batiment_nom" not in df.columns:
        df["batiment_nom"] = ""

    df["batiment_nom"] = df["batiment_nom"].fillna("Non lié").replace("", "Non lié")

    return df


def load_entretiens() -> pd.DataFrame:
    init_db()
    table = _current_table()

    try:
        df = read_table(table)
    except Exception:
        return pd.DataFrame()

    if df.empty:
        return df

    df = _normalize_entretiens(df)
    df = _join_batiments(df)

    if "actif" in df.columns:
        df = df[pd.to_numeric(df["actif"], errors="coerce").fillna(1).astype(int) == 1]

    return df.sort_values("id", ascending=False)


def get_entretien(entretien_id: int) -> dict[str, Any] | None:
    df = load_entretiens()

    if df.empty:
        return None

    row = df[df["id"] == int(entretien_id)]

    if row.empty:
        return None

    return row.iloc[0].to_dict()


def add_entretien(data: dict[str, Any]) -> None:
    init_db()
    table = _current_table()
    cols = table_columns(table)

    payload = {
        "batiment_id": int(data.get("batiment_id")) if data.get("batiment_id") else None,
        "type_entretien": data.get("type_entretien"),
        "type_id": data.get("type_id"),
        "date_entretien": data.get("date_entretien"),
        "date_prochain": data.get("date_prochain"),
        "fournisseur": data.get("fournisseur"),
        "montant": float(data.get("montant") or 0),
        "statut": data.get("statut"),
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


def update_entretien(entretien_id: int, data: dict[str, Any]) -> None:
    init_db()
    table = _current_table()
    cols = table_columns(table)

    payload = {
        "batiment_id": int(data.get("batiment_id")) if data.get("batiment_id") else None,
        "type_entretien": data.get("type_entretien"),
        "type_id": data.get("type_id"),
        "date_entretien": data.get("date_entretien"),
        "date_prochain": data.get("date_prochain"),
        "fournisseur": data.get("fournisseur"),
        "montant": float(data.get("montant") or 0),
        "statut": data.get("statut"),
        "commentaire": data.get("commentaire"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    payload = {k: v for k, v in payload.items() if k in cols}

    conn = connect()
    try:
        set_clause = ", ".join([f'"{k}"=?' for k in payload.keys()])
        conn.execute(
            f'UPDATE "{table}" SET {set_clause} WHERE id=?',
            tuple(payload.values()) + (int(entretien_id),),
        )
        conn.commit()
    finally:
        conn.close()


def delete_entretien(entretien_id: int, hard_delete: bool = False) -> None:
    init_db()
    table = _current_table()
    cols = table_columns(table)

    conn = connect()
    try:
        if hard_delete:
            conn.execute(f'DELETE FROM "{table}" WHERE id=?', (int(entretien_id),))
        elif "actif" in cols:
            conn.execute(f'UPDATE "{table}" SET actif=0 WHERE id=?', (int(entretien_id),))
        else:
            conn.execute(f'DELETE FROM "{table}" WHERE id=?', (int(entretien_id),))

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


def _entretien_options(df: pd.DataFrame) -> dict[str, int]:
    options = {}

    for _, row in df.iterrows():
        label = f"#{row['id']} — {row.get('batiment_nom') or 'Non lié'} — {row.get('type_entretien') or ''} — {_format_date(row.get('date_prochain'))}"
        options[label] = int(row["id"])

    return options


def _type_options() -> dict[str, tuple[int | None, str, int]]:
    df = load_entretien_types()
    options: dict[str, tuple[int | None, str, int]] = {}

    if df.empty:
        defaults = [
            ("Chauffage / chaudière", 12),
            ("Électricité", 12),
            ("Plomberie", 12),
            ("Toiture / étanchéité", 24),
            ("Sécurité incendie", 12),
            ("Contrôle général bâtiment", 12),
        ]
        for label, months in defaults:
            options[label] = (None, label, months)
        return options

    for _, row in df.iterrows():
        label = str(row["nom"])
        options[label] = (int(row["id"]), label, int(row["periodicite_mois"]))

    return options


def _add_months(base_date: date, months: int) -> date:
    month = base_date.month - 1 + months
    year = base_date.year + month // 12
    month = month % 12 + 1

    days = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    day = min(base_date.day, days[month - 1])

    return date(year, month, day)


def render_liste() -> None:
    st.markdown("### 📋 Liste des entretiens bâtiments")

    df = load_entretiens()

    if df.empty:
        st.info("Aucun entretien enregistré pour le moment.")
        return

    c1, c2, c3 = st.columns(3)

    with c1:
        search = st.text_input("🔍 Recherche", key="patrimoine_entretiens_search")

    with c2:
        only_linked = st.checkbox("Afficher seulement les entretiens liés", value=False)

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
    if "date_entretien" in display.columns:
        display["date_entretien"] = display["date_entretien"].apply(_format_date)
    if "date_prochain" in display.columns:
        display["date_prochain"] = display["date_prochain"].apply(_format_date)

    cols = [
        "id",
        "batiment_nom",
        "type_entretien",
        "date_entretien",
        "date_prochain",
        "fournisseur",
        "montant",
        "statut",
        "commentaire",
    ]

    if show_columns:
        cols = list(display.columns)

    cols = [c for c in cols if c in display.columns]

    st.caption(f"{len(display)} entretien(s) affiché(s) sur {len(df)}")
    st.dataframe(display[cols], width="stretch", hide_index=True)

    st.markdown("### 🔎 Détail entretien")

    opts = _entretien_options(filtered)

    if not opts:
        st.info("Aucun entretien à détailler.")
        return

    selected = st.selectbox("Sélectionner un entretien", list(opts.keys()), key="patrimoine_entretien_detail_select")
    entretien = get_entretien(opts[selected])

    if not entretien:
        st.warning("Entretien introuvable.")
        return

    c1, c2, c3 = st.columns(3)

    with c1:
        st.write(f"**Bâtiment :** {entretien.get('batiment_nom', 'Non lié')}")
        st.write(f"**Type :** {entretien.get('type_entretien', '')}")

    with c2:
        st.write(f"**Date entretien :** {_format_date(entretien.get('date_entretien', ''))}")
        st.write(f"**Prochain entretien :** {_format_date(entretien.get('date_prochain', ''))}")

    with c3:
        st.write(f"**Fournisseur :** {entretien.get('fournisseur', '')}")
        st.write(f"**Montant :** {entretien.get('montant', 0)} €")
        st.write(f"**Statut :** {entretien.get('statut', '')}")

    commentaire = _clean_text(entretien.get("commentaire"))
    if commentaire:
        st.info(commentaire)

    with st.expander("🔍 Données brutes de l'entretien", expanded=False):
        st.json({k: str(v) for k, v in entretien.items()})


def render_ajouter() -> None:
    st.markdown("### ➕ Ajouter un entretien bâtiment")

    batiments = _batiment_options()

    if not batiments:
        st.warning("Tu dois d'abord avoir au moins un bâtiment.")
        return

    types = _type_options()

    with st.form("patrimoine_add_entretien"):
        selected_bat = st.selectbox("Bâtiment", list(batiments.keys()))
        selected_type = st.selectbox("Type d'entretien", list(types.keys()))

        type_id, type_label, periodicite = types[selected_type]

        c1, c2 = st.columns(2)

        with c1:
            type_entretien = st.text_input("Libellé entretien", value=type_label)
            date_entretien = st.date_input("Date entretien / intervention", value=date.today())
            auto_next = st.checkbox(f"Calculer prochain entretien +{periodicite} mois", value=True)

        with c2:
            default_next = _add_months(date_entretien, periodicite)
            date_prochain = st.date_input("Date prochain entretien", value=default_next if auto_next else None)
            fournisseur = st.text_input("Fournisseur / prestataire")
            montant = st.number_input("Montant €", min_value=0.0, step=10.0)

        statut = st.selectbox("Statut", ["Planifié", "Réalisé", "À surveiller", "En retard", "Annulé"])
        commentaire = st.text_area("Commentaire")
        submitted = st.form_submit_button("💾 Enregistrer l'entretien", width="stretch")

    if submitted:
        add_entretien(
            {
                "batiment_id": batiments[selected_bat],
                "type_id": type_id,
                "type_entretien": type_entretien,
                "date_entretien": date_entretien.isoformat() if date_entretien else "",
                "date_prochain": date_prochain.isoformat() if date_prochain else "",
                "fournisseur": fournisseur,
                "montant": montant,
                "statut": statut,
                "commentaire": commentaire,
            }
        )
        st.success("Entretien ajouté.")
        st.rerun()


def render_modifier() -> None:
    st.markdown("### ✏️ Modifier / supprimer un entretien")

    df = load_entretiens()
    batiments = _batiment_options()

    if df.empty:
        st.info("Aucun entretien disponible.")
        return

    if not batiments:
        st.warning("Aucun bâtiment disponible.")
        return

    options = _entretien_options(df)
    selected = st.selectbox("Entretien", list(options.keys()))
    entretien_id = options[selected]

    row = df[df["id"] == entretien_id].iloc[0].to_dict()

    bat_labels = list(batiments.keys())
    bat_values = list(batiments.values())

    try:
        default_bat_index = bat_values.index(int(float(row.get("batiment_id"))))
    except Exception:
        default_bat_index = 0

    with st.form(f"patrimoine_edit_entretien_{entretien_id}"):
        selected_bat = st.selectbox("Bâtiment", bat_labels, index=default_bat_index)

        c1, c2 = st.columns(2)

        with c1:
            type_entretien = st.text_input("Type entretien", value=str(row.get("type_entretien") or ""))
            date_entretien = st.text_input("Date entretien", value=str(row.get("date_entretien") or ""))
            date_prochain = st.text_input("Date prochain entretien", value=str(row.get("date_prochain") or ""))

        with c2:
            fournisseur = st.text_input("Fournisseur / prestataire", value=str(row.get("fournisseur") or ""))
            montant = st.number_input("Montant €", value=float(row.get("montant") or 0), step=10.0)
            current_statut = str(row.get("statut") or "Planifié")
            statuts = ["Planifié", "Réalisé", "À surveiller", "En retard", "Annulé"]
            index_statut = statuts.index(current_statut) if current_statut in statuts else 0
            statut = st.selectbox("Statut", statuts, index=index_statut)

        commentaire = st.text_area("Commentaire", value=str(row.get("commentaire") or ""))
        submitted = st.form_submit_button("💾 Enregistrer les modifications", width="stretch")

    if submitted:
        update_entretien(
            entretien_id,
            {
                "batiment_id": batiments[selected_bat],
                "type_entretien": type_entretien,
                "date_entretien": date_entretien,
                "date_prochain": date_prochain,
                "fournisseur": fournisseur,
                "montant": montant,
                "statut": statut,
                "commentaire": commentaire,
            },
        )
        st.success("Entretien modifié.")
        st.rerun()

    st.divider()
    confirm = st.checkbox("Confirmer la suppression", key=f"delete_entretien_{entretien_id}")

    if st.button("🗑️ Supprimer l'entretien", disabled=not confirm, width="stretch"):
        delete_entretien(entretien_id)
        st.success("Entretien supprimé.")
        st.rerun()


def render_alertes() -> None:
    st.markdown("### 🚨 Alertes entretiens")

    df = load_entretiens()

    if df.empty:
        st.info("Aucun entretien enregistré.")
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
    c1.metric("Entretiens", len(df))
    c2.metric("En retard", len(retard))
    c3.metric("À venir 30j", len(avenir))

    if not retard.empty:
        st.error("Entretiens en retard")
        st.dataframe(retard, width="stretch", hide_index=True)
    else:
        st.success("Aucun entretien en retard.")

    if not avenir.empty:
        st.warning("Entretiens à venir")
        st.dataframe(avenir, width="stretch", hide_index=True)


def render_types() -> None:
    st.markdown("### 🧰 Types d'entretiens")

    df = load_entretien_types()

    if df.empty:
        st.info("Aucun type d'entretien.")
    else:
        st.dataframe(df, width="stretch", hide_index=True)

    st.markdown("### ➕ Ajouter un type")

    with st.form("patrimoine_add_type_entretien"):
        nom = st.text_input("Nom du type")
        periodicite = st.number_input("Périodicité en mois", min_value=1, max_value=120, value=12, step=1)
        submitted = st.form_submit_button("Ajouter le type", width="stretch")

    if submitted:
        if not nom.strip():
            st.error("Le nom est obligatoire.")
            return

        table = _type_table() or "entretien_types"

        conn = connect()
        try:
            cols = table_columns(table)

            if "nom" in cols and "periodicite_mois" in cols:
                conn.execute(
                    f'INSERT INTO "{table}" (nom, periodicite_mois, actif) VALUES (?, ?, 1)',
                    (nom.strip(), int(periodicite)),
                )
            elif "libelle" in cols:
                conn.execute(
                    f'INSERT INTO "{table}" (libelle) VALUES (?)',
                    (nom.strip(),),
                )
            else:
                st.error("Structure de table types non compatible.")
                return

            conn.commit()
            st.success("Type ajouté.")
            st.rerun()
        finally:
            conn.close()


def render_diagnostic() -> None:
    st.markdown("### 🔍 Diagnostic entretiens")

    table = _current_table()
    type_table = _type_table()

    st.write(f"**Base utilisée :** `{get_db_path()}`")
    st.write(f"**Table entretiens utilisée :** `{table}`")
    st.write(f"**Nombre de lignes entretiens :** `{count_table(table)}`")
    st.write(f"**Colonnes entretiens :** `{table_columns(table)}`")

    if type_table:
        st.write(f"**Table types utilisée :** `{type_table}`")
        st.write(f"**Nombre de types :** `{count_table(type_table)}`")
        st.write(f"**Colonnes types :** `{table_columns(type_table)}`")

    try:
        raw = read_table(table)
        st.markdown("#### Aperçu brut entretiens")
        st.dataframe(raw.head(20), width="stretch", hide_index=True)
    except Exception as exc:
        st.warning(f"Aperçu brut impossible : {exc}")

    df = load_entretiens()
    st.markdown("#### Aperçu normalisé")
    st.dataframe(df.head(20), width="stretch", hide_index=True)

    st.markdown("#### Toutes les tables")
    st.dataframe(diagnostics(), width="stretch", hide_index=True)


def render() -> None:
    init_db()

    st.markdown("### 🛠️ Entretiens patrimoine")
    st.caption(f"Base : {get_db_path()} — table : {_current_table()} — lignes : {count_table(_current_table())}")

    tabs = st.tabs(
        [
            "📋 Liste / Détail",
            "➕ Ajouter",
            "✏️ Modifier / Supprimer",
            "🚨 Alertes",
            "🧰 Types",
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
        render_types()

    with tabs[5]:
        render_diagnostic()


def show() -> None:
    render()
