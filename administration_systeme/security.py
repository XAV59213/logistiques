# -*- coding: utf-8 -*-
from __future__ import annotations

import sqlite3
from pathlib import Path

import streamlit as st

from administration_systeme.common import APP_DIR, get_db_files, fmt_size


SENSITIVE_FILES = [
    ".env",
    "config.py",
    "secrets.toml",
    ".streamlit/secrets.toml",
]


def check_file_permissions(path: Path):
    try:
        return oct(path.stat().st_mode)[-3:]
    except Exception:
        return "N/A"


def find_admins():
    results = []

    for db in get_db_files():
        try:
            conn = sqlite3.connect(str(db))
            cur = conn.cursor()

            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if not cur.fetchone():
                conn.close()
                continue

            cur.execute("PRAGMA table_info(users)")
            columns = [r[1] for r in cur.fetchall()]

            select_cols = []
            for col in ["id", "email", "username", "name", "role", "is_active", "validated"]:
                if col in columns:
                    select_cols.append(col)

            if not select_cols:
                conn.close()
                continue

            query = f"SELECT {', '.join(select_cols)} FROM users"

            if "role" in columns:
                query += " WHERE LOWER(role)='admin'"

            cur.execute(query)

            for row in cur.fetchall():
                results.append(
                    {
                        "base": db.name,
                        "colonnes": ", ".join(select_cols),
                        "valeurs": row,
                    }
                )

            conn.close()

        except Exception:
            pass

    return results


def render():
    st.subheader("🔐 Sécurité")

    st.info("Contrôles rapides : fichiers sensibles, permissions, comptes administrateurs et fichiers volumineux.")

    st.markdown("### Fichiers sensibles")

    for rel in SENSITIVE_FILES:
        path = APP_DIR / rel
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(str(path))
        c2.write("Présent" if path.exists() else "Absent")
        c3.write(check_file_permissions(path) if path.exists() else "-")

    st.divider()

    st.markdown("### Comptes administrateurs détectés")

    admins = find_admins()

    if not admins:
        st.warning("Aucun compte admin détecté dans les bases contenant une table users, ou structure inconnue.")
    else:
        for admin in admins:
            with st.container(border=True):
                st.write(f"**Base : {admin['base']}**")
                st.caption(admin["colonnes"])
                st.write(admin["valeurs"])

    st.divider()

    st.markdown("### Fichiers volumineux dans le projet")

    large_files = []

    for p in APP_DIR.rglob("*"):
        try:
            if p.is_file():
                if ".venv" in str(p) or "/.git/" in str(p):
                    continue

                size = p.stat().st_size

                if size > 100 * 1024 * 1024:
                    large_files.append((p, size))
        except Exception:
            pass

    if not large_files:
        st.success("Aucun fichier supérieur à 100 Mo détecté hors .venv/.git.")
    else:
        for p, size in sorted(large_files, key=lambda x: x[1], reverse=True):
            st.warning(f"{p} — {fmt_size(size)}")

    st.divider()

    st.markdown("### Recommandations")
    st.write("- Ne jamais exposer `.env` ou `secrets.toml` publiquement.")
    st.write("- Garder au moins un compte admin validé.")
    st.write("- Éviter les sauvegardes ZIP géantes dans l’application.")
    st.write("- Ajouter un swap serveur pour limiter les `oom-kill`.")
