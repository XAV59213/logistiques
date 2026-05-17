# -*- coding: utf-8 -*-
from __future__ import annotations

import mimetypes
from pathlib import Path
from datetime import date, datetime
from typing import Any

import pandas as pd
import streamlit as st

from .batiments import load_batiments
from .db import connect, get_db_path, table_columns


PROJECT_DIR = Path("/opt/logistique-pro")
DATA_DIR = PROJECT_DIR / "data"
DOCUMENTS_DIR = DATA_DIR / "patrimoine_documents"
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

TABLE_NAME = "patrimoine_documents"


def _clean(value: Any) -> str:
    if value is None:
        return ""
    value = str(value)
    if value.lower() in ["none", "nan", "nat"]:
        return ""
    return value.strip()


def _safe_filename(name: str) -> str:
    name = _clean(name) or "document"

    for ch in ['/', '\\', ':', '*', '?', '"', '<', '>', '|', "'", " "]:
        name = name.replace(ch, "_")

    return name[:140]


def _format_date(value: Any) -> str:
    value = _clean(value)

    if not value:
        return ""

    try:
        parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
        if pd.isna(parsed):
            return value
        return parsed.strftime("%d/%m/%Y")
    except Exception:
        return value


def init_db() -> None:
    conn = connect()
    try:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batiment_id INTEGER,
                type_document TEXT DEFAULT '',
                titre TEXT DEFAULT '',
                date_document TEXT DEFAULT '',
                fichier_nom TEXT DEFAULT '',
                fichier_path TEXT DEFAULT '',
                mime_type TEXT DEFAULT '',
                taille_octets INTEGER DEFAULT 0,
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


def _columns() -> list[str]:
    init_db()
    return table_columns(TABLE_NAME)


def _save_uploaded_file(uploaded_file, batiment_id: int, type_document: str) -> dict[str, Any]:
    if uploaded_file is None:
        raise ValueError("Aucun fichier fourni.")

    original_name = _safe_filename(uploaded_file.name)
    suffix = Path(original_name).suffix.lower()

    if not suffix:
        suffix = ".bin"

    folder = DOCUMENTS_DIR / f"batiment_{batiment_id}"
    folder.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    type_safe = _safe_filename(type_document)
    filename = f"{timestamp}_{type_safe}_{original_name}"
    target = folder / filename

    with open(target, "wb") as f:
        f.write(uploaded_file.getbuffer())

    mime_type = uploaded_file.type or mimetypes.guess_type(str(target))[0] or "application/octet-stream"

    return {
        "fichier_nom": uploaded_file.name,
        "fichier_path": str(target),
        "mime_type": mime_type,
        "taille_octets": int(target.stat().st_size),
    }


def add_document(data: dict[str, Any]) -> None:
    init_db()
    cols = _columns()

    payload = {
        "batiment_id": int(data.get("batiment_id")) if data.get("batiment_id") else None,
        "type_document": data.get("type_document"),
        "titre": data.get("titre"),
        "date_document": data.get("date_document"),
        "fichier_nom": data.get("fichier_nom"),
        "fichier_path": data.get("fichier_path"),
        "mime_type": data.get("mime_type"),
        "taille_octets": int(data.get("taille_octets") or 0),
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
            f'INSERT INTO "{TABLE_NAME}" ({columns}) VALUES ({placeholders})',
            tuple(payload.values()),
        )
        conn.commit()
    finally:
        conn.close()


def update_document(document_id: int, data: dict[str, Any]) -> None:
    init_db()
    cols = _columns()

    payload = {
        "batiment_id": int(data.get("batiment_id")) if data.get("batiment_id") else None,
        "type_document": data.get("type_document"),
        "titre": data.get("titre"),
        "date_document": data.get("date_document"),
        "commentaire": data.get("commentaire"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    if data.get("fichier_path"):
        payload.update(
            {
                "fichier_nom": data.get("fichier_nom"),
                "fichier_path": data.get("fichier_path"),
                "mime_type": data.get("mime_type"),
                "taille_octets": int(data.get("taille_octets") or 0),
            }
        )

    payload = {k: v for k, v in payload.items() if k in cols}

    conn = connect()
    try:
        set_clause = ", ".join([f'"{k}"=?' for k in payload.keys()])
        conn.execute(
            f'UPDATE "{TABLE_NAME}" SET {set_clause} WHERE id=?',
            tuple(payload.values()) + (int(document_id),),
        )
        conn.commit()
    finally:
        conn.close()


def delete_document(document_id: int, hard_delete: bool = False, delete_file: bool = False) -> None:
    init_db()
    doc = get_document(document_id)

    conn = connect()
    try:
        if hard_delete:
            conn.execute(f'DELETE FROM "{TABLE_NAME}" WHERE id=?', (int(document_id),))
        else:
            conn.execute(f'UPDATE "{TABLE_NAME}" SET actif=0 WHERE id=?', (int(document_id),))
        conn.commit()
    finally:
        conn.close()

    if delete_file and doc:
        path = Path(_clean(doc.get("fichier_path")))
        if path.exists():
            try:
                path.unlink()
            except Exception:
                pass


def load_documents(include_inactive: bool = False) -> pd.DataFrame:
    init_db()

    conn = connect()
    try:
        df = pd.read_sql_query(f'SELECT * FROM "{TABLE_NAME}" ORDER BY id DESC', conn)
    finally:
        conn.close()

    if df.empty:
        return df

    if not include_inactive and "actif" in df.columns:
        df = df[pd.to_numeric(df["actif"], errors="coerce").fillna(1).astype(int) == 1]

    batiments = load_batiments(include_inactive=True)

    if not batiments.empty and "batiment_id" in df.columns:
        bdf = batiments.copy()

        if "id" not in bdf.columns:
            bdf["id"] = range(1, len(bdf) + 1)

        if "nom" not in bdf.columns:
            bdf["nom"] = ""

        if "ville" not in bdf.columns:
            bdf["ville"] = ""

        bdf = bdf[["id", "nom", "ville"]].rename(
            columns={"id": "batiment_id", "nom": "batiment_nom"}
        )

        df["batiment_id"] = pd.to_numeric(df["batiment_id"], errors="coerce")
        df = df.merge(bdf, on="batiment_id", how="left")

    if "batiment_nom" not in df.columns:
        df["batiment_nom"] = ""

    df["batiment_nom"] = df["batiment_nom"].fillna("Non lié").replace("", "Non lié")

    return df


def get_document(document_id: int) -> dict[str, Any] | None:
    df = load_documents(include_inactive=True)

    if df.empty:
        return None

    row = df[df["id"] == int(document_id)]

    if row.empty:
        return None

    return row.iloc[0].to_dict()


def _batiment_options() -> dict[str, int]:
    df = load_batiments(include_inactive=False)
    options = {}

    for _, row in df.iterrows():
        label = f"#{row['id']} — {row.get('nom') or 'Sans nom'} — {row.get('ville') or ''}"
        options[label] = int(row["id"])

    return options


def _document_options(df: pd.DataFrame) -> dict[str, int]:
    options = {}

    for _, row in df.iterrows():
        label = f"#{row['id']} — {row.get('batiment_nom') or 'Non lié'} — {row.get('type_document') or ''} — {row.get('titre') or row.get('fichier_nom') or ''}"
        options[label] = int(row["id"])

    return options



def _download_key(doc: dict[str, Any]) -> str:
    doc_id = _clean(doc.get("id")) or "0"
    file_name = _safe_filename(_clean(doc.get("fichier_nom")) or "document")
    return f"patrimoine_doc_download_{doc_id}_{file_name}"



def _download_document(doc: dict[str, Any], label: str = "📥 Télécharger le document") -> None:
    path = Path(_clean(doc.get("fichier_path")))

    if not path.exists():
        st.warning(f"Fichier introuvable : {path}")
        return

    try:
        with open(path, "rb") as f:
            st.download_button(
                label,
                data=f.read(),
                file_name=_clean(doc.get("fichier_nom")) or path.name,
                mime=_clean(doc.get("mime_type")) or "application/octet-stream",
                width="stretch",
                key=_download_key(doc),
            )
    except Exception as exc:
        st.error(f"Impossible de préparer le téléchargement : {exc}")



def render_liste() -> None:
    st.markdown("### 📋 Documents bâtiments")

    df = load_documents(include_inactive=True)

    if df.empty:
        st.info("Aucun document enregistré pour le moment.")
        return

    c1, c2, c3 = st.columns(3)

    with c1:
        search = st.text_input("🔍 Recherche", key="patrimoine_documents_search")

    with c2:
        types = sorted([x for x in df["type_document"].fillna("").unique().tolist() if str(x).strip()])
        type_filter = st.selectbox("Type document", ["Tous"] + types)

    with c3:
        actif_filter = st.selectbox("Statut", ["Actifs", "Tous", "Inactifs"])

    filtered = df.copy()

    if type_filter != "Tous":
        filtered = filtered[filtered["type_document"] == type_filter]

    if actif_filter == "Actifs":
        filtered = filtered[pd.to_numeric(filtered["actif"], errors="coerce").fillna(1).astype(int) == 1]
    elif actif_filter == "Inactifs":
        filtered = filtered[pd.to_numeric(filtered["actif"], errors="coerce").fillna(1).astype(int) == 0]

    if search:
        q = search.lower()
        mask = pd.Series(False, index=filtered.index)

        for col in filtered.columns:
            mask = mask | filtered[col].astype(str).str.lower().str.contains(q, na=False)

        filtered = filtered[mask]

    display = filtered.copy()

    if "date_document" in display.columns:
        display["date_document"] = display["date_document"].apply(_format_date)

    if "taille_octets" in display.columns:
        display["taille Ko"] = display["taille_octets"].apply(lambda x: round(float(x or 0) / 1024, 1))

    cols = [
        "id",
        "batiment_nom",
        "type_document",
        "titre",
        "date_document",
        "fichier_nom",
        "taille Ko",
        "commentaire",
        "actif",
    ]
    cols = [c for c in cols if c in display.columns]

    st.caption(f"{len(display)} document(s) affiché(s) sur {len(df)}")
    st.dataframe(display[cols], width="stretch", hide_index=True)

    st.markdown("### 🔎 Détail document")

    opts = _document_options(filtered)

    if not opts:
        st.info("Aucun document à détailler.")
        return

    selected = st.selectbox("Document", list(opts.keys()), key="patrimoine_document_detail_select")
    doc = get_document(opts[selected])

    if not doc:
        st.warning("Document introuvable.")
        return

    c1, c2, c3 = st.columns(3)

    with c1:
        st.write(f"**Bâtiment :** {doc.get('batiment_nom', 'Non lié')}")
        st.write(f"**Type :** {doc.get('type_document', '')}")
        st.write(f"**Titre :** {doc.get('titre', '')}")

    with c2:
        st.write(f"**Date :** {_format_date(doc.get('date_document'))}")
        st.write(f"**Fichier :** {doc.get('fichier_nom', '')}")
        st.write(f"**MIME :** {doc.get('mime_type', '')}")

    with c3:
        taille = round(float(doc.get("taille_octets") or 0) / 1024, 1)
        st.write(f"**Taille :** {taille} Ko")
        st.write(f"**Actif :** {'Oui' if int(doc.get('actif') or 0) == 1 else 'Non'}")

    commentaire = _clean(doc.get("commentaire"))
    if commentaire:
        st.info(commentaire)

    _download_document(doc)


def render_ajouter() -> None:
    st.markdown("### ➕ Ajouter un document bâtiment")

    batiments = _batiment_options()

    if not batiments:
        st.warning("Tu dois d'abord avoir au moins un bâtiment.")
        return

    with st.form("patrimoine_add_document"):
        selected_bat = st.selectbox("Bâtiment", list(batiments.keys()))

        c1, c2 = st.columns(2)

        with c1:
            type_document = st.selectbox(
                "Type document",
                [
                    "Rapport de contrôle",
                    "Diagnostic",
                    "Attestation",
                    "Facture",
                    "Plan",
                    "Notice",
                    "Photo",
                    "Contrat",
                    "Autre",
                ],
            )
            titre = st.text_input("Titre / description courte")
            date_document = st.date_input("Date du document", value=date.today())

        with c2:
            uploaded = st.file_uploader(
                "Fichier",
                type=[
                    "pdf",
                    "jpg",
                    "jpeg",
                    "png",
                    "webp",
                    "doc",
                    "docx",
                    "xls",
                    "xlsx",
                    "csv",
                    "txt",
                ],
            )

        commentaire = st.text_area("Commentaire")
        submitted = st.form_submit_button("💾 Enregistrer le document", width="stretch")

    if submitted:
        if uploaded is None:
            st.error("Tu dois sélectionner un fichier.")
            return

        batiment_id = batiments[selected_bat]

        try:
            file_info = _save_uploaded_file(uploaded, batiment_id, type_document)

            add_document(
                {
                    "batiment_id": batiment_id,
                    "type_document": type_document,
                    "titre": titre or uploaded.name,
                    "date_document": date_document.isoformat() if date_document else "",
                    "commentaire": commentaire,
                    **file_info,
                }
            )

            st.success("Document ajouté.")
            st.rerun()
        except Exception as exc:
            st.error(f"Erreur ajout document : {exc}")


def render_modifier() -> None:
    st.markdown("### ✏️ Modifier / supprimer un document")

    df = load_documents(include_inactive=True)
    batiments = _batiment_options()

    if df.empty:
        st.info("Aucun document disponible.")
        return

    if not batiments:
        st.warning("Aucun bâtiment disponible.")
        return

    opts = _document_options(df)
    selected = st.selectbox("Document", list(opts.keys()))
    document_id = opts[selected]
    row = df[df["id"] == document_id].iloc[0].to_dict()

    bat_labels = list(batiments.keys())
    bat_values = list(batiments.values())

    try:
        default_bat_index = bat_values.index(int(float(row.get("batiment_id"))))
    except Exception:
        default_bat_index = 0

    with st.form(f"patrimoine_edit_document_{document_id}"):
        selected_bat = st.selectbox("Bâtiment", bat_labels, index=default_bat_index)

        c1, c2 = st.columns(2)

        with c1:
            type_document = st.text_input("Type document", value=str(row.get("type_document") or ""))
            titre = st.text_input("Titre", value=str(row.get("titre") or ""))
            date_document = st.text_input("Date document", value=str(row.get("date_document") or ""))

        with c2:
            uploaded = st.file_uploader(
                "Remplacer le fichier",
                type=[
                    "pdf",
                    "jpg",
                    "jpeg",
                    "png",
                    "webp",
                    "doc",
                    "docx",
                    "xls",
                    "xlsx",
                    "csv",
                    "txt",
                ],
                key=f"replace_document_{document_id}",
            )
            st.caption(f"Fichier actuel : {row.get('fichier_nom') or ''}")

        commentaire = st.text_area("Commentaire", value=str(row.get("commentaire") or ""))

        submitted = st.form_submit_button("💾 Enregistrer les modifications", width="stretch")

    if submitted:
        try:
            file_info = {}

            if uploaded is not None:
                file_info = _save_uploaded_file(uploaded, batiments[selected_bat], type_document)

            update_document(
                document_id,
                {
                    "batiment_id": batiments[selected_bat],
                    "type_document": type_document,
                    "titre": titre,
                    "date_document": date_document,
                    "commentaire": commentaire,
                    **file_info,
                },
            )

            st.success("Document modifié.")
            st.rerun()
        except Exception as exc:
            st.error(f"Erreur modification document : {exc}")

    st.divider()
    st.markdown("### 🗑️ Suppression")

    c1, c2 = st.columns(2)

    with c1:
        confirm_soft = st.checkbox("Confirmer désactivation", key=f"doc_soft_{document_id}")

        if st.button("Désactiver le document", disabled=not confirm_soft, width="stretch", key=f"btn_doc_soft_delete_{document_id}"):
            delete_document(document_id, hard_delete=False, delete_file=False)
            st.success("Document désactivé.")
            st.rerun()

    with c2:
        confirm_hard = st.checkbox("Confirmer suppression définitive", key=f"doc_hard_{document_id}")
        delete_file = st.checkbox("Supprimer aussi le fichier physique", key=f"doc_file_{document_id}")

        if st.button("Supprimer définitivement", disabled=not confirm_hard, width="stretch", key=f"btn_doc_hard_delete_{document_id}"):
            delete_document(document_id, hard_delete=True, delete_file=delete_file)
            st.success("Document supprimé.")
            st.rerun()


def render_par_batiment() -> None:
    st.markdown("### 🏢 Documents par bâtiment")

    df = load_documents(include_inactive=False)

    if df.empty:
        st.info("Aucun document.")
        return

    bats = sorted(df["batiment_nom"].fillna("Non lié").unique().tolist())

    for bat in bats:
        bat_df = df[df["batiment_nom"] == bat].copy()

        with st.expander(f"{bat} — {len(bat_df)} document(s)", expanded=False):
            display = bat_df.copy()

            if "date_document" in display.columns:
                display["date_document"] = display["date_document"].apply(_format_date)

            cols = ["id", "type_document", "titre", "date_document", "fichier_nom", "commentaire"]
            cols = [c for c in cols if c in display.columns]

            st.dataframe(display[cols], width="stretch", hide_index=True)


def render_diagnostic() -> None:
    st.markdown("### 🔍 Diagnostic documents")

    df = load_documents(include_inactive=True)

    st.write(f"**Base :** `{get_db_path()}`")
    st.write(f"**Table :** `{TABLE_NAME}`")
    st.write(f"**Dossier documents :** `{DOCUMENTS_DIR}`")
    st.write(f"**Documents en base :** `{len(df)}`")

    files = [p for p in DOCUMENTS_DIR.rglob("*") if p.is_file()]
    st.write(f"**Fichiers physiques :** `{len(files)}`")

    invalid = []

    if not df.empty:
        for _, row in df.iterrows():
            path = Path(_clean(row.get("fichier_path")))

            if path and not path.exists():
                invalid.append(
                    {
                        "id": row.get("id"),
                        "titre": row.get("titre"),
                        "fichier_path": row.get("fichier_path"),
                        "problème": "Fichier introuvable",
                    }
                )

    if invalid:
        st.warning(f"{len(invalid)} document(s) ont un fichier introuvable.")
        st.dataframe(invalid, width="stretch", hide_index=True)
    else:
        st.success("Aucun fichier manquant détecté.")


def render() -> None:
    init_db()

    st.markdown("### 📎 Documents bâtiments")
    st.caption(f"Dossier : {DOCUMENTS_DIR}")

    tabs = st.tabs(
        [
            "📋 Liste / Détail",
            "➕ Ajouter",
            "✏️ Modifier / Supprimer",
            "🏢 Par bâtiment",
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
        render_par_batiment()

    with tabs[4]:
        render_diagnostic()


def show() -> None:
    render()
