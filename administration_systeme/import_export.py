# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import streamlit as st

from administration_systeme.common import DATA_DIR, PATCH_BACKUP_DIR, get_db_files, sqlite_tables, fmt_size


EXPORT_DIR = DATA_DIR / "exports"
IMPORT_DIR = DATA_DIR / "imports"

EXPORT_DIR.mkdir(parents=True, exist_ok=True)
IMPORT_DIR.mkdir(parents=True, exist_ok=True)


def backup_db(db: Path) -> Path:
    target = PATCH_BACKUP_DIR / f"{db.stem}_before_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}{db.suffix}"
    shutil.copy2(db, target)
    return target


def export_table_csv(db: Path, table: str) -> Path:
    target = EXPORT_DIR / f"{db.stem}_{table}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    cur.execute(f'SELECT * FROM "{table}"')
    rows = cur.fetchall()
    columns = [d[0] for d in cur.description]
    conn.close()

    with open(target, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(columns)
        writer.writerows(rows)

    return target


def preview_csv(uploaded_file, max_rows: int = 10):
    content = uploaded_file.getvalue().decode("utf-8-sig", errors="ignore").splitlines()
    reader = csv.DictReader(content, delimiter=";")
    rows = list(reader)
    columns = reader.fieldnames or []
    return columns, rows[:max_rows], rows


def import_csv_append(db: Path, table: str, uploaded_file) -> int:
    backup_db(db)

    columns, preview_rows, all_rows = preview_csv(uploaded_file, max_rows=10)

    if not all_rows:
        return 0

    conn = sqlite3.connect(str(db))
    cur = conn.cursor()

    cur.execute(f'PRAGMA table_info("{table}")')
    table_columns = [r[1] for r in cur.fetchall()]

    missing = [c for c in columns if c not in table_columns]
    if missing:
        conn.close()
        raise RuntimeError(f"Colonnes absentes de la table : {', '.join(missing)}")

    placeholders = ", ".join(["?"] * len(columns))
    quoted_cols = ", ".join([f'"{c}"' for c in columns])

    inserted = 0

    for row in all_rows:
        values = [row.get(c) for c in columns]
        cur.execute(f'INSERT INTO "{table}" ({quoted_cols}) VALUES ({placeholders})', values)
        inserted += 1

    conn.commit()
    conn.close()

    return inserted


def list_exports() -> list[Path]:
    files = []
    for pattern in ["*.csv", "*.sql"]:
        files.extend(EXPORT_DIR.glob(pattern))
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def render():
    st.subheader("📤 Import / Export")

    dbs = get_db_files()

    if not dbs:
        st.warning("Aucune base SQLite détectée.")
        return

    selected_db_str = st.selectbox(
        "Base de données",
        [str(db) for db in dbs],
        format_func=lambda x: Path(x).name,
        key="import_export_db",
    )

    db = Path(selected_db_str)
    tables = sqlite_tables(db)

    if not tables:
        st.warning("Aucune table détectée.")
        return

    table = st.selectbox("Table", tables, key="import_export_table")

    st.caption(f"Base : {db}")
    st.caption(f"Table : {table}")

    st.divider()

    st.markdown("### Export CSV")

    if st.button("Exporter cette table en CSV", width="stretch", key="export_csv"):
        try:
            target = export_table_csv(db, table)
            st.success(f"Export créé : {target.name}")

            with open(target, "rb") as f:
                st.download_button(
                    "Télécharger le CSV",
                    data=f.read(),
                    file_name=target.name,
                    mime="text/csv",
                    width="stretch",
                    key=f"download_csv_{target.name}",
                )

        except Exception as exc:
            st.error(f"Erreur export : {exc}")

    st.divider()

    st.markdown("### Import CSV dans une table existante")

    st.warning(
        "L'import ajoute des lignes dans la table choisie. "
        "Une sauvegarde de la base est créée automatiquement avant import."
    )

    uploaded = st.file_uploader("CSV à importer", type=["csv"], key="upload_csv_import")

    if uploaded is not None:
        try:
            columns, preview_rows, all_rows = preview_csv(uploaded, max_rows=10)

            st.info(f"{len(all_rows)} ligne(s) détectée(s).")
            st.caption("Colonnes détectées : " + ", ".join(columns))

            if preview_rows:
                st.markdown("#### Aperçu des premières lignes")
                for i, row in enumerate(preview_rows, start=1):
                    with st.expander(f"Ligne {i}", expanded=False):
                        st.json(row)

        except Exception as exc:
            st.error(f"Erreur lecture CSV : {exc}")

    confirm = st.checkbox("Je confirme vouloir importer ce CSV dans la table sélectionnée", key="confirm_csv_import")

    if uploaded is not None and st.button("Importer le CSV", disabled=not confirm, type="primary", width="stretch", key="run_csv_import"):
        try:
            inserted = import_csv_append(db, table, uploaded)
            st.success(f"Import terminé : {inserted} ligne(s) ajoutée(s).")
        except Exception as exc:
            st.error(f"Erreur import : {exc}")

    st.divider()

    st.markdown("### Exports existants")

    exports = list_exports()

    if not exports:
        st.info("Aucun export disponible.")
        return

    for export in exports[:20]:
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.write(f"**{export.name}**")
            c1.caption(f"{fmt_size(export.stat().st_size)} — {export}")

            with open(export, "rb") as f:
                c2.download_button(
                    "Télécharger",
                    data=f.read(),
                    file_name=export.name,
                    mime="text/csv" if export.suffix.lower() == ".csv" else "text/plain",
                    key=f"download_export_{export.name}",
                    width="stretch",
                )
