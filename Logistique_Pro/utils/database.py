import sqlite3
from typing import Optional, Any

import bcrypt

from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def init_database() -> None:
    """Initialise la base de données avec toutes les tables nécessaires."""
    conn = get_connection()
    cursor = conn.cursor()

    # ==================== USERS ====================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
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

    # ==================== SETTINGS ====================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # ==================== NOTIFICATIONS ====================
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

    # ==================== ARTICLES ====================
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

    # ==================== OUTILS ====================
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

    # ==================== FOURNISSEURS ====================
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

    # ==================== VEHICULES ====================
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

    # ==================== MAINTENANCE VEHICULES ====================
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

    # ==================== EVENEMENTS ====================
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

    # ==================== BUILDINGS ====================
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

    # ==================== STOCK ITEMS ====================
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

    # ==================== FLAGS INIT ====================
    cursor.execute("""
        INSERT OR IGNORE INTO settings (key, value)
        VALUES ('demo_data_inserted', 'false')
    """)

    conn.commit()
    conn.close()

    _add_missing_columns()
    insert_demo_data()


def _column_exists(cursor: sqlite3.Cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return any(col["name"] == column_name for col in columns)


def _add_missing_columns() -> None:
    """Ajoute les colonnes manquantes sur une base existante."""
    conn = get_connection()
    cursor = conn.cursor()

    user_columns = {
        "first_name": "TEXT",
        "last_name": "TEXT",
        "photo_profil": "TEXT",
        "logo_perso": "TEXT",
        "telephone": "TEXT",
        "theme_prefere": "TEXT DEFAULT 'Municipal Bleu'",
        "validated_at": "TIMESTAMP",
        "categorie": "TEXT",
        "status": "TEXT DEFAULT 'pending'",
    }

    for column_name, column_type in user_columns.items():
        if not _column_exists(cursor, "users", column_name):
            cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")

    conn.commit()
    conn.close()


def insert_demo_data() -> None:
    """Insère des données de démonstration une seule fois."""
    conn = get_connection()
    cursor = conn.cursor()

    flag = cursor.execute(
        "SELECT value FROM settings WHERE key = 'demo_data_inserted'"
    ).fetchone()

    if flag and flag["value"] == "true":
        conn.close()
        return

    # ==================== ADMIN DEMO ====================
    admin_exists = cursor.execute(
        "SELECT id FROM users WHERE email = ?",
        ("admin@marly.fr",)
    ).fetchone()

    if not admin_exists:
        cursor.execute("""
            INSERT INTO users (
                username, email, password_hash, role, categorie, status, theme_prefere, validated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            "Administrateur",
            "admin@marly.fr",
            hash_password("ChangeMe123!"),
            "admin",
            "Administration",
            "validated",
            "Municipal Bleu",
        ))

    # ==================== FOURNISSEURS DEMO ====================
    fournisseurs_count = cursor.execute("SELECT COUNT(*) FROM fournisseurs").fetchone()[0]
    if fournisseurs_count == 0:
        cursor.executemany("""
            INSERT INTO fournisseurs (nom, contact_email, telephone, adresse, notes)
            VALUES (?, ?, ?, ?, ?)
        """, [
            ("Mobilier Events", "contact@mobilier-events.fr", "03 87 11 11 11", "Metz", "Fournisseur mobilier"),
            ("Tech Sono Grand Est", "contact@techsono.fr", "03 87 22 22 22", "Nancy", "Sonorisation et technique"),
        ])

    # ==================== ARTICLES DEMO ====================
    articles_count = cursor.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    if articles_count == 0:
        cursor.executemany("""
            INSERT INTO articles (
                nom, categorie, sous_categorie, quantite_stock, stock_minimum,
                prix_unitaire, description, etat_maintenance, actif
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            ("Chaises pliantes noires", "Mobilier", "Chaises", 245, 10, 4.50, "Chaises pliantes pour événements", "Bon", 1),
            ("Barnum 6x6m blanc", "Structures", "Barnums", 12, 2, 450.00, "Barnum extérieur blanc", "Bon", 1),
            ("Tables rectangulaires 180cm", "Mobilier", "Tables", 68, 5, 28.00, "Tables de réception", "Bon", 1),
            ("Sonorisation 2000W", "Technique", "Audio", 6, 1, 890.00, "Système audio complet", "Bon", 1),
            ("Mange-debout hautes", "Mobilier", "Tables hautes", 42, 8, 45.00, "Mange-debout pour réceptions", "Bon", 1),
        ])

    # ==================== OUTILS DEMO ====================
    outils_count = cursor.execute("SELECT COUNT(*) FROM outils").fetchone()[0]
    if outils_count == 0:
        cursor.executemany("""
            INSERT INTO outils (
                nom, reference, categorie, quantite_stock, stock_minimum,
                emplacement, etat, description, actif
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            ("Perceuse 18V", "OUT-001", "Électroportatif", 8, 2, "Atelier", "Bon", "Perceuse sans fil 18V", 1),
            ("Câbles 50m", "OUT-002", "Électricité", 15, 5, "Entrepôt C", "Bon", "Câbles rallonge 50m", 1),
        ])

    # ==================== VEHICULES DEMO ====================
    vehicules_count = cursor.execute("SELECT COUNT(*) FROM vehicules").fetchone()[0]
    if vehicules_count == 0:
        cursor.executemany("""
            INSERT INTO vehicules (
                immatriculation, modele, type, capacite_kg, etat, kilometrage
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, [
            ("AA-123-BB", "Renault Master", "Utilitaire", 1400, "Disponible", 58200),
            ("CC-456-DD", "Peugeot Boxer", "Utilitaire", 1300, "Disponible", 67450),
            ("EE-789-FF", "Citroën Jumper", "Utilitaire", 1500, "Maintenance", 91320),
        ])

    # ==================== BUILDINGS DEMO ====================
    buildings_count = cursor.execute("SELECT COUNT(*) FROM buildings").fetchone()[0]
    if buildings_count == 0:
        cursor.executemany("""
            INSERT INTO buildings (name, category, address, capacity, safety_notes)
            VALUES (?, ?, ?, ?, ?)
        """, [
            ("Salle des Fêtes", "Salle des fêtes", "Centre-ville", 250, "Contrôle extincteurs à jour"),
            ("Gymnase Municipal", "Gymnase", "Rue du Stade", 500, "Vérifier issues de secours"),
        ])

    # ==================== STOCK ITEMS DEMO ====================
    stock_items_count = cursor.execute("SELECT COUNT(*) FROM stock_items").fetchone()[0]
    if stock_items_count == 0:
        cursor.executemany("""
            INSERT INTO stock_items (
                name, category, quantity, unit, min_threshold, location, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            ("Barrières Vauban", "Sécurité", 30, "pcs", 10, "Entrepôt A", "État correct"),
            ("Gilets haute visibilité", "Sécurité", 18, "pcs", 5, "Atelier", "Tailles mixtes"),
            ("Projecteurs LED", "Technique", 10, "pcs", 3, "Entrepôt B", "Contrôlés en mars"),
        ])

    # ==================== EVENEMENTS DEMO ====================
    evenements_count = cursor.execute("SELECT COUNT(*) FROM evenements").fetchone()[0]
    if evenements_count == 0:
        cursor.executemany("""
            INSERT INTO evenements (titre, description, date_debut, date_fin, lieu, type)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            ("Fête de printemps", "Organisation logistique communale", "2026-04-25 10:00", "2026-04-25 22:00", "Parc communal", "Fête communale"),
            ("Concert Place de l'Église", "Installation technique et logistique", "2026-05-03 18:00", "2026-05-03 23:30", "Place de l'Église", "Concert"),
        ])

    # ==================== NOTIFICATIONS DEMO ====================
    notifications_count = cursor.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
    if notifications_count == 0:
        cursor.executemany("""
            INSERT INTO notifications (title, message, level, is_read)
            VALUES (?, ?, ?, ?)
        """, [
            ("Nouvelle demande validée", "Demande #487 - Barnum 6x6m", "info", 0),
            ("Alerte maintenance", "Véhicule EE-789-FF - Révision à planifier", "warning", 0),
            ("Stock bas", "Barrières Vauban bientôt sous le seuil minimum", "warning", 0),
        ])

    cursor.execute(
        "UPDATE settings SET value = 'true' WHERE key = 'demo_data_inserted'"
    )

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
    """
    Crée un utilisateur.
    Retourne True si c'est le premier admin créé, sinon False.
    """
    username = (username or "").strip()
    email = (email or "").strip().lower()
    password = password or ""

    if not username:
        raise ValueError("Le nom d'utilisateur est obligatoire.")

    if not email:
        raise ValueError("L'email est obligatoire.")

    if "@" not in email or "." not in email:
        raise ValueError("Adresse email invalide.")

    if len(password) < 8:
        raise ValueError("Le mot de passe doit contenir au moins 8 caractères.")

    conn = get_connection()
    cursor = conn.cursor()

    existing_user = cursor.execute(
        "SELECT id FROM users WHERE email = ?",
        (email,)
    ).fetchone()

    if existing_user:
        conn.close()
        raise ValueError("Un compte existe déjà avec cette adresse email.")

    first_admin = is_first_admin()

    if first_admin:
        final_role = "admin"
        final_status = "validated"
        categorie = "Administration"
        validated_at_sql = "CURRENT_TIMESTAMP"
    else:
        final_role = role
        final_status = "pending"
        categorie = None
        validated_at_sql = "NULL"

    password_hash = hash_password(password)

    cursor.execute(f"""
        INSERT INTO users (
            username, email, password_hash, role, categorie, status, theme_prefere, validated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, {validated_at_sql})
    """, (
        username,
        email,
        password_hash,
        final_role,
        categorie,
        final_status,
        "Municipal Bleu",
    ))

    conn.commit()
    conn.close()

    return first_admin


def authenticate_user(email: str, password: str) -> Optional[dict]:
    email = (email or "").strip().lower()
    password = password or ""

    if not email or not password:
        return None

    conn = get_connection()
    cursor = conn.cursor()

    row = cursor.execute("""
        SELECT
            id,
            username,
            first_name,
            last_name,
            email,
            password_hash,
            role,
            categorie,
            status,
            photo_profil,
            logo_perso,
            telephone,
            theme_prefere,
            created_at,
            validated_at
        FROM users
        WHERE email = ?
    """, (email,)).fetchone()

    conn.close()

    if not row:
        return None

    if not verify_password(password, row["password_hash"]):
        return None

    return {
        "id": row["id"],
        "username": row["username"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "email": row["email"],
        "role": row["role"],
        "categorie": row["categorie"],
        "status": row["status"],
        "photo_profil": row["photo_profil"],
        "logo_perso": row["logo_perso"],
        "telephone": row["telephone"],
        "theme_prefere": row["theme_prefere"] or "Municipal Bleu",
        "created_at": row["created_at"],
        "validated_at": row["validated_at"],
    }


def get_user_by_id(user_id: int) -> Optional[dict]:
    conn = get_connection()
    cursor = conn.cursor()

    row = cursor.execute("""
        SELECT
            id,
            username,
            first_name,
            last_name,
            email,
            role,
            categorie,
            status,
            photo_profil,
            logo_perso,
            telephone,
            theme_prefere,
            created_at,
            validated_at
        FROM users
        WHERE id = ?
    """, (int(user_id),)).fetchone()

    conn.close()

    if not row:
        return None

    return dict(row)


def get_pending_users() -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, username, email, role, categorie, created_at
        FROM users
        WHERE status = 'pending'
        ORDER BY created_at DESC
    """).fetchall()
    conn.close()
    return rows


def validate_user(user_id: int, role: str, categorie: Optional[str] = None) -> bool:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET
            status = 'validated',
            role = ?,
            categorie = ?,
            validated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (role, categorie, int(user_id)))

    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated


def delete_user(user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM users WHERE id = ?", (int(user_id),))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def get_table_count(table_name: str) -> int:
    allowed_tables = {
        "users",
        "settings",
        "notifications",
        "articles",
        "outils",
        "fournisseurs",
        "vehicules",
        "maintenance_vehicules",
        "evenements",
        "buildings",
        "stock_items",
    }

    if table_name not in allowed_tables:
        raise ValueError("Table non autorisée.")

    conn = get_connection()
    cursor = conn.cursor()
    count = cursor.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    conn.close()
    return count


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    rows = cursor.execute(query, params).fetchall()
    conn.close()
    return rows


def fetch_one(query: str, params: tuple[Any, ...] = ()) -> Optional[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    row = cursor.execute(query, params).fetchone()
    conn.close()
    return row


def execute_query(query: str, params: tuple[Any, ...] = ()) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_database()
    print("✅ Base de données initialisée avec succès.")
