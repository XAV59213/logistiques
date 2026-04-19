# utils/database.py
import sqlite3
import bcrypt
from typing import Optional
from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def init_database() -> None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
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

    cursor.execute("""
        INSERT OR IGNORE INTO settings (key, value)
        VALUES ('demo_data_inserted', 'false')
    """)

    conn.commit()
    conn.close()
    insert_demo_data()


def insert_demo_data() -> None:
    conn = get_connection()
    cursor = conn.cursor()

    flag = cursor.execute(
        "SELECT value FROM settings WHERE key = 'demo_data_inserted'"
    ).fetchone()

    if flag and flag["value"] == "true":
        conn.close()
        return

    fournisseurs = [
        ("Location Event Pro", "contact@eventpro.fr", "06 12 34 56 78", "Zone industrielle Marly", "Barnums et tentes"),
        ("Matériel Festif", "info@materielfestif.fr", "03 87 65 43 21", "Metz", "Sonorisation et éclairage"),
        ("Mobilier Urbain", "commercial@mobilierurbain.fr", "06 98 76 54 32", "Nancy", "Chaises et tables"),
    ]
    cursor.executemany("""
        INSERT INTO fournisseurs (nom, contact_email, telephone, adresse, notes)
        VALUES (?, ?, ?, ?, ?)
    """, fournisseurs)

    articles = [
        ("Chaises pliantes noires", "Mobilier", "Chaises", 245, 10, 4.5, None, "Chaises empilables", "Bon", None, 1),
        ("Tables rectangulaires 180cm", "Mobilier", "Tables", 68, 5, 28.0, None, "Tables événementielles", "Bon", None, 1),
        ("Barnum 6x6m blanc", "Structures", "Barnums", 12, 2, 450.0, None, "Barnum étanche", "Bon", None, 1),
        ("Sonorisation 2000W", "Technique", "Sonorisation", 6, 1, 890.0, None, "Système complet", "Bon", None, 1),
    ]
    cursor.executemany("""
        INSERT INTO articles (
            nom, categorie, sous_categorie, quantite_stock, stock_minimum,
            prix_unitaire, photo_path, description, etat_maintenance,
            date_derniere_maintenance, fournisseur_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, articles)

    cursor.execute("SELECT COUNT(*) AS total FROM users")
    user_count = cursor.fetchone()["total"]

    if user_count == 0:
        password_hash = bcrypt.hashpw("ChangeMe123!".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        cursor.execute("""
            INSERT INTO users (
                username, email, password_hash, role, categorie, status
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "Administrateur",
            "admin@marly.fr",
            password_hash,
            "admin",
            "Administration",
            "validated",
        ))

    cursor.execute("UPDATE settings SET value = 'true' WHERE key = 'demo_data_inserted'")
    conn.commit()
    conn.close()


def is_first_admin() -> bool:
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM users WHERE role = 'admin' AND status = 'validated'"
    ).fetchone()[0]
    conn.close()
    return count == 0


def create_user(username: str, email: str, password: str, role: str = "externe") -> bool:
    conn = get_connection()
    cursor = conn.cursor()

    existing = cursor.execute(
        "SELECT id FROM users WHERE email = ?",
        (email.strip().lower(),)
    ).fetchone()

    if existing:
        conn.close()
        raise ValueError("Un compte existe déjà avec cet email.")

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    first_admin = is_first_admin()
    final_role = "admin" if first_admin else role
    final_status = "validated" if first_admin else "pending"
    final_categorie = "Administration" if first_admin else None

    cursor.execute("""
        INSERT INTO users (
            username, email, password_hash, role, categorie, status
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        username.strip(),
        email.strip().lower(),
        password_hash,
        final_role,
        final_categorie,
        final_status,
    ))

    conn.commit()
    conn.close()

    return first_admin


def authenticate_user(email: str, password: str) -> Optional[dict]:
    conn = get_connection()
    user = conn.execute("""
        SELECT id, username, email, password_hash, role, categorie, status, photo_profil, logo_perso, telephone
        FROM users
        WHERE email = ?
    """, (email.strip().lower(),)).fetchone()
    conn.close()

    if not user:
        return None

    if not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
        return None

    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
        "categorie": user["categorie"],
        "status": user["status"],
        "photo_profil": user["photo_profil"],
        "logo_perso": user["logo_perso"],
        "telephone": user["telephone"],
    }
