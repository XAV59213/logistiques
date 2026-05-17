# -*- coding: utf-8 -*-
from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import streamlit as st

from administration_systeme.common import DATA_DIR, PATCH_BACKUP_DIR, fmt_size, get_db_files


def backup_db(db: Path) -> Path:
    target = PATCH_BACKUP_DIR / f"{db.stem}_before_db_tools_{datetime.now().strftime('%Y%m%d_%H%M%S')}{db.suffix}"
    shutil.copy2(db, target)
    return target


def run_pragma(db: Path, pragma: str):
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    cur.execute(pragma)
    rows = cur.fetchall()
    conn.close()
    return rows


def table_info(db: Path):
    rows = []
    try:
        conn = sqlite3.connect(str(db))
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]

        for table in tables:
            try:
                cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                count = cur.fetchone()[0]
            except Exception:
                count = "Erreur"

            rows.append({"Table": table, "Lignes": count})

        conn.close()
    except Exception:
        pass

    return rows


def vacuum_db(db: Path):
    conn = sqlite3.connect(str(db))
    conn.execute("VACUUM")
    conn.close()


def analyze_db(db: Path):
    conn = sqlite3.connect(str(db))
    conn.execute("ANALYZE")
    conn.close()


def create_sql_dump(db: Path) -> Path:
    export_dir = DATA_DIR / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    dump_file = export_dir / f"{db.stem}_dump_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"

    conn = sqlite3.connect(str(db))
    with open(dump_file, "w", encoding="utf-8") as f:
        for line in conn.iterdump():
            f.write(f"{line}\n")
    conn.close()

    return dump_file


def render():
    st.subheader("🧱 Outils bases de données")

    dbs = get_db_files()

    if not dbs:
        st.warning("Aucune base SQLite détectée.")
        return

    selected = st.selectbox(
        "Base à contrôler",
        [str(db) for db in dbs],
        format_func=lambda x: Path(x).name,
        key="db_tools_selected",
    )

    db = Path(selected)

    st.caption(str(db))
    st.metric("Taille", fmt_size(db.stat().st_size) if db.exists() else "N/A")

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Integrity check", width="stretch", key="db_integrity"):
            try:
                rows = run_pragma(db, "PRAGMA integrity_check")
                result = "\n".join(str(r[0]) for r in rows)

                if result.strip().lower() == "ok":
                    st.success("Base OK")
                else:
                    st.warning(result)

            except Exception as exc:
                st.error(f"Erreur integrity_check : {exc}")

    with col2:
        confirm_vacuum = st.checkbox("Confirmer VACUUM", key="confirm_vacuum")

        if st.button("VACUUM", disabled=not confirm_vacuum, width="stretch", key="db_vacuum"):
            try:
                backup = backup_db(db)
                vacuum_db(db)
                st.success(f"VACUUM terminé. Sauvegarde : {backup.name}")
                st.rerun()
            except Exception as exc:
                st.error(f"Erreur VACUUM : {exc}")

    with col3:
        confirm_analyze = st.checkbox("Confirmer ANALYZE", key="confirm_analyze")

        if st.button("ANALYZE", disabled=not confirm_analyze, width="stretch", key="db_analyze"):
            try:
                backup = backup_db(db)
                analyze_db(db)
                st.success(f"ANALYZE terminé. Sauvegarde : {backup.name}")
            except Exception as exc:
                st.error(f"Erreur ANALYZE : {exc}")

    st.divider()

    st.markdown("### Tables")

    rows = table_info(db)

    if not rows:
        st.info("Aucune table détectée.")
    else:
        for row in rows:
            c1, c2 = st.columns([3, 1])
            c1.write(row["Table"])
            c2.write(row["Lignes"])

    st.divider()

    st.markdown("### Dump SQL")

    if st.button("Créer un dump SQL", width="stretch", key="create_sql_dump"):
        try:
            dump = create_sql_dump(db)
            st.success(f"Dump créé : {dump}")
        except Exception as exc:
            st.error(f"Erreur dump : {exc}")
