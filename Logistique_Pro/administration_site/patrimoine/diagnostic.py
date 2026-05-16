# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from .batiments import load_batiments
from .controles import load_controles
from .entretiens import load_entretiens
from .db import (
    connect,
    count_table,
    diagnostics,
    get_db_path,
    get_tables,
    read_table,
    table_columns,
)


PROJECT_DIR = Path("/opt/logistique-pro")
EXPORT_DIR = PROJECT_DIR / "data" / "exports" / "patrimoine"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def _clean(value: Any) -> str:
    if value is None:
        return ""
    value = str(value)
    if value.lower() in ["none", "nan", "nat"]:
        return ""
    return value.strip()


def _is_empty_value(value: Any) -> bool:
    value = _clean(value)
    return value == ""


def _table_empty_columns(table_name: str) -> pd.DataFrame:
    try:
        df = read_table(table_name)
    except Exception:
        return pd.DataFrame()

    rows = []

    if df.empty:
        for col in table_columns(table_name):
            rows.append(
                {
                    "table": table_name,
                    "colonne": col,
                    "lignes": 0,
                    "vides": 0,
                    "remplies": 0,
                    "pourcentage_vide": 100,
                }
            )
        return pd.DataFrame(rows)

    total = len(df)

    for col in df.columns:
        empty_count = int(df[col].apply(_is_empty_value).sum())
        filled = total - empty_count
        percent = round((empty_count / total) * 100, 1) if total else 100

        rows.append(
            {
                "table": table_name,
                "colonne": col,
                "lignes": total,
                "vides": empty_count,
                "remplies": filled,
                "pourcentage_vide": percent,
            }
        )

    return pd.DataFrame(rows)


def _all_empty_columns() -> pd.DataFrame:
    frames = []

    for table in get_tables():
        if table == "sqlite_sequence":
            continue

        try:
            frames.append(_table_empty_columns(table))
        except Exception:
            pass

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


def _duplicate_batiments() -> pd.DataFrame:
    df = load_batiments(include_inactive=True)

    if df.empty or "nom" not in df.columns:
        return pd.DataFrame()

    working = df.copy()
    working["_nom_clean"] = working["nom"].fillna("").astype(str).str.lower().str.strip()

    dup_names = (
        working[working["_nom_clean"] != ""]
        .groupby("_nom_clean")
        .size()
        .reset_index(name="nb")
    )

    dup_names = dup_names[dup_names["nb"] > 1]

    if dup_names.empty:
        return pd.DataFrame()

    result = working[working["_nom_clean"].isin(dup_names["_nom_clean"])].copy()

    cols = ["id", "nom", "type_batiment", "adresse", "ville", "actif"]
    cols = [c for c in cols if c in result.columns]

    return result[cols].sort_values("nom")


def _unlinked_controles() -> pd.DataFrame:
    df = load_controles()

    if df.empty:
        return pd.DataFrame()

    result = df.copy()

    if "batiment_nom" in result.columns:
        result = result[
            result["batiment_nom"].fillna("").astype(str).str.strip().isin(["", "Non lié", "nan", "None"])
        ]
    elif "batiment_id" in result.columns:
        result = result[
            result["batiment_id"].fillna("").astype(str).str.strip().isin(["", "nan", "None"])
        ]
    else:
        return result

    cols = [
        "id",
        "batiment_id",
        "batiment_nom",
        "type_controle",
        "detail_controle",
        "date_prochain",
        "organisme",
        "statut",
    ]
    cols = [c for c in cols if c in result.columns]

    return result[cols]


def _unlinked_entretiens() -> pd.DataFrame:
    df = load_entretiens()

    if df.empty:
        return pd.DataFrame()

    result = df.copy()

    if "batiment_nom" in result.columns:
        result = result[
            result["batiment_nom"].fillna("").astype(str).str.strip().isin(["", "Non lié", "nan", "None"])
        ]
    elif "batiment_id" in result.columns:
        result = result[
            result["batiment_id"].fillna("").astype(str).str.strip().isin(["", "nan", "None"])
        ]
    else:
        return result

    cols = [
        "id",
        "batiment_id",
        "batiment_nom",
        "type_entretien",
        "date_prochain",
        "fournisseur",
        "statut",
    ]
    cols = [c for c in cols if c in result.columns]

    return result[cols]


def _invalid_photo_paths() -> pd.DataFrame:
    df = load_batiments(include_inactive=True)

    if df.empty:
        return pd.DataFrame()

    rows = []

    for _, row in df.iterrows():
        photo = ""

        for key in ["photo_path", "image_path", "photo", "image"]:
            if key in row.index:
                value = _clean(row.get(key))
                if value:
                    photo = value
                    break

        if not photo:
            continue

        path = Path(photo)

        if not path.is_absolute():
            path = PROJECT_DIR / photo

        if not path.exists():
            rows.append(
                {
                    "id": row.get("id", ""),
                    "nom": row.get("nom", ""),
                    "photo": photo,
                    "chemin_testé": str(path),
                    "problème": "Image introuvable",
                }
            )

    return pd.DataFrame(rows)


def _summary_rows() -> pd.DataFrame:
    batiments = load_batiments(include_inactive=True)
    controles = load_controles()
    entretiens = load_entretiens()

    rows = [
        {"élément": "Base utilisée", "valeur": str(get_db_path())},
        {"élément": "Tables détectées", "valeur": len(get_tables())},
        {"élément": "Bâtiments chargés", "valeur": len(batiments)},
        {"élément": "Contrôles chargés", "valeur": len(controles)},
        {"élément": "Entretiens chargés", "valeur": len(entretiens)},
        {"élément": "Contrôles non liés", "valeur": len(_unlinked_controles())},
        {"élément": "Entretiens non liés", "valeur": len(_unlinked_entretiens())},
        {"élément": "Doublons bâtiments possibles", "valeur": len(_duplicate_batiments())},
        {"élément": "Images bâtiment invalides", "valeur": len(_invalid_photo_paths())},
    ]

    return pd.DataFrame(rows)


def _export_diagnostic_zip() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = EXPORT_DIR / f"diagnostic_patrimoine_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    exports = {
        "resume.csv": _summary_rows(),
        "tables.csv": pd.DataFrame(diagnostics()),
        "colonnes_vides.csv": _all_empty_columns(),
        "doublons_batiments.csv": _duplicate_batiments(),
        "controles_non_lies.csv": _unlinked_controles(),
        "entretiens_non_lies.csv": _unlinked_entretiens(),
        "images_invalides.csv": _invalid_photo_paths(),
    }

    for filename, df in exports.items():
        if df is None or df.empty:
            df = pd.DataFrame()
        df.to_csv(out_dir / filename, index=False, encoding="utf-8-sig")

    zip_path = EXPORT_DIR / f"diagnostic_patrimoine_{timestamp}.zip"

    import zipfile

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for file in out_dir.glob("*.csv"):
            z.write(file, arcname=file.name)

    return zip_path


def _download_df(df: pd.DataFrame, filename: str, label: str) -> None:
    if df.empty:
        return

    st.download_button(
        label,
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name=filename,
        mime="text/csv",
        width="stretch",
    )


def render_resume() -> None:
    st.markdown("### 📊 Résumé diagnostic")

    summary = _summary_rows()
    st.dataframe(summary, width="stretch", hide_index=True)

    values = {row["élément"]: row["valeur"] for _, row in summary.iterrows()}

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Bâtiments", values.get("Bâtiments chargés", 0))
    c2.metric("Contrôles", values.get("Contrôles chargés", 0))
    c3.metric("Entretiens", values.get("Entretiens chargés", 0))
    c4.metric("Images invalides", values.get("Images bâtiment invalides", 0))

    if st.button("📦 Générer ZIP diagnostic complet", width="stretch"):
        try:
            path = _export_diagnostic_zip()
            st.success(f"Diagnostic généré : {path}")

            with open(path, "rb") as f:
                st.download_button(
                    "📥 Télécharger le ZIP diagnostic",
                    data=f.read(),
                    file_name=path.name,
                    mime="application/zip",
                    width="stretch",
                )
        except Exception as exc:
            st.error(f"Erreur export diagnostic : {exc}")


def render_tables() -> None:
    st.markdown("### 🗄️ Tables et colonnes")

    rows = diagnostics()
    df = pd.DataFrame(rows)

    if df.empty:
        st.info("Aucune table détectée.")
        return

    st.dataframe(df, width="stretch", hide_index=True)
    _download_df(df, "diagnostic_tables_patrimoine.csv", "📥 Export CSV tables")


def render_colonnes_vides() -> None:
    st.markdown("### 🧹 Colonnes vides / inutilisées")

    df = _all_empty_columns()

    if df.empty:
        st.info("Aucune donnée de colonne.")
        return

    only_empty = st.checkbox("Afficher uniquement les colonnes 100% vides", value=True)

    display = df.copy()

    if only_empty:
        display = display[display["pourcentage_vide"] >= 100]

    st.dataframe(display, width="stretch", hide_index=True)
    _download_df(display, "colonnes_vides_patrimoine.csv", "📥 Export CSV colonnes")


def render_liaisons() -> None:
    st.markdown("### 🔗 Liaisons bâtiments / suivis")

    controles = _unlinked_controles()
    entretiens = _unlinked_entretiens()

    tab1, tab2 = st.tabs(
        [
            f"Contrôles non liés ({len(controles)})",
            f"Entretiens non liés ({len(entretiens)})",
        ]
    )

    with tab1:
        if controles.empty:
            st.success("Tous les contrôles semblent liés à un bâtiment.")
        else:
            st.dataframe(controles, width="stretch", hide_index=True)
            _download_df(controles, "controles_non_lies.csv", "📥 Export CSV contrôles non liés")

    with tab2:
        if entretiens.empty:
            st.success("Tous les entretiens semblent liés à un bâtiment.")
        else:
            st.dataframe(entretiens, width="stretch", hide_index=True)
            _download_df(entretiens, "entretiens_non_lies.csv", "📥 Export CSV entretiens non liés")


def render_doublons() -> None:
    st.markdown("### 🧬 Doublons potentiels bâtiments")

    df = _duplicate_batiments()

    if df.empty:
        st.success("Aucun doublon évident détecté sur le nom des bâtiments.")
        return

    st.warning(f"{len(df)} ligne(s) concernée(s) par des doublons potentiels.")
    st.dataframe(df, width="stretch", hide_index=True)
    _download_df(df, "doublons_batiments.csv", "📥 Export CSV doublons")


def render_images() -> None:
    st.markdown("### 🖼️ Diagnostic images bâtiments")

    df = _invalid_photo_paths()

    if df.empty:
        st.success("Aucune image invalide détectée.")
        return

    st.warning(f"{len(df)} image(s) introuvable(s).")
    st.dataframe(df, width="stretch", hide_index=True)
    _download_df(df, "images_invalides_batiments.csv", "📥 Export CSV images invalides")


def render_sql() -> None:
    st.markdown("### 🧪 Requête SQL lecture seule")

    st.warning("Utilise uniquement des requêtes SELECT. Aucun DELETE/UPDATE/INSERT n'est autorisé ici.")

    query = st.text_area(
        "Requête SQL",
        value='SELECT name FROM sqlite_master WHERE type="table" ORDER BY name;',
        height=120,
    )

    forbidden = ["delete", "update", "insert", "drop", "alter", "create", "replace", "pragma"]

    if st.button("Exécuter la requête", width="stretch"):
        lowered = query.lower()

        if any(word in lowered for word in forbidden):
            st.error("Requête refusée : seules les requêtes SELECT simples sont autorisées.")
            return

        if not lowered.strip().startswith("select"):
            st.error("La requête doit commencer par SELECT.")
            return

        try:
            conn = connect()
            df = pd.read_sql_query(query, conn)
            conn.close()

            st.dataframe(df, width="stretch", hide_index=True)
            _download_df(df, "resultat_requete_sql.csv", "📥 Export CSV résultat")
        except Exception as exc:
            st.error(f"Erreur SQL : {exc}")


def render() -> None:
    st.markdown("### 🔍 Diagnostic avancé patrimoine")
    st.caption(f"Base : {get_db_path()}")

    tabs = st.tabs(
        [
            "📊 Résumé",
            "🗄️ Tables",
            "🧹 Colonnes vides",
            "🔗 Liaisons",
            "🧬 Doublons",
            "🖼️ Images",
            "🧪 SQL lecture",
        ]
    )

    with tabs[0]:
        render_resume()

    with tabs[1]:
        render_tables()

    with tabs[2]:
        render_colonnes_vides()

    with tabs[3]:
        render_liaisons()

    with tabs[4]:
        render_doublons()

    with tabs[5]:
        render_images()

    with tabs[6]:
        render_sql()


def show() -> None:
    render()
