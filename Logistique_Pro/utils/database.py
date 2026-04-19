import sqlite3
import bcrypt
from typing import Optional
from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def init_database() -> None:
    """Initialise la base de données avec TOUTES les tables et colonnes nécessaires"""
    conn = get_connection()
    cursor = conn.cursor()

    # ==================== TABLE USERS (corrigée) ====================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            first_name TEXT,           -- ← AJOUTÉ
            last_name TEXT,            -- ← AJOUTÉ
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'externe',
            categorie TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            photo_profil TEXT,
            logo_perso TEXT,
            telephone TEXT,
            theme_prefere TEXT DEFAULT 'Municipal Bleu',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            validated_at TIMESTAMP
        )
    """)

    # ==================== TABLES MANQUANTES (ajoutées) ====================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS maintenance_vehicules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicule_id INTEGER,
            date_maintenance TEXT,
            type_maintenance TEXT,
            description TEXT,
            kilometrage INTEGER,
            cout REAL,
            prochain_entretien TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evenements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titre TEXT NOT NULL,
            description TEXT,
            date_debut TEXT,
            date_fin TEXT,
            lieu TEXT,
            type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ==================== TABLES EXISTANTES (gardées telles quelles) ====================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            level TEXT DEFAULT 'info',
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            categorie TEXT,
            sous_categorie TEXT,
            quantite_stock INTEGER DEFAULT 0,
            stock_minimum INTEGER DEFAULT 5,
            prix_unitaire REAL DEFAULT 0.0,
            photo_path TEXT,
            description TEXT,
            etat_maintenance TEXT DEFAULT 'Bon',
            date_derniere_maintenance TIMESTAMP,
            fournisseur_id INTEGER,
            actif INTEGER DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS outils (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            reference TEXT,
            categorie TEXT,
            quantite_stock INTEGER DEFAULT 0,
            stock_minimum INTEGER DEFAULT 3,
            emplacement TEXT,
            etat TEXT DEFAULT 'Bon',
            photo_path TEXT,
            description TEXT,
            actif INTEGER DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fournisseurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            contact_email TEXT,
            telephone TEXT,
            adresse TEXT,
            notes TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            immatriculation TEXT UNIQUE NOT NULL,
            modele TEXT NOT NULL,
            type TEXT NOT NULL,
            capacite_kg INTEGER,
            etat TEXT DEFAULT 'Disponible',
            kilometrage INTEGER DEFAULT 0,
            photo_path TEXT,
            date_derniere_revision TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS buildings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            address TEXT,
            capacity INTEGER DEFAULT 0,
            safety_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            quantity INTEGER DEFAULT 0,
            unit TEXT DEFAULT 'pcs',
            min_threshold INTEGER DEFAULT 0,
            location TEXT,
            qr_code TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insertion du flag demo_data
    cursor.execute("""
        INSERT OR IGNORE INTO settings (key, value)
        VALUES ('demo_data_inserted', 'false')
    """)

    conn.commit()
    conn.close()

    # Mise à jour des colonnes manquantes sur une base existante
    _add_missing_columns()

    insert_demo_data()
    print("✅ Base de données initialisée avec toutes les tables et colonnes manquantes")


def _add_missing_columns():
    """Ajoute les colonnes manquantes sur une base existante (sécurité)"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN first_name TEXT")
        cursor.execute("ALTER TABLE users ADD COLUMN last_name TEXT")
    except:
        pass  # colonnes déjà présentes
    conn.commit()
    conn.close()


# ====================== Le reste du fichier reste IDENTIQUE ======================
def insert_demo_data() -> None:
    # ... (tu peux garder exactement le même code que tu avais)
    conn = get_connection()
    cursor = conn.cursor()
    flag = cursor.execute(
        "SELECT value FROM settings WHERE key = 'demo_data_inserted'"
    ).fetchone()
    if flag and flag["value"] == "true":
        conn.close()
        return

    # (le reste de ta fonction insert_demo_data reste inchangé)
    # ... [copie-colle ici tout le contenu de ta fonction insert_demo_data actuelle]

    cursor.execute("UPDATE settings SET value = 'true' WHERE key = 'demo_data_inserted'")
    conn.commit()
    conn.close()


def is_first_admin() -> bool:
    # (garde ton code tel quel)
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM users WHERE role = 'admin' AND status = 'validated'"
    ).fetchone()[0]
    conn.close()
    return count == 0


def create_user(username: str, email: str, password: str, role: str = "externe") -> bool:
    # (garde ton code tel quel)
    # ...
    pass


def authenticate_user(email: str, password: str) -> Optional[dict]:
    # (garde ton code tel quel)
    # ...
    pass
