# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
import mimetypes
import sqlite3
from pathlib import Path

import streamlit as st


APP_DIR = Path("/opt/logistique-pro")
DATA_DIR = APP_DIR / "data"

DOC_DIR_CANDIDATES = [
    DATA_DIR / "patrimoine_documents",
    DATA_DIR / "patrimoine_documents" / "documents",
    DATA_DIR / "patrimoine_documents" / "uploads",
    DATA_DIR / "documents_batiments",
    DATA_DIR / "documents",
    APP_DIR / "uploads",
    APP_DIR / "static" / "uploads",
]

DB_CANDIDATES = [
    DATA_DIR / "patrimoine_bati.db",
    DATA_DIR / "logistique_marly.db",
    DATA_DIR / "logistique.db",
    DATA_DIR / "database.db",
]


def fmt_size_ko(value) -> str:
    try:
        return f"{float(value):.1f} Ko"
    except Exception:
        return ""


def safe_name(value) -> str:
    return str(value or "").strip()


def possible_filenames(filename: str) -> list[str]:
    filename = safe_name(filename)
    if not filename:
        return []

    p = Path(filename)
    names = [filename, p.name]

    # Si la base contient parfois des espaces ou chemins Windows
    names.append(filename.replace("\\", "/").split("/")[-1])
    names.append(filename.replace("/", "\\").split("\\")[-1])

    # Déduplication
    out = []
    for name in names:
        if name and name not in out:
            out.append(name)
    return out


def find_existing_file(filename: str, row: dict | None = None) -> Path | None:
    row = row or {}

    # 1) Colonnes chemin direct possibles
    for col in [
        "fichier_path",
        "chemin",
        "path",
        "filepath",
        "file_path",
        "url_fichier",
        "document_path",
    ]:
        value = safe_name(row.get(col))
        if not value:
            continue

        candidates = [
            Path(value),
            APP_DIR / value,
            DATA_DIR / value,
        ]

        for candidate in candidates:
            try:
                if candidate.exists() and candidate.is_file():
                    return candidate
            except Exception:
                pass

    # 2) Recherche par nom de fichier
    names = possible_filenames(filename)

    for name in names:
        for folder in DOC_DIR_CANDIDATES:
            if not folder.exists():
                continue

            direct = folder / name
            if direct.exists() and direct.is_file():
                return direct

            # Recherche récursive
            try:
                for p in folder.rglob(name):
                    if p.exists() and p.is_file():
                        return p
            except Exception:
                pass

    # 3) Recherche globale limitée dans data
    for name in names:
        try:
            for p in DATA_DIR.rglob(name):
                if p.exists() and p.is_file():
                    return p
        except Exception:
            pass

    return None


def get_tables(conn: sqlite3.Connection) -> list[str]:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [r[0] for r in cur.fetchall()]


def get_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cur = conn.cursor()
    cur.execute(f'PRAGMA table_info("{table}")')
    return [r[1] for r in cur.fetchall()]


def find_documents_table(conn: sqlite3.Connection) -> str | None:
    for table in get_tables(conn):
        cols = set(get_columns(conn, table))

        if {"batiment_nom", "fichier_nom"}.issubset(cols):
            return table

        if {"batiment_id", "fichier_nom"}.issubset(cols):
            return table

        if "document" in table.lower() and (
            "fichier_nom" in cols or "fichier_path" in cols or "chemin" in cols
        ):
            return table

    return None


def find_documents_db() -> tuple[Path | None, str | None]:
    for db in DB_CANDIDATES:
        if not db.exists():
            continue

        try:
            conn = sqlite3.connect(str(db))
            table = find_documents_table(conn)
            conn.close()

            if table:
                return db, table
        except Exception:
            pass

    for db in DATA_DIR.glob("*.db"):
        try:
            conn = sqlite3.connect(str(db))
            table = find_documents_table(conn)
            conn.close()

            if table:
                return db, table
        except Exception:
            pass

    return None, None


def list_documents_for_batiment(batiment_nom: str, batiment_id=None) -> list[dict]:
    db, table = find_documents_db()

    if not db or not table:
        return []

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cols = get_columns(conn, table)

    where = []
    params = []

    if "batiment_nom" in cols and batiment_nom:
        where.append("LOWER(TRIM(batiment_nom)) = LOWER(TRIM(?))")
        params.append(str(batiment_nom))

    if batiment_id not in [None, "", 0] and "batiment_id" in cols:
        where.append("batiment_id = ?")
        params.append(batiment_id)

    active_filter = "actif = 1" if "actif" in cols else "1=1"

    if where:
        sql = f'''
            SELECT *
            FROM "{table}"
            WHERE ({' OR '.join(where)})
              AND {active_filter}
            ORDER BY id DESC
        '''
        cur.execute(sql, params)
    else:
        conn.close()
        return []

    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    return rows


def value(row: dict, *names, default=""):
    for name in names:
        if name in row and row[name] not in [None, ""]:
            return row[name]
    return default


def render_file_preview(file_path: Path):
    suffix = file_path.suffix.lower()

    if suffix in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        st.image(str(file_path), caption=file_path.name, use_container_width=True)
        return

    if suffix == ".pdf":
        try:
            data = file_path.read_bytes()
            b64 = base64.b64encode(data).decode("utf-8")
            st.markdown(
                f'''
                <iframe
                    src="data:application/pdf;base64,{b64}"
                    width="100%"
                    height="500"
                    style="border:1px solid #ddd;border-radius:8px;">
                </iframe>
                ''',
                unsafe_allow_html=True,
            )
        except Exception as exc:
            st.warning(f"Aperçu PDF indisponible : {exc}")
        return

    st.info("Aperçu direct non disponible pour ce type de fichier. Utilise Télécharger.")


def render_documents_view(batiment_nom: str, batiment_id=None):
    docs = list_documents_for_batiment(batiment_nom=batiment_nom, batiment_id=batiment_id)

    st.caption("Documents liés au bâtiment depuis Administration Site > Patrimoine bâti > Documents.")

    if not docs:
        st.info("Aucun document enregistré pour ce bâtiment.")
        return

    st.success(f"{len(docs)} document(s) trouvé(s).")

    for doc in docs:
        doc_id = value(doc, "id", default="")
        titre = value(doc, "titre", "nom", "libelle", default="Document")
        type_document = value(doc, "type_document", "type", default="Document")
        date_document = value(doc, "date_document", "date", "created_at", default="")
        fichier_nom = value(doc, "fichier_nom", "fichier", "filename", default="")
        commentaire = value(doc, "commentaire", "description", default="")
        taille = value(doc, "taille_ko", "taille", default="")

        file_path = find_existing_file(str(fichier_nom), doc)

        with st.container(border=True):
            c1, c2 = st.columns([3, 1])

            with c1:
                st.write(f"**{titre}**")
                st.caption(f"{type_document} — {date_document} — {fichier_nom}")
                if commentaire:
                    st.write(commentaire)
                if taille not in ["", None]:
                    st.caption(f"Taille : {fmt_size_ko(taille)}")
                if file_path:
                    st.caption(f"Fichier : `{file_path}`")

            with c2:
                if file_path and file_path.exists():
                    with open(file_path, "rb") as f:
                        mime, _ = mimetypes.guess_type(str(file_path))
                        st.download_button(
                            "Télécharger",
                            data=f.read(),
                            file_name=file_path.name,
                            mime=mime or "application/octet-stream",
                            key=f"catalogue_bat_doc_download_{doc_id}_{file_path.name}",
                            width="stretch",
                        )
                else:
                    st.warning("Fichier introuvable")

            if file_path and file_path.exists():
                with st.expander("👁️ Voir le document", expanded=False):
                    render_file_preview(file_path)
            else:
                with st.expander("🔎 Diagnostic fichier introuvable", expanded=False):
                    st.write("Nom en base :", fichier_nom)
                    st.write("Dossiers recherchés :")
                    for folder in DOC_DIR_CANDIDATES:
                        st.code(str(folder), language="bash")
