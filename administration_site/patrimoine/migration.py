# -*- coding: utf-8 -*-
from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from .db import connect, get_db_path, get_tables, read_table, table_columns


PROJECT_DIR = Path("/opt/logistique-pro")
DATA_DIR = PROJECT_DIR / "data"
BACKUP_DIR = DATA_DIR / "patch_backups"
EXPORT_DIR = DATA_DIR / "exports" / "patrimoine"

BACKUP_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


OLD_BATIMENTS = "batiments"
OLD_CONTROLES = "controle_batiments"
OLD_ENTRETIENS = "batiment_entretiens"
OLD_TYPES = "entretien_types"

CLEAN_BATIMENTS = "patrimoine_batiments_clean"
CLEAN_CONTROLES = "patrimoine_controles_clean"
CLEAN_ENTRETIENS = "patrimoine_entretiens_clean"
CLEAN_TYPES = "patrimoine_entretien_types_clean"


def _clean(value: Any) -> str:
    if value is None:
        return ""
    value = str(value)
    if value.lower() in ["none", "nan", "nat"]:
        return ""
    return value.strip()


def _to_float(value: Any) -> float:
    value = _clean(value).replace(",", ".")
    try:
        return float(value)
    except Exception:
        return 0.0


def _to_int_or_none(value: Any):
    value = _clean(value)
    if not value:
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def _date_to_iso(value: Any) -> str:
    value = _clean(value)
    if not value:
        return ""

    try:
        parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
        if pd.isna(parsed):
            return value
        return parsed.strftime("%Y-%m-%d")
    except Exception:
        return value


def _first(row: pd.Series, keys: list[str], default: Any = ""):
    for key in keys:
        if key in row.index:
            value = row.get(key)
            if not _clean(value):
                continue
            return value
    return default


def _table_exists(table: str) -> bool:
    return table in get_tables()


def _safe_read(table: str) -> pd.DataFrame:
    if not _table_exists(table):
        return pd.DataFrame()
    try:
        return read_table(table)
    except Exception:
        return pd.DataFrame()


def backup_database() -> Path:
    src = get_db_path()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"patrimoine_bati_before_clean_migration_{timestamp}.db"
    shutil.copy2(src, dest)
    return dest


def create_clean_schema() -> None:
    conn = connect()
    try:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {CLEAN_BATIMENTS} (
                id INTEGER PRIMARY KEY,
                ancien_id INTEGER,
                nom TEXT NOT NULL,
                type_batiment TEXT DEFAULT '',
                adresse TEXT DEFAULT '',
                code_postal TEXT DEFAULT '',
                ville TEXT DEFAULT '',
                surface REAL DEFAULT 0,
                valeur_estimee REAL DEFAULT 0,
                annee_construction INTEGER,
                etat TEXT DEFAULT '',
                responsable TEXT DEFAULT '',
                telephone TEXT DEFAULT '',
                email TEXT DEFAULT '',
                photo_path TEXT DEFAULT '',
                image_path TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                actif INTEGER DEFAULT 1,
                source_table TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {CLEAN_CONTROLES} (
                id INTEGER PRIMARY KEY,
                ancien_id INTEGER,
                batiment_id INTEGER,
                ancien_batiment_id INTEGER,
                domaine TEXT DEFAULT '',
                type_controle TEXT DEFAULT '',
                detail_controle TEXT DEFAULT '',
                libelle_prestation TEXT DEFAULT '',
                date_debut TEXT DEFAULT '',
                date_intervention TEXT DEFAULT '',
                date_controle TEXT DEFAULT '',
                date_prochain TEXT DEFAULT '',
                organisme TEXT DEFAULT '',
                statut TEXT DEFAULT '',
                resultat TEXT DEFAULT '',
                reference TEXT DEFAULT '',
                identifiant_activite TEXT DEFAULT '',
                nom_site TEXT DEFAULT '',
                ville_site TEXT DEFAULT '',
                commentaire TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                actif INTEGER DEFAULT 1,
                source_table TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {CLEAN_TYPES} (
                id INTEGER PRIMARY KEY,
                ancien_id INTEGER,
                nom TEXT NOT NULL,
                periodicite_mois INTEGER DEFAULT 12,
                actif INTEGER DEFAULT 1,
                source_table TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {CLEAN_ENTRETIENS} (
                id INTEGER PRIMARY KEY,
                ancien_id INTEGER,
                batiment_id INTEGER,
                ancien_batiment_id INTEGER,
                type_id INTEGER,
                ancien_type_id INTEGER,
                type_entretien TEXT DEFAULT '',
                date_entretien TEXT DEFAULT '',
                date_prochain TEXT DEFAULT '',
                fournisseur TEXT DEFAULT '',
                montant REAL DEFAULT 0,
                statut TEXT DEFAULT '',
                commentaire TEXT DEFAULT '',
                actif INTEGER DEFAULT 1,
                source_table TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS patrimoine_migration_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_migration TEXT DEFAULT CURRENT_TIMESTAMP,
                action TEXT,
                detail TEXT,
                statut TEXT
            )
            """
        )

        conn.commit()
    finally:
        conn.close()


def clear_clean_tables() -> None:
    conn = connect()
    try:
        for table in [CLEAN_BATIMENTS, CLEAN_CONTROLES, CLEAN_ENTRETIENS, CLEAN_TYPES]:
            conn.execute(f"DELETE FROM {table}")
        conn.commit()
    finally:
        conn.close()


def migrate_batiments() -> int:
    df = _safe_read(OLD_BATIMENTS)
    if df.empty:
        return 0

    rows = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for _, row in df.iterrows():
        ancien_id = _to_int_or_none(_first(row, ["id"], None))
        if ancien_id is None:
            continue

        nom = _clean(
            _first(
                row,
                [
                    "nom",
                    "designation",
                    "libelle",
                    "libellé",
                    "nom_batiment",
                    "batiment",
                    "site",
                    "nom_site",
                ],
                f"Bâtiment {ancien_id}",
            )
        )

        rows.append(
            {
                "id": ancien_id,
                "ancien_id": ancien_id,
                "nom": nom or f"Bâtiment {ancien_id}",
                "type_batiment": _clean(_first(row, ["type_batiment", "type", "categorie", "catégorie"])),
                "adresse": _clean(_first(row, ["adresse", "address"])),
                "code_postal": _clean(_first(row, ["code_postal", "cp", "postal"])),
                "ville": _clean(_first(row, ["ville", "commune"])),
                "surface": _to_float(_first(row, ["surface", "surface_m2", "surface_totale"], 0)),
                "valeur_estimee": _to_float(_first(row, ["valeur_estimee", "valeur", "valeur_patrimoniale"], 0)),
                "annee_construction": _to_int_or_none(_first(row, ["annee_construction", "annee", "construction"], None)),
                "etat": _clean(_first(row, ["etat", "etat_general", "statut"])),
                "responsable": _clean(_first(row, ["responsable", "agent", "service"])),
                "telephone": _clean(_first(row, ["telephone", "tel"])),
                "email": _clean(_first(row, ["email", "mail"])),
                "photo_path": _clean(_first(row, ["photo_path", "photo", "image_path", "image"])),
                "image_path": _clean(_first(row, ["image_path", "photo_path", "photo", "image"])),
                "notes": _clean(_first(row, ["notes", "commentaire", "commentaires", "observations"])),
                "actif": _to_int_or_none(_first(row, ["actif"], 1)) or 1,
                "source_table": OLD_BATIMENTS,
                "created_at": _clean(_first(row, ["created_at"], now)) or now,
                "updated_at": now,
            }
        )

    if not rows:
        return 0

    conn = connect()
    try:
        for item in rows:
            columns = ", ".join(item.keys())
            placeholders = ", ".join(["?"] * len(item))
            conn.execute(
                f"INSERT OR REPLACE INTO {CLEAN_BATIMENTS} ({columns}) VALUES ({placeholders})",
                tuple(item.values()),
            )
        conn.commit()
    finally:
        conn.close()

    return len(rows)


def migrate_controles() -> int:
    df = _safe_read(OLD_CONTROLES)
    if df.empty:
        return 0

    rows = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for _, row in df.iterrows():
        ancien_id = _to_int_or_none(_first(row, ["id"], None))
        if ancien_id is None:
            continue

        batiment_id = _to_int_or_none(_first(row, ["batiment_id", "id_batiment", "id_bat", "site_id"], None))

        domaine = _clean(_first(row, ["domaine", "type_controle", "controle", "type", "categorie"], ""))
        prestation = _clean(_first(row, ["libelle_prestation", "detail_controle", "libelle", "designation", "nom"], ""))

        date_debut = _date_to_iso(_first(row, ["date_debut", "date_controle", "date"], ""))
        date_intervention = _date_to_iso(_first(row, ["date_intervention", "date_prochain", "date_echeance", "echeance"], ""))

        rows.append(
            {
                "id": ancien_id,
                "ancien_id": ancien_id,
                "batiment_id": batiment_id,
                "ancien_batiment_id": batiment_id,
                "domaine": domaine,
                "type_controle": domaine or prestation,
                "detail_controle": prestation,
                "libelle_prestation": prestation,
                "date_debut": date_debut,
                "date_intervention": date_intervention,
                "date_controle": date_debut or date_intervention,
                "date_prochain": date_intervention or date_debut,
                "organisme": _clean(_first(row, ["organisme", "prestataire", "societe", "société", "entreprise"])),
                "statut": _clean(_first(row, ["statut", "etat", "status"])),
                "resultat": _clean(_first(row, ["resultat", "conformite", "conformité", "avis"])),
                "reference": _clean(_first(row, ["reference", "référence"])),
                "identifiant_activite": _clean(_first(row, ["identifiant_activite", "activite", "activité"])),
                "nom_site": _clean(_first(row, ["nom_site", "batiment_nom", "batiment", "site"])),
                "ville_site": _clean(_first(row, ["ville_site", "ville", "commune"])),
                "commentaire": _clean(_first(row, ["commentaire", "notes", "observations"])),
                "notes": _clean(_first(row, ["notes", "commentaire", "observations"])),
                "actif": _to_int_or_none(_first(row, ["actif"], 1)) or 1,
                "source_table": OLD_CONTROLES,
                "created_at": _clean(_first(row, ["created_at"], now)) or now,
                "updated_at": now,
            }
        )

    if not rows:
        return 0

    conn = connect()
    try:
        for item in rows:
            columns = ", ".join(item.keys())
            placeholders = ", ".join(["?"] * len(item))
            conn.execute(
                f"INSERT OR REPLACE INTO {CLEAN_CONTROLES} ({columns}) VALUES ({placeholders})",
                tuple(item.values()),
            )
        conn.commit()
    finally:
        conn.close()

    return len(rows)


def migrate_types() -> int:
    df = _safe_read(OLD_TYPES)
    if df.empty:
        return 0

    rows = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for _, row in df.iterrows():
        ancien_id = _to_int_or_none(_first(row, ["id"], None))
        if ancien_id is None:
            continue

        nom = _clean(_first(row, ["nom", "libelle", "libellé", "designation", "type", "titre"], ""))

        if not nom:
            nom = f"Type {ancien_id}"

        rows.append(
            {
                "id": ancien_id,
                "ancien_id": ancien_id,
                "nom": nom,
                "periodicite_mois": _to_int_or_none(_first(row, ["periodicite_mois", "periodicite", "périodicité", "mois"], 12)) or 12,
                "actif": _to_int_or_none(_first(row, ["actif"], 1)) or 1,
                "source_table": OLD_TYPES,
                "created_at": _clean(_first(row, ["created_at"], now)) or now,
                "updated_at": now,
            }
        )

    if not rows:
        return 0

    conn = connect()
    try:
        for item in rows:
            columns = ", ".join(item.keys())
            placeholders = ", ".join(["?"] * len(item))
            conn.execute(
                f"INSERT OR REPLACE INTO {CLEAN_TYPES} ({columns}) VALUES ({placeholders})",
                tuple(item.values()),
            )
        conn.commit()
    finally:
        conn.close()

    return len(rows)


def migrate_entretiens() -> int:
    df = _safe_read(OLD_ENTRETIENS)
    if df.empty:
        return 0

    rows = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for _, row in df.iterrows():
        ancien_id = _to_int_or_none(_first(row, ["id"], None))
        if ancien_id is None:
            continue

        batiment_id = _to_int_or_none(_first(row, ["batiment_id", "id_batiment", "id_bat", "site_id"], None))
        type_id = _to_int_or_none(_first(row, ["type_id", "id_type", "entretien_type_id", "type_entretien_id"], None))

        rows.append(
            {
                "id": ancien_id,
                "ancien_id": ancien_id,
                "batiment_id": batiment_id,
                "ancien_batiment_id": batiment_id,
                "type_id": type_id,
                "ancien_type_id": type_id,
                "type_entretien": _clean(_first(row, ["type_entretien", "entretien", "type", "libelle", "nom"], "")),
                "date_entretien": _date_to_iso(_first(row, ["date_entretien", "date_intervention", "date_debut", "date"], "")),
                "date_prochain": _date_to_iso(_first(row, ["date_prochain", "date_prevue", "date_echeance", "echeance"], "")),
                "fournisseur": _clean(_first(row, ["fournisseur", "prestataire", "societe", "société", "organisme"])),
                "montant": _to_float(_first(row, ["montant", "cout", "coût", "prix", "total"], 0)),
                "statut": _clean(_first(row, ["statut", "etat", "status"])),
                "commentaire": _clean(_first(row, ["commentaire", "notes", "observations"])),
                "actif": _to_int_or_none(_first(row, ["actif"], 1)) or 1,
                "source_table": OLD_ENTRETIENS,
                "created_at": _clean(_first(row, ["created_at"], now)) or now,
                "updated_at": now,
            }
        )

    if not rows:
        return 0

    conn = connect()
    try:
        for item in rows:
            columns = ", ".join(item.keys())
            placeholders = ", ".join(["?"] * len(item))
            conn.execute(
                f"INSERT OR REPLACE INTO {CLEAN_ENTRETIENS} ({columns}) VALUES ({placeholders})",
                tuple(item.values()),
            )
        conn.commit()
    finally:
        conn.close()

    return len(rows)


def write_log(action: str, detail: str, statut: str = "OK") -> None:
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO patrimoine_migration_log (action, detail, statut) VALUES (?, ?, ?)",
            (action, detail, statut),
        )
        conn.commit()
    finally:
        conn.close()


def run_migration(clear_before: bool = True) -> dict[str, Any]:
    backup = backup_database()
    create_clean_schema()

    if clear_before:
        clear_clean_tables()

    result = {
        "backup": str(backup),
        "batiments": migrate_batiments(),
        "controles": migrate_controles(),
        "types": migrate_types(),
        "entretiens": migrate_entretiens(),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    detail = (
        f"batiments={result['batiments']}, "
        f"controles={result['controles']}, "
        f"types={result['types']}, "
        f"entretiens={result['entretiens']}, "
        f"backup={result['backup']}"
    )

    write_log("migration_clean", detail, "OK")

    return result


def compare_tables() -> pd.DataFrame:
    rows = []

    pairs = [
        (OLD_BATIMENTS, CLEAN_BATIMENTS),
        (OLD_CONTROLES, CLEAN_CONTROLES),
        (OLD_TYPES, CLEAN_TYPES),
        (OLD_ENTRETIENS, CLEAN_ENTRETIENS),
    ]

    for old, clean in pairs:
        old_count = 0
        clean_count = 0

        if _table_exists(old):
            old_count = len(_safe_read(old))

        if _table_exists(clean):
            clean_count = len(_safe_read(clean))

        rows.append(
            {
                "ancienne_table": old,
                "ancienne_lignes": old_count,
                "table_clean": clean,
                "clean_lignes": clean_count,
                "écart": clean_count - old_count,
            }
        )

    return pd.DataFrame(rows)


def get_migration_log() -> pd.DataFrame:
    if not _table_exists("patrimoine_migration_log"):
        return pd.DataFrame()

    try:
        return read_table("patrimoine_migration_log").sort_values("id", ascending=False)
    except Exception:
        return pd.DataFrame()


def export_clean_tables_csv() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = EXPORT_DIR / f"migration_clean_export_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    for table in [CLEAN_BATIMENTS, CLEAN_CONTROLES, CLEAN_ENTRETIENS, CLEAN_TYPES]:
        if _table_exists(table):
            df = read_table(table)
            df.to_csv(out_dir / f"{table}.csv", index=False, encoding="utf-8-sig")

    zip_path = EXPORT_DIR / f"migration_clean_export_{timestamp}.zip"

    import zipfile

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for file in out_dir.glob("*.csv"):
            z.write(file, arcname=file.name)

    return zip_path


def render() -> None:
    st.markdown("### 🧬 Migration propre Patrimoine")
    st.caption(f"Base utilisée : {get_db_path()}")

    st.warning(
        "Ce module ne supprime pas les anciennes tables. "
        "Il crée des tables propres *_clean et copie les données dedans."
    )

    tabs = st.tabs(
        [
            "▶️ Migration",
            "📊 Comparaison",
            "🗄️ Tables clean",
            "📜 Historique",
            "📥 Export clean",
        ]
    )

    with tabs[0]:
        st.markdown("#### Lancer la migration propre")

        st.info(
            "Une sauvegarde de la base sera créée automatiquement avant chaque migration."
        )

        clear_before = st.checkbox(
            "Vider les tables clean avant de recopier",
            value=True,
            help="Recommandé pour éviter les doublons dans les tables clean.",
        )

        confirm = st.checkbox("Je confirme lancer la migration propre")

        if st.button("▶️ Lancer la migration", disabled=not confirm, width="stretch"):
            try:
                result = run_migration(clear_before=clear_before)
                st.success("Migration terminée avec succès.")
                st.json(result)
            except Exception as exc:
                write_log("migration_clean", str(exc), "ERREUR")
                st.error(f"Erreur migration : {exc}")

    with tabs[1]:
        st.markdown("#### Comparaison anciennes tables / tables clean")
        create_clean_schema()
        comparison = compare_tables()
        st.dataframe(comparison, width="stretch", hide_index=True)

    with tabs[2]:
        st.markdown("#### Tables clean")

        create_clean_schema()

        table = st.selectbox(
            "Table clean",
            [CLEAN_BATIMENTS, CLEAN_CONTROLES, CLEAN_ENTRETIENS, CLEAN_TYPES],
        )

        if _table_exists(table):
            df = read_table(table)
            st.caption(f"{len(df)} ligne(s)")
            st.dataframe(df.head(300), width="stretch", hide_index=True)
        else:
            st.info("Table non créée.")

    with tabs[3]:
        st.markdown("#### Historique migrations")

        log = get_migration_log()

        if log.empty:
            st.info("Aucun historique.")
        else:
            st.dataframe(log, width="stretch", hide_index=True)

    with tabs[4]:
        st.markdown("#### Export CSV des tables clean")

        if st.button("📦 Générer ZIP des tables clean", width="stretch"):
            try:
                path = export_clean_tables_csv()
                st.success(f"Export généré : {path}")

                with open(path, "rb") as f:
                    st.download_button(
                        "📥 Télécharger le ZIP",
                        data=f.read(),
                        file_name=path.name,
                        mime="application/zip",
                        width="stretch",
                    )
            except Exception as exc:
                st.error(f"Erreur export : {exc}")


def show() -> None:
    render()
