# -*- coding: utf-8 -*-
import streamlit as st

from administration_systeme.common import (
    fmt_size,
    get_db_files,
    sqlite_count,
    sqlite_tables,
)


def render():
    st.subheader("Toutes les bases de données")

    dbs = get_db_files()

    if not dbs:
        st.warning("Aucune base SQLite détectée.")
        return

    st.success(f"{len(dbs)} base(s) SQLite détectée(s).")

    st.markdown("### Liste des bases")

    for db in dbs:
        tables = sqlite_tables(db)

        c1, c2, c3 = st.columns([2, 4, 1])
        c1.write(f"**{db.name}**")
        c2.caption(str(db))
        c3.write(fmt_size(db.stat().st_size) if db.exists() else "N/A")

        st.caption(f"{len(tables)} table(s)")
        st.divider()

    selected_name = st.selectbox(
        "Choisir une base à contrôler",
        [db.name for db in dbs],
        key="admin_selected_db_modules",
    )

    selected_db = next((db for db in dbs if db.name == selected_name), dbs[0])

    st.markdown(f"### Détail : `{selected_db.name}`")
    st.caption(str(selected_db))

    tables = sqlite_tables(selected_db)

    if not tables:
        st.warning("Aucune table détectée.")
        return

    for table in tables:
        c1, c2 = st.columns([3, 1])
        c1.write(table)
        c2.write(sqlite_count(selected_db, table))

    st.markdown("### Compteurs rapides")

    cols = st.columns(4)

    for i, table in enumerate(tables):
        cols[i % 4].metric(table, sqlite_count(selected_db, table))
