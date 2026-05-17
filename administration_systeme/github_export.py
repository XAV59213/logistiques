# -*- coding: utf-8 -*-
from __future__ import annotations

import sqlite3
import subprocess
import tarfile
from datetime import datetime
from pathlib import Path

import streamlit as st

from administration_systeme.common import APP_DIR, DATA_DIR, PATCH_BACKUP_DIR, fmt_size


EMPTY_DB_DIR = DATA_DIR / "db_empty"
EMPTY_DB_DIR.mkdir(parents=True, exist_ok=True)


GITIGNORE_CONTENT = """# Environnements Python
.venv/
venv/
env/
ENV/
__pycache__/
*.pyc
*.pyo
*.pyd

# Fichiers secrets
.env
.env.*
!.env.example
!Logistique_Pro/.env.example
secrets.toml
.streamlit/secrets.toml

# Logs
*.log
logs/
data/logs/

# Sauvegardes
data/backups/
data/patch_backups/
Logistique_Pro/data/backups/
Logistique_Pro/data/patch_backups/
backups/
*.zip
*.tar
*.tar.gz
*.7z
*.rar
*.bak

# Bases réelles avec données
*.db
*.sqlite
*.sqlite3

# Bases vides autorisées
!data/db_empty/
!data/db_empty/*.db
!data/db_empty/*.sqlite
!data/db_empty/*.sqlite3

# Imports / exports locaux
data/imports/
data/exports/

# Données runtime locales
data/inventaires/
data/reservations/
data/stock/
data/patrimoine_db_path.txt

# Images / médias / uploads
assets/photos/
assets/images/
assets/uploads/
uploads/
static/uploads/
static/images/
*.png
*.jpg
*.jpeg
*.gif
*.webp
*.bmp
*.tiff
*.ico
*.svg
*.mp4
*.mov
*.avi
*.mkv
*.mp3
*.wav
*.pdf

# Pages / dossiers désactivés
pages_disabled/
Logistique_Pro/pages_disabled/

# Système / IDE
.DS_Store
Thumbs.db
.cache/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.vscode/
.idea/
"""


def run_cmd(cmd: list[str], timeout: int = 120) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            cmd,
            cwd=str(APP_DIR),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

        output = ""

        if result.stdout:
            output += result.stdout.strip()

        if result.stderr:
            output += ("\n\n" if output else "") + result.stderr.strip()

        return result.returncode == 0, output or f"Code retour : {result.returncode}"

    except subprocess.TimeoutExpired:
        return False, f"Commande trop longue : timeout après {timeout} secondes."
    except Exception as exc:
        return False, str(exc)


def is_git_repo() -> bool:
    return (APP_DIR / ".git").exists()


def current_branch() -> str:
    ok, out = run_cmd(["git", "branch", "--show-current"], timeout=20)
    if ok and out.strip():
        return out.strip()
    return "main"


def create_local_backup() -> Path:
    backup = PATCH_BACKUP_DIR / f"before_github_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"

    excluded_parts = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "backups",
        "patch_backups",
        "pages_disabled",
    }

    with tarfile.open(backup, "w:gz") as tar:
        for path in APP_DIR.rglob("*"):
            try:
                rel = path.relative_to(APP_DIR)
                if set(rel.parts) & excluded_parts:
                    continue
                tar.add(path, arcname=str(rel))
            except Exception:
                pass

    return backup


def write_gitignore() -> Path:
    path = APP_DIR / ".gitignore"
    path.write_text(GITIGNORE_CONTENT, encoding="utf-8")
    return path


def find_real_databases() -> list[Path]:
    excluded_parts = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "backups",
        "patch_backups",
        "db_empty",
    }

    results: list[Path] = []

    for pattern in ("*.db", "*.sqlite", "*.sqlite3"):
        for db in APP_DIR.rglob(pattern):
            try:
                rel = db.relative_to(APP_DIR)
                if set(rel.parts) & excluded_parts:
                    continue
                if db.is_file():
                    results.append(db)
            except Exception:
                pass

    unique = []
    seen = set()

    for db in results:
        key = str(db.resolve())
        if key not in seen:
            unique.append(db)
            seen.add(key)

    return sorted(unique, key=lambda p: str(p))


def empty_db_name(source_db: Path) -> str:
    if source_db.suffix == ".db":
        return f"{source_db.stem}_empty.db"
    if source_db.suffix == ".sqlite":
        return f"{source_db.stem}_empty.sqlite"
    if source_db.suffix == ".sqlite3":
        return f"{source_db.stem}_empty.sqlite3"
    return f"{source_db.name}_empty.db"


def create_empty_db_copy(source_db: Path) -> Path:
    target = EMPTY_DB_DIR / empty_db_name(source_db)

    if target.exists():
        target.unlink()

    src = sqlite3.connect(str(source_db))
    dst = sqlite3.connect(str(target))
    src.row_factory = sqlite3.Row

    cur = src.cursor()

    cur.execute(
        """
        SELECT type, name, tbl_name, sql
        FROM sqlite_master
        WHERE sql IS NOT NULL
          AND name NOT LIKE 'sqlite_%'
        ORDER BY
          CASE type
            WHEN 'table' THEN 1
            WHEN 'index' THEN 2
            WHEN 'view' THEN 3
            WHEN 'trigger' THEN 4
            ELSE 5
          END
        """
    )

    objects = cur.fetchall()
    errors = []

    for obj in objects:
        sql = obj["sql"]

        if not sql:
            continue

        try:
            dst.execute(sql)
        except Exception as exc:
            errors.append(f"{obj['type']} {obj['name']} : {exc}")

    dst.commit()
    src.close()
    dst.close()

    return target


def create_all_empty_databases() -> list[Path]:
    created = []

    for source_db in find_real_databases():
        try:
            created.append(create_empty_db_copy(source_db))
        except Exception as exc:
            st.warning(f"Erreur avec {source_db.name} : {exc}")

    return created


def remove_cached_excluded_files() -> str:
    commands = [
        ["git", "rm", "-r", "--cached", ".venv"],
        ["git", "rm", "-r", "--cached", "venv"],
        ["git", "rm", "-r", "--cached", "env"],
        ["git", "rm", "-r", "--cached", "ENV"],
        ["git", "rm", "-r", "--cached", "data/backups"],
        ["git", "rm", "-r", "--cached", "data/patch_backups"],
        ["git", "rm", "-r", "--cached", "Logistique_Pro/data/patch_backups"],
        ["git", "rm", "-r", "--cached", "Logistique_Pro/data/backups"],
        ["git", "rm", "-r", "--cached", "backups"],
        ["git", "rm", "-r", "--cached", "pages_disabled"],
        ["git", "rm", "-r", "--cached", "Logistique_Pro/pages_disabled"],
        ["git", "rm", "-r", "--cached", "assets/photos"],
        ["git", "rm", "-r", "--cached", "assets/images"],
        ["git", "rm", "-r", "--cached", "assets/uploads"],
        ["git", "rm", "-r", "--cached", "uploads"],
        ["git", "rm", "-r", "--cached", "static/uploads"],
        ["git", "rm", "-r", "--cached", "static/images"],
    ]

    output = []

    for cmd in commands:
        ok, out = run_cmd(cmd, timeout=60)
        if out:
            output.append(f"$ {' '.join(cmd)}\n{out}")

    shell_commands = [
        "git ls-files | grep -Ei '\\.(png|jpg|jpeg|gif|webp|bmp|tiff|ico|svg|mp4|mov|avi|mkv|mp3|wav|pdf)$' | xargs -r git rm --cached --",
        "git ls-files | grep -Ei '\\.(zip|tar|tar\\.gz|7z|rar|log|bak)$' | xargs -r git rm --cached --",
        "git ls-files | grep -Ei '(^|/)\\.env(\\.|$)|secrets\\.toml$' | xargs -r git rm --cached --",
        "git ls-files | grep -Ei '\\.(db|sqlite|sqlite3)$' | grep -v '^data/db_empty/' | xargs -r git rm --cached --",
    ]

    for cmd in shell_commands:
        ok, out = run_cmd(["bash", "-lc", cmd], timeout=120)
        if out:
            output.append(f"$ {cmd}\n{out}")

    return "\n\n".join(output) or "Aucun fichier exclu à retirer du suivi Git."


def git_add_files() -> tuple[bool, str]:
    commands = [
        ["git", "add", ".gitignore"],
        ["git", "add", ".env.example"],
        ["git", "add", "Logistique_Pro/.env.example"],
        ["git", "add", "administration_systeme/"],
        ["git", "add", "pages/Administration_Systeme.py"],
        ["git", "add", "data/db_empty/"],
    ]

    outputs = []

    for cmd in commands:
        ok, out = run_cmd(cmd, timeout=120)
        if not ok:
            return False, out
        if out:
            outputs.append(out)

    return True, "\n".join(outputs) or "Fichiers ajoutés à l'index Git."


def git_commit(message: str) -> tuple[bool, str]:
    ok, diff = run_cmd(["git", "diff", "--cached", "--quiet"], timeout=60)

    if ok:
        return True, "Aucun changement à committer."

    return run_cmd(["git", "commit", "-m", message], timeout=120)


def git_push(branch: str) -> tuple[bool, str]:
    return run_cmd(["git", "push", "origin", branch], timeout=180)


def render_status():
    st.markdown("### État Git")

    if not is_git_repo():
        st.error(f"{APP_DIR} n'est pas un dépôt Git.")
        return

    ok_remote, remote = run_cmd(["git", "remote", "-v"], timeout=20)
    ok_status, status = run_cmd(["git", "status", "--short"], timeout=20)
    branch = current_branch()

    c1, c2 = st.columns(2)
    c1.metric("Branche", branch)
    c2.metric("Dépôt Git", "OK" if is_git_repo() else "Non")

    st.markdown("#### Remote")
    st.code(remote if ok_remote else "Remote introuvable.", language="bash")

    st.markdown("#### Changements")
    st.code(status or "Aucun changement détecté.", language="bash")


def render_databases_preview():
    st.markdown("### Bases réelles détectées")

    dbs = find_real_databases()

    if not dbs:
        st.info("Aucune base SQLite réelle détectée.")
        return

    for db in dbs:
        c1, c2, c3 = st.columns([3, 2, 1])
        c1.write(f"**{db.name}**")
        c2.caption(str(db.relative_to(APP_DIR)))
        c3.write(fmt_size(db.stat().st_size))


def render_empty_db_preview():
    st.markdown("### Bases vides générées")

    dbs = sorted(EMPTY_DB_DIR.glob("*"))

    if not dbs:
        st.info("Aucune base vide générée pour le moment.")
        return

    for db in dbs:
        c1, c2 = st.columns([3, 1])
        c1.write(f"**{db.name}**")
        c2.write(fmt_size(db.stat().st_size))


def render():
    st.subheader("🚀 Export GitHub")

    st.info(
        "Ce module exporte les modifications vers GitHub sans envoyer les images, les sauvegardes, "
        "les fichiers secrets ou les bases de données réelles. Il génère des copies vides des bases dans `data/db_empty/`."
    )

    if not is_git_repo():
        st.error("Le dossier /opt/logistique-pro ne contient pas de dépôt Git.")
        return

    render_status()

    st.divider()
    render_databases_preview()

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("1. Écrire / mettre à jour .gitignore", width="stretch", key="gh_export_gitignore"):
            path = write_gitignore()
            st.success(f".gitignore écrit : {path}")

    with col2:
        if st.button("2. Générer les bases vides", width="stretch", key="gh_export_empty_dbs"):
            created = create_all_empty_databases()
            st.success(f"{len(created)} base(s) vide(s) générée(s).")
            st.rerun()

    render_empty_db_preview()

    st.divider()

    st.markdown("### Nettoyage du suivi Git")

    st.warning(
        "Cette action ne supprime pas les fichiers du serveur. "
        "Elle les retire seulement du suivi Git s'ils étaient déjà suivis."
    )

    confirm_clean = st.checkbox(
        "Je confirme retirer du suivi Git les images, .env, sauvegardes et bases réelles",
        key="gh_export_confirm_clean",
    )

    if st.button("3. Nettoyer le suivi Git", disabled=not confirm_clean, width="stretch", key="gh_export_clean_cached"):
        out = remove_cached_excluded_files()
        st.code(out, language="bash")

    st.divider()

    st.markdown("### Commit et push")

    commit_message = st.text_input(
        "Message du commit",
        value="Mise à jour administration système modulaire et bases vides",
        key="gh_export_commit_message",
    )

    branch = st.text_input(
        "Branche GitHub",
        value=current_branch(),
        key="gh_export_branch",
    )

    confirm_push = st.checkbox(
        "Je confirme vouloir faire le commit et push vers GitHub",
        key="gh_export_confirm_push",
    )

    if st.button("4. Préparer + commit + push", disabled=not confirm_push, type="primary", width="stretch", key="gh_export_commit_push"):
        try:
            st.info("Création d'une sauvegarde locale avant export...")
            backup = create_local_backup()
            st.success(f"Sauvegarde locale créée : {backup.name}")

            st.info("Mise à jour du .gitignore...")
            write_gitignore()

            st.info("Génération des bases vides...")
            created = create_all_empty_databases()
            st.success(f"{len(created)} base(s) vide(s) générée(s).")

            st.info("Retrait du suivi Git des fichiers exclus...")
            clean_out = remove_cached_excluded_files()
            st.code(clean_out, language="bash")

            st.info("Ajout des fichiers autorisés...")
            ok_add, out_add = git_add_files()
            st.code(out_add, language="bash")

            if not ok_add:
                st.error("Erreur pendant git add.")
                return

            st.info("Commit...")
            ok_commit, out_commit = git_commit(commit_message)
            st.code(out_commit, language="bash")

            if not ok_commit:
                st.error("Erreur pendant git commit.")
                return

            st.info("Push GitHub...")
            ok_push, out_push = git_push(branch)
            st.code(out_push, language="bash")

            if ok_push:
                st.success("Export GitHub terminé avec succès.")
            else:
                st.error("Erreur pendant git push. Vérifie l'authentification GitHub.")

        except Exception as exc:
            st.error(f"Erreur export GitHub : {exc}")

    st.divider()

    if st.button("Actualiser le statut Git", width="stretch", key="gh_export_refresh_status"):
        st.rerun()
