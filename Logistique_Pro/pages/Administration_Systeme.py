# -*- coding: utf-8 -*-
"""
Administration_Systeme.py
Page Administration Système allégée et sécurisée.

Objectif :
- éviter la page grisée Streamlit
- éviter les OOM kill
- éviter les redémarrages/kill depuis Streamlit
- fournir les outils essentiels : diagnostic, base, sauvegarde, GitHub
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import streamlit as st


THIS_FILE = Path(__file__).resolve()
PAGES_DIR = THIS_FILE.parent
BASE_DIR = PAGES_DIR.parent
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = DATA_DIR / "backups"
PATCH_BACKUP_DIR = DATA_DIR / "patch_backups"

for d in (DATA_DIR, BACKUP_DIR, PATCH_BACKUP_DIR):
    d.mkdir(parents=True, exist_ok=True)

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def is_admin() -> bool:
    user = st.session_state.get("user") or st.session_state.get("current_user") or {}
    role = str(user.get("role", "")).lower() if isinstance(user, dict) else ""
    return role == "admin" or st.session_state.get("role") == "admin"


def run_cmd(cmd: list[str], cwd: Path | None = None, timeout: int = 60) -> tuple[bool, str]:
    try:
        r = subprocess.run(
            cmd,
            cwd=str(cwd or BASE_DIR),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        out = ""
        if r.stdout:
            out += r.stdout.strip()
        if r.stderr:
            out += ("\n\n" if out else "") + r.stderr.strip()
        return r.returncode == 0, out or f"Code retour : {r.returncode}"
    except subprocess.TimeoutExpired:
        return False, f"Timeout après {timeout} secondes."
    except Exception as exc:
        return False, str(exc)


def fmt_size(size: int) -> str:
    try:
        size = int(size)
    except Exception:
        return "N/A"
    for unit in ["o", "Ko", "Mo", "Go"]:
        if size < 1024:
            return f"{size:.1f} {unit}" if unit != "o" else f"{size} {unit}"
        size /= 1024
    return f"{size:.1f} To"


def find_db_files() -> list[Path]:
    files = []
    for root in [DATA_DIR, BASE_DIR]:
        if root.exists():
            files.extend(root.glob("*.db"))
            files.extend(root.glob("*.sqlite"))
            files.extend(root.glob("*.sqlite3"))

    # Ajoute la base depuis config.py si disponible
    try:
        from config import Config
        if hasattr(Config, "DB_PATH"):
            files.append(Path(Config.DB_PATH))
    except Exception:
        pass

    unique = []
    seen = set()
    for f in files:
        try:
            key = str(f.resolve())
        except Exception:
            key = str(f)
        if key not in seen:
            unique.append(f)
            seen.add(key)

    return unique


def table_count(db: Path, table: str) -> int | None:
    if not db.exists():
        return None
    try:
        con = sqlite3.connect(str(db))
        cur = con.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        value = int(cur.fetchone()[0])
        con.close()
        return value
    except Exception:
        return None


def render_diagnostic() -> None:
    st.subheader("Diagnostic")
    st.info("Cette version allégée ne charge pas les modules lourds automatiquement.")

    col1, col2, col3 = st.columns(3)
    col1.metric("Dossier application", BASE_DIR.name)
    col2.metric("Python", sys.version.split()[0])
    col3.metric("Dossier data", "OK" if DATA_DIR.exists() else "Manquant")

    st.code(str(BASE_DIR), language="bash")

    if st.button("Voir le statut Git", width="stretch"):
        for cmd in [
            ["git", "status", "-sb"],
            ["git", "branch", "--show-current"],
            ["git", "rev-parse", "--short", "HEAD"],
            ["git", "remote", "-v"],
        ]:
            ok, out = run_cmd(cmd, BASE_DIR, timeout=20)
            st.markdown(f"**`{' '.join(cmd)}`**")
            st.code(out, language="bash")


def render_database() -> None:
    st.subheader("Base de données")

    dbs = find_db_files()
    if not dbs:
        st.warning("Aucune base SQLite trouvée.")
        return

    rows = []
    for db in dbs:
        rows.append({
            "base": db.name,
            "chemin": str(db),
            "existe": db.exists(),
            "taille": fmt_size(db.stat().st_size) if db.exists() else "N/A",
        })

    st.dataframe(rows, hide_index=True, width="stretch")

    db = dbs[0]
    st.markdown(f"### Statistiques base principale : `{db.name}`")

    tables = [
        "users",
        "articles",
        "stock_items",
        "inventaire_items",
        "demandes",
        "messages",
        "notifications",
        "vehicules",
        "fournisseurs",
        "batiments",
        "controles_batiments",
    ]

    cols = st.columns(4)
    for i, table in enumerate(tables):
        count = table_count(db, table)
        cols[i % 4].metric(table, count if count is not None else "N/A")


def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    if ".git" in parts or ".venv" in parts or "venv" in parts or "__pycache__" in parts:
        return True
    if path.suffix.lower() in [".pyc", ".pyo", ".log"]:
        return True
    if "data/backups" in str(path):
        return True
    if "data/patch_backups" in str(path):
        return True
    return False


def render_backup() -> None:
    st.subheader("Sauvegarde simple")

    if st.button("Créer une sauvegarde ZIP du projet", type="primary", width="stretch"):
        backup = BACKUP_DIR / f"logistique_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

        try:
            with zipfile.ZipFile(backup, "w", zipfile.ZIP_DEFLATED) as z:
                for root, dirs, files in os.walk(BASE_DIR):
                    root_path = Path(root)
                    dirs[:] = [d for d in dirs if not should_skip(root_path / d)]

                    for file in files:
                        p = root_path / file
                        if should_skip(p):
                            continue
                        z.write(p, p.relative_to(BASE_DIR))

            st.success(f"Sauvegarde créée : {backup.name}")
        except Exception as exc:
            st.error(f"Erreur sauvegarde : {exc}")

    backups = sorted(BACKUP_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)

    if backups:
        st.markdown("### Dernières sauvegardes")
        for b in backups[:10]:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{b.name}**")
                c1.caption(fmt_size(b.stat().st_size))
                with open(b, "rb") as f:
                    c2.download_button(
                        "Télécharger",
                        data=f.read(),
                        file_name=b.name,
                        mime="application/zip",
                        key=f"download_{b.name}",
                        width="stretch",
                    )
    else:
        st.info("Aucune sauvegarde ZIP.")


def detect_git_root() -> Path:
    candidates = [
        BASE_DIR,
        BASE_DIR.parent,
        Path("/opt/logistique-pro/Logistique_Pro"),
        Path("/opt/logistique-pro"),
    ]

    for c in candidates:
        if (c / ".git").exists():
            return c.resolve()

    return BASE_DIR.resolve()


def render_github_update() -> None:
    st.subheader("Mise à jour GitHub sécurisée")

    repo = detect_git_root()

    st.info(
        "La mise à jour GitHub ne redémarre plus Streamlit automatiquement. "
        "Après un pull réussi, redémarre le service manuellement."
    )

    st.write("Dossier Git utilisé :")
    st.code(str(repo), language="bash")

    ok_branch, branch = run_cmd(["git", "branch", "--show-current"], repo, timeout=10)
    branch = branch.strip() if ok_branch and branch.strip() else "main"

    c1, c2, c3 = st.columns(3)
    c1.metric("Branche", branch)

    ok_commit, commit = run_cmd(["git", "rev-parse", "--short", "HEAD"], repo, timeout=10)
    c2.metric("Commit", commit.strip() if ok_commit else "N/A")

    ok_remote, remote = run_cmd(["git", "remote", "get-url", "origin"], repo, timeout=10)
    c3.metric("Remote", "OK" if ok_remote else "N/A")

    if ok_remote:
        st.caption(remote)

    if st.button("Vérifier les nouveautés", width="stretch"):
        ok, out = run_cmd(["git", "fetch", "--all", "--prune"], repo, timeout=60)
        if ok:
            st.success("Vérification terminée.")
        else:
            st.error("Erreur pendant git fetch.")
        st.code(out, language="bash")

        ok2, out2 = run_cmd(["git", "status", "-sb"], repo, timeout=20)
        st.code(out2, language="bash")

    st.divider()

    confirm = st.checkbox("Je confirme vouloir faire git pull depuis GitHub")

    if st.button("Mettre à jour maintenant", disabled=not confirm, type="primary", width="stretch"):
        backup = PATCH_BACKUP_DIR / f"before_git_pull_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

        try:
            with zipfile.ZipFile(backup, "w", zipfile.ZIP_DEFLATED) as z:
                for root, dirs, files in os.walk(BASE_DIR):
                    root_path = Path(root)
                    dirs[:] = [d for d in dirs if not should_skip(root_path / d)]
                    for file in files:
                        p = root_path / file
                        if should_skip(p):
                            continue
                        z.write(p, p.relative_to(BASE_DIR))
            st.success(f"Sauvegarde avant mise à jour : {backup.name}")
        except Exception as exc:
            st.error(f"Erreur sauvegarde avant mise à jour : {exc}")
            return

        ok, out = run_cmd(["git", "pull", "--ff-only", "origin", branch], repo, timeout=120)

        if ok:
            st.success("Mise à jour GitHub terminée.")
            st.warning("Redémarre maintenant le service avec la commande ci-dessous.")
            st.code("systemctl restart logistique.service", language="bash")
        else:
            st.error("Mise à jour échouée.")
            st.code(out, language="bash")


def render_service_help() -> None:
    st.subheader("Commandes serveur utiles")

    st.code("systemctl status logistique.service --no-pager -l", language="bash")
    st.code("journalctl -u logistique.service -n 120 --no-pager", language="bash")
    st.code("systemctl restart logistique.service", language="bash")
    st.code("free -h", language="bash")


def show() -> None:
    st.title("Administration Système")
    st.caption("Version allégée et sécurisée")

    if not is_admin():
        st.error("Accès réservé aux administrateurs.")
        st.stop()

    section = st.radio(
        "Section",
        ["Diagnostic", "Base de données", "Sauvegarde", "Mise à jour GitHub", "Aide serveur"],
        horizontal=True,
        label_visibility="collapsed",
        key="admin_system_light_section",
    )

    st.divider()

    if section == "Diagnostic":
        render_diagnostic()
    elif section == "Base de données":
        render_database()
    elif section == "Sauvegarde":
        render_backup()
    elif section == "Mise à jour GitHub":
        render_github_update()
    elif section == "Aide serveur":
        render_service_help()


if __name__ == "__main__":
    show()
