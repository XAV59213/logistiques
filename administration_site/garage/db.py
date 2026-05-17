# -*- coding: utf-8 -*-
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd


BASE_DIR = Path("/opt/logistique-pro")
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "garage_vehicules.db"
PHOTO_DIR = BASE_DIR / "assets" / "photos" / "garage_vehicules"


VEHICULE_COLUMNS: dict[str, str] = {
    "nom": "nom TEXT",
    "immatriculation": "immatriculation TEXT",
    "marque": "marque TEXT",
    "modele": "modele TEXT",
    "categorie": "categorie TEXT",
    "service": "service TEXT",
    "energie": "energie TEXT",
    "kilometrage_actuel": "kilometrage_actuel INTEGER DEFAULT 0",
    "date_mise_en_service": "date_mise_en_service TEXT",
    "date_ct": "date_ct TEXT",
    "assurance": "assurance TEXT",
    "statut": "statut TEXT DEFAULT 'Actif'",
    "actif": "actif INTEGER DEFAULT 1",
    "photo_path": "photo_path TEXT",
    "notes": "notes TEXT",
    "created_at": "created_at TEXT DEFAULT CURRENT_TIMESTAMP",
    "updated_at": "updated_at TEXT",
}


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def table_columns(table_name: str) -> set[str]:
    conn = connect()
    try:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {row["name"] for row in rows}
    finally:
        conn.close()


def add_column_if_missing(table_name: str, column_name: str, column_sql: str) -> None:
    existing = table_columns(table_name)

    if column_name in existing:
        return

    conn = connect()
    try:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")
        conn.commit()
    finally:
        conn.close()


def create_tables() -> None:
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS vehicules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT,
            immatriculation TEXT,
            marque TEXT,
            modele TEXT,
            categorie TEXT,
            service TEXT,
            energie TEXT,
            kilometrage_actuel INTEGER DEFAULT 0,
            date_mise_en_service TEXT,
            date_ct TEXT,
            assurance TEXT,
            statut TEXT DEFAULT 'Actif',
            actif INTEGER DEFAULT 1,
            photo_path TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS vehicule_kilometrages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicule_id INTEGER,
            date_releve TEXT,
            kilometrage INTEGER,
            commentaire TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vehicule_id) REFERENCES vehicules(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS vehicule_carburants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicule_id INTEGER,
            date_plein TEXT,
            kilometrage INTEGER,
            type_carburant TEXT,
            litres REAL,
            prix_litre REAL,
            montant_total REAL,
            station TEXT,
            conducteur TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vehicule_id) REFERENCES vehicules(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS vehicule_entretiens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicule_id INTEGER,
            type_entretien TEXT,
            date_entretien TEXT,
            date_prochain TEXT,
            km_entretien INTEGER,
            km_prochain INTEGER,
            fournisseur TEXT,
            montant REAL,
            statut TEXT DEFAULT 'Planifié',
            commentaire TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vehicule_id) REFERENCES vehicules(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS vehicule_attributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicule_id INTEGER,
            utilisateur TEXT,
            date_debut TEXT,
            date_fin TEXT,
            commentaire TEXT,
            actif INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vehicule_id) REFERENCES vehicules(id)
        )
        """
    )

    conn.commit()
    conn.close()


def migrate_db() -> None:
    create_tables()

    for column_name, column_sql in VEHICULE_COLUMNS.items():
        add_column_if_missing("vehicules", column_name, column_sql)

    conn = connect()
    try:
        conn.execute("UPDATE vehicules SET actif=1 WHERE actif IS NULL")
        conn.execute("UPDATE vehicules SET statut='Actif' WHERE statut IS NULL OR statut=''")
        conn.execute("UPDATE vehicules SET kilometrage_actuel=0 WHERE kilometrage_actuel IS NULL")
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    migrate_db()


def load_table(table_name: str) -> pd.DataFrame:
    init_db()

    conn = connect()
    try:
        return pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    finally:
        conn.close()


def list_tables() -> list[str]:
    conn = connect()
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        return [row["name"] for row in rows]
    finally:
        conn.close()


def list_columns(table_name: str) -> list[str]:
    conn = connect()
    try:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return [row["name"] for row in rows]
    finally:
        conn.close()
