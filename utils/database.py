from __future__ import annotations

import sqlite3
from typing import Any, Optional

import bcrypt

from config import DB_PATH


# =========================================================
# CONNEXION / HELPERS SQL
# =========================================================
def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        return cur.execute(query, params).fetchall()
    finally:
        conn.close()


def fetch_one(query: str, params: tuple[Any, ...] = ()) -> Optional[sqlite3.Row]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        return cur.execute(query, params).fetchone()
    finally:
        conn.close()


def execute_query(query: str, params: tuple[Any, ...] = ()) -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
    finally:
        conn.close()


# =========================================================
# SETTINGS
# =========================================================
def get_setting(key: str, default: str = "") -> str:
    row = fetch_one("SELECT value FROM settings WHERE key = ?", (key,))
    if not row:
        return default
    return row["value"] if row["value"] is not None else default


def set_setting(key: str, value: str) -> None:
    execute_query(
        """
        INSERT INTO settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )


# =========================================================
# SÉCURITÉ
# =========================================================
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception as e:
        print("Erreur verify_password :", e)
        return False


# =========================================================
# INIT DB
# =========================================================
def _table_exists(cursor: sqlite3.Cursor, table_name: str) -> bool:
    row = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _column_exists(cursor: sqlite3.Cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table_name})")
    rows = cursor.fetchall()
    return any(row["name"] == column_name for row in rows)


def init_database() -> None:
    conn = get_connection()
    cursor = conn.cursor()

    # ==================== USERS ====================
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'particulier',
            categorie TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            photo_profil TEXT,
            logo_perso TEXT,
            telephone TEXT,
            theme_prefere TEXT DEFAULT 'Municipal Bleu',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            validated_at TIMESTAMP
        )
        """
    )

    # ==================== SETTINGS ====================
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )

    # ==================== NOTIFICATIONS ====================
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            level TEXT DEFAULT 'info',
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # ==================== ARTICLES ====================
    cursor.execute(
        """
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
        """
    )

    # ==================== OUTILS ====================
    cursor.execute(
        """
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
        """
    )

    # ==================== FOURNISSEURS ====================
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS fournisseurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            contact_email TEXT,
            telephone TEXT,
            adresse TEXT,
            notes TEXT
        )
        """
    )

    # ==================== VEHICULES ====================
    cursor.execute(
        """
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
        """
    )

    # ==================== MAINTENANCE VEHICULES ====================
    cursor.execute(
        """
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
        """
    )

    # ==================== EVENEMENTS ====================
    cursor.execute(
        """
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
        """
    )

    # ==================== BUILDINGS ====================
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS buildings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            address TEXT,
            capacity INTEGER DEFAULT 0,
            safety_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # ==================== STOCK ITEMS ====================
    cursor.execute(
        """
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
        """
    )

    # ==================== MESSAGES ====================
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            recipient_id INTEGER,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users(id),
            FOREIGN KEY (recipient_id) REFERENCES users(id)
        )
        """
    )

    # ==================== DEMANDES ====================
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS demandes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            titre TEXT NOT NULL,
            motif TEXT,
            date_evenement TEXT,
            lieu TEXT,
            statut TEXT NOT NULL DEFAULT 'En attente',
            montant_estime REAL DEFAULT 0.0,
            commentaire_admin TEXT,
            stock_applied INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )

    # ==================== DEMANDE LIGNES ====================
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS demande_lignes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            demande_id INTEGER NOT NULL,
            article_id INTEGER,
            article_nom TEXT NOT NULL,
            quantite_demandee INTEGER NOT NULL DEFAULT 1,
            prix_unitaire REAL DEFAULT 0.0,
            FOREIGN KEY (demande_id) REFERENCES demandes(id),
            FOREIGN KEY (article_id) REFERENCES articles(id)
        )
        """
    )

    # Flag de démo
    cursor.execute(
        """
        INSERT OR IGNORE INTO settings (key, value)
        VALUES ('demo_data_inserted', 'false')
        """
    )

    # Valeurs visuelles par défaut
    default_settings = {
        "site_title": "Logistique Pro - Ville de Marly",
        "site_subtitle": "Service Logistique & Événements",
        "primary_color": "#003366",
        "secondary_color": "#f8f9fa",
        "accent_color": "#ffc107",
    }
    for key, value in default_settings.items():
        cursor.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )

    conn.commit()
    conn.close()

    _add_missing_columns()
    insert_demo_data()
    print("✅ Base de données initialisée avec toutes les tables et colonnes manquantes")


def _add_missing_columns() -> None:
    conn = get_connection()
    cursor = conn.cursor()

    if _table_exists(cursor, "users"):
        missing = {
            "first_name": "TEXT",
            "last_name": "TEXT",
            "categorie": "TEXT",
            "status": "TEXT DEFAULT 'pending'",
            "photo_profil": "TEXT",
            "logo_perso": "TEXT",
            "telephone": "TEXT",
            "theme_prefere": "TEXT DEFAULT 'Municipal Bleu'",
            "validated_at": "TIMESTAMP",
        }
        for col, typ in missing.items():
            if not _column_exists(cursor, "users", col):
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {typ}")

    if _table_exists(cursor, "articles"):
        missing = {
            "sous_categorie": "TEXT",
            "photo_path": "TEXT",
            "description": "TEXT",
            "etat_maintenance": "TEXT DEFAULT 'Bon'",
            "date_derniere_maintenance": "TIMESTAMP",
            "fournisseur_id": "INTEGER",
            "actif": "INTEGER DEFAULT 1",
        }
        for col, typ in missing.items():
            if not _column_exists(cursor, "articles", col):
                cursor.execute(f"ALTER TABLE articles ADD COLUMN {col} {typ}")

    if _table_exists(cursor, "outils"):
        missing = {
            "reference": "TEXT",
            "emplacement": "TEXT",
            "etat": "TEXT DEFAULT 'Bon'",
            "photo_path": "TEXT",
            "description": "TEXT",
            "actif": "INTEGER DEFAULT 1",
        }
        for col, typ in missing.items():
            if not _column_exists(cursor, "outils", col):
                cursor.execute(f"ALTER TABLE outils ADD COLUMN {col} {typ}")

    if _table_exists(cursor, "demandes"):
        missing = {
            "commentaire_admin": "TEXT",
            "updated_at": "TIMESTAMP",
            "montant_estime": "REAL DEFAULT 0.0",
            "stock_applied": "INTEGER DEFAULT 0",
        }
        for col, typ in missing.items():
            if not _column_exists(cursor, "demandes", col):
                cursor.execute(f"ALTER TABLE demandes ADD COLUMN {col} {typ}")

    conn.commit()
    conn.close()


# =========================================================
# DONNÉES DE DÉMONSTRATION
# =========================================================
def insert_demo_data() -> None:
    conn = get_connection()
    cursor = conn.cursor()

    flag = cursor.execute(
        "SELECT value FROM settings WHERE key = 'demo_data_inserted'"
    ).fetchone()

    if flag and flag["value"] == "true":
        conn.close()
        return

    admin_email = "admin@marly.fr"
    admin_password = "ChangeMe123!"

    admin_row = cursor.execute(
        "SELECT id FROM users WHERE email = ?",
        (admin_email,),
    ).fetchone()

    if not admin_row:
        cursor.execute(
            """
            INSERT INTO users (
                username, email, password_hash, role, categorie, status, theme_prefere, validated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                "Administrateur",
                admin_email,
                hash_password(admin_password),
                "admin",
                "Administration",
                "validated",
                "Municipal Bleu",
            ),
        )
        admin_id = int(cursor.lastrowid)
    else:
        admin_id = int(admin_row["id"])

    if cursor.execute("SELECT COUNT(*) FROM fournisseurs").fetchone()[0] == 0:
        cursor.executemany(
            """
            INSERT INTO fournisseurs (nom, contact_email, telephone, adresse, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("Mobilier Events", "contact@mobilier-events.fr", "03 87 11 11 11", "Metz", "Fournisseur mobilier"),
                ("Tech Sono Grand Est", "contact@techsono.fr", "03 87 22 22 22", "Nancy", "Sonorisation et technique"),
            ],
        )

    if cursor.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 0:
        cursor.executemany(
            """
            INSERT INTO articles (
                nom, categorie, sous_categorie, quantite_stock, stock_minimum,
                prix_unitaire, description, etat_maintenance, actif
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("Chaises pliantes noires", "Mobilier", "Chaises", 245, 10, 4.50, "Chaises pliantes pour événements", "Bon", 1),
                ("Barnum 6x6m blanc", "Structures", "Barnums", 12, 2, 450.00, "Barnum extérieur blanc", "Bon", 1),
                ("Tables rectangulaires 180cm", "Mobilier", "Tables", 68, 5, 28.00, "Tables de réception", "Bon", 1),
                ("Sonorisation 2000W", "Technique", "Audio", 6, 1, 890.00, "Système audio complet", "Bon", 1),
                ("Mange-debout hautes", "Mobilier", "Tables hautes", 42, 8, 45.00, "Mange-debout pour réceptions", "Bon", 1),
            ],
        )

    if cursor.execute("SELECT COUNT(*) FROM outils").fetchone()[0] == 0:
        cursor.executemany(
            """
            INSERT INTO outils (
                nom, reference, categorie, quantite_stock, stock_minimum,
                emplacement, etat, description, actif
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("Perceuse 18V", "OUT-001", "Électroportatif", 8, 2, "Atelier", "Bon", "Perceuse sans fil 18V", 1),
                ("Câbles 50m", "OUT-002", "Électricité", 15, 5, "Entrepôt C", "Bon", "Câbles rallonge 50m", 1),
            ],
        )

    if cursor.execute("SELECT COUNT(*) FROM vehicules").fetchone()[0] == 0:
        cursor.executemany(
            """
            INSERT INTO vehicules (
                immatriculation, modele, type, capacite_kg, etat, kilometrage
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                ("AA-123-BB", "Renault Master", "Utilitaire", 1400, "Disponible", 58200),
                ("CC-456-DD", "Peugeot Boxer", "Utilitaire", 1300, "Disponible", 67450),
                ("EE-789-FF", "Citroën Jumper", "Utilitaire", 1500, "Maintenance", 91320),
            ],
        )

    if cursor.execute("SELECT COUNT(*) FROM buildings").fetchone()[0] == 0:
        cursor.executemany(
            """
            INSERT INTO buildings (name, category, address, capacity, safety_notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("Salle des Fêtes", "Salle des fêtes", "Centre-ville", 250, "Contrôle extincteurs à jour"),
                ("Gymnase Municipal", "Gymnase", "Rue du Stade", 500, "Vérifier issues de secours"),
            ],
        )

    if cursor.execute("SELECT COUNT(*) FROM stock_items").fetchone()[0] == 0:
        cursor.executemany(
            """
            INSERT INTO stock_items (
                name, category, quantity, unit, min_threshold, location, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("Barrières Vauban", "Sécurité", 30, "pcs", 10, "Entrepôt A", "État correct"),
                ("Gilets haute visibilité", "Sécurité", 18, "pcs", 5, "Atelier", "Tailles mixtes"),
                ("Projecteurs LED", "Technique", 10, "pcs", 3, "Entrepôt B", "Contrôlés en mars"),
            ],
        )

    if cursor.execute("SELECT COUNT(*) FROM evenements").fetchone()[0] == 0:
        cursor.executemany(
            """
            INSERT INTO evenements (titre, description, date_debut, date_fin, lieu, type)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                ("Fête de printemps", "Organisation logistique communale", "2026-04-25 10:00", "2026-04-25 22:00", "Parc communal", "Fête communale"),
                ("Concert Place de l'Église", "Installation technique et logistique", "2026-05-03 18:00", "2026-05-03 23:30", "Place de l'Église", "Concert"),
            ],
        )

    if cursor.execute("SELECT COUNT(*) FROM notifications").fetchone()[0] == 0:
        cursor.executemany(
            """
            INSERT INTO notifications (title, message, level, is_read)
            VALUES (?, ?, ?, ?)
            """,
            [
                ("Nouvelle demande validée", "Demande #487 - Barnum 6x6m", "info", 0),
                ("Alerte maintenance", "Véhicule EE-789-FF - Révision à planifier", "warning", 0),
                ("Stock bas", "Barrières Vauban bientôt sous le seuil minimum", "warning", 0),
            ],
        )

    if cursor.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 0:
        cursor.execute(
            """
            INSERT INTO messages (sender_id, recipient_id, subject, body, is_read)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                admin_id,
                admin_id,
                "Bienvenue dans Logistique Pro",
                "Votre espace de gestion logistique est prêt.",
                0,
            ),
        )

    if cursor.execute("SELECT COUNT(*) FROM demandes").fetchone()[0] == 0:
        cursor.execute(
            """
            INSERT INTO demandes (
                user_id, titre, motif, date_evenement, lieu, statut, montant_estime,
                commentaire_admin, stock_applied, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                admin_id,
                "Fête de printemps",
                "Besoin de matériel pour événement communal",
                "2026-04-25",
                "Parc communal",
                "Validée",
                1245.00,
                "Demande de démonstration validée.",
                0,
            ),
        )
        demande_id = int(cursor.lastrowid)

        cursor.executemany(
            """
            INSERT INTO demande_lignes (
                demande_id, article_id, article_nom, quantite_demandee, prix_unitaire
            ) VALUES (?, ?, ?, ?, ?)
            """,
            [
                (demande_id, 1, "Chaises pliantes noires", 80, 4.50),
                (demande_id, 2, "Barnum 6x6m blanc", 1, 450.00),
                (demande_id, 3, "Tables rectangulaires 180cm", 10, 28.00),
            ],
        )

    cursor.execute(
        "UPDATE settings SET value = 'true' WHERE key = 'demo_data_inserted'"
    )

    conn.commit()
    conn.close()


# =========================================================
# USERS / AUTH
# =========================================================
def is_first_admin() -> bool:
    row = fetch_one(
        "SELECT COUNT(*) AS total FROM users WHERE role = 'admin' AND status = 'validated'"
    )
    return int(row["total"]) == 0 if row else True


def create_user(username: str, email: str, password: str, role: str = "particulier") -> bool:
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

    existing_user = fetch_one("SELECT id FROM users WHERE email = ?", (email,))
    if existing_user:
        raise ValueError("Un compte existe déjà avec cette adresse email.")

    first_admin = is_first_admin()

    if first_admin:
        final_role = "admin"
        final_status = "validated"
        categorie = "Administration"
        validated_clause = "CURRENT_TIMESTAMP"
    else:
        final_role = role
        final_status = "pending"
        categorie = None
        validated_clause = "NULL"

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            INSERT INTO users (
                username, email, password_hash, role, categorie, status, theme_prefere, validated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, {validated_clause})
            """,
            (
                username,
                email,
                hash_password(password),
                final_role,
                categorie,
                final_status,
                "Municipal Bleu",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return first_admin


def authenticate_user(email: str, password: str) -> Optional[dict]:
    email = (email or "").strip().lower()
    password = password or ""

    if not email or not password:
        return None

    row = fetch_one(
        """
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
        """,
        (email,),
    )

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
    row = fetch_one(
        """
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
        """,
        (int(user_id),),
    )
    return dict(row) if row else None


def get_pending_users() -> list[sqlite3.Row]:
    return fetch_all(
        """
        SELECT id, username, email, role, categorie, created_at
        FROM users
        WHERE status = 'pending'
        ORDER BY created_at DESC
        """
    )


def validate_user(user_id: int, role: str, categorie: Optional[str] = None) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE users
            SET status = 'validated',
                role = ?,
                categorie = ?,
                validated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (role, categorie, int(user_id)),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_user(user_id: int) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id = ?", (int(user_id),))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# =========================================================
# MESSAGES
# =========================================================
def create_message(sender_id: int, recipient_id: Optional[int], subject: str, body: str) -> None:
    execute_query(
        """
        INSERT INTO messages (sender_id, recipient_id, subject, body)
        VALUES (?, ?, ?, ?)
        """,
        (
            int(sender_id),
            recipient_id if recipient_id is None else int(recipient_id),
            subject.strip(),
            body.strip(),
        ),
    )


def get_received_messages(user_id: int) -> list[sqlite3.Row]:
    return fetch_all(
        """
        SELECT
            m.id,
            m.subject,
            m.body,
            m.is_read,
            m.created_at,
            u.username AS sender_name,
            u.email AS sender_email
        FROM messages m
        JOIN users u ON u.id = m.sender_id
        WHERE m.recipient_id = ?
        ORDER BY datetime(m.created_at) DESC
        """,
        (int(user_id),),
    )


def get_sent_messages(user_id: int) -> list[sqlite3.Row]:
    return fetch_all(
        """
        SELECT
            m.id,
            m.subject,
            m.body,
            m.is_read,
            m.created_at,
            u.username AS recipient_name,
            u.email AS recipient_email
        FROM messages m
        LEFT JOIN users u ON u.id = m.recipient_id
        WHERE m.sender_id = ?
        ORDER BY datetime(m.created_at) DESC
        """,
        (int(user_id),),
    )


def mark_message_read(message_id: int, is_read: int = 1) -> None:
    execute_query(
        "UPDATE messages SET is_read = ? WHERE id = ?",
        (int(is_read), int(message_id)),
    )


def get_message_recipients_for_user(user_role: str) -> list[sqlite3.Row]:
    if user_role == "admin":
        return fetch_all(
            """
            SELECT id, username, email, role
            FROM users
            WHERE status = 'validated'
            ORDER BY username ASC
            """
        )

    return fetch_all(
        """
        SELECT id, username, email, role
        FROM users
        WHERE status = 'validated'
          AND role = 'admin'
        ORDER BY username ASC
        """
    )


# =========================================================
# DEMANDES
# =========================================================
def create_demande(
    user_id: int,
    titre: str,
    motif: str,
    date_evenement: str,
    lieu: str,
    lignes: list[dict],
) -> int:
    conn = get_connection()
    try:
        cur = conn.cursor()

        montant_estime = 0.0
        for ligne in lignes:
            quantite = int(ligne.get("quantite_demandee", 0))
            prix = float(ligne.get("prix_unitaire", 0.0))
            montant_estime += quantite * prix

        cur.execute(
            """
            INSERT INTO demandes (
                user_id, titre, motif, date_evenement, lieu, statut,
                montant_estime, commentaire_admin, stock_applied, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'En attente', ?, '', 0, CURRENT_TIMESTAMP)
            """,
            (
                int(user_id),
                titre.strip(),
                motif.strip(),
                date_evenement.strip(),
                lieu.strip(),
                montant_estime,
            ),
        )

        demande_id = int(cur.lastrowid)

        for ligne in lignes:
            cur.execute(
                """
                INSERT INTO demande_lignes (
                    demande_id, article_id, article_nom, quantite_demandee, prix_unitaire
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    demande_id,
                    ligne.get("article_id"),
                    ligne.get("article_nom", "").strip(),
                    int(ligne.get("quantite_demandee", 1)),
                    float(ligne.get("prix_unitaire", 0.0)),
                ),
            )

        conn.commit()
        return demande_id
    finally:
        conn.close()


def get_demandes_by_user(user_id: int) -> list[sqlite3.Row]:
    return fetch_all(
        """
        SELECT
            d.id,
            d.titre,
            d.motif,
            d.date_evenement,
            d.lieu,
            d.statut,
            d.montant_estime,
            d.commentaire_admin,
            d.stock_applied,
            d.created_at,
            d.updated_at
        FROM demandes d
        WHERE d.user_id = ?
        ORDER BY datetime(d.created_at) DESC
        """,
        (int(user_id),),
    )


def get_all_demandes() -> list[sqlite3.Row]:
    return fetch_all(
        """
        SELECT
            d.id,
            d.user_id,
            u.username,
            u.email,
            d.titre,
            d.motif,
            d.date_evenement,
            d.lieu,
            d.statut,
            d.montant_estime,
            d.commentaire_admin,
            d.stock_applied,
            d.created_at,
            d.updated_at
        FROM demandes d
        JOIN users u ON u.id = d.user_id
        ORDER BY datetime(d.created_at) DESC
        """
    )


def get_demande_by_id(demande_id: int) -> Optional[sqlite3.Row]:
    return fetch_one(
        """
        SELECT
            d.id,
            d.user_id,
            d.titre,
            d.motif,
            d.date_evenement,
            d.lieu,
            d.statut,
            d.montant_estime,
            d.commentaire_admin,
            d.stock_applied,
            d.created_at,
            d.updated_at
        FROM demandes d
        WHERE d.id = ?
        """,
        (int(demande_id),),
    )


def get_demande_lignes(demande_id: int) -> list[sqlite3.Row]:
    return fetch_all(
        """
        SELECT
            id,
            article_id,
            article_nom,
            quantite_demandee,
            prix_unitaire
        FROM demande_lignes
        WHERE demande_id = ?
        ORDER BY id ASC
        """,
        (int(demande_id),),
    )


def update_demande_status(demande_id: int, statut: str, commentaire_admin: str = "") -> None:
    execute_query(
        """
        UPDATE demandes
        SET statut = ?, commentaire_admin = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (statut, commentaire_admin.strip(), int(demande_id)),
    )


def can_apply_demande_stock(demande_id: int) -> bool:
    row = fetch_one(
        "SELECT stock_applied FROM demandes WHERE id = ?",
        (int(demande_id),),
    )
    if not row:
        return False
    return int(row["stock_applied"] or 0) == 0


def apply_demande_stock(demande_id: int) -> None:
    if not can_apply_demande_stock(int(demande_id)):
        return

    conn = get_connection()
    try:
        cur = conn.cursor()

        lignes = cur.execute(
            """
            SELECT article_id, quantite_demandee
            FROM demande_lignes
            WHERE demande_id = ?
              AND article_id IS NOT NULL
            """,
            (int(demande_id),),
        ).fetchall()

        for ligne in lignes:
            article_id = ligne["article_id"]
            quantite = int(ligne["quantite_demandee"] or 0)

            cur.execute(
                """
                UPDATE articles
                SET quantite_stock = CASE
                    WHEN quantite_stock - ? < 0 THEN 0
                    ELSE quantite_stock - ?
                END
                WHERE id = ?
                """,
                (quantite, quantite, int(article_id)),
            )

        cur.execute(
            """
            UPDATE demandes
            SET stock_applied = 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (int(demande_id),),
        )

        conn.commit()
    finally:
        conn.close()


# =========================================================
# ARTICLES / STATS
# =========================================================
def get_active_articles() -> list[sqlite3.Row]:
    return fetch_all(
        """
        SELECT
            id,
            nom,
            categorie,
            quantite_stock,
            stock_minimum,
            prix_unitaire
        FROM articles
        WHERE actif = 1
        ORDER BY nom ASC
        """
    )


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
        "messages",
        "demandes",
        "demande_lignes",
    }
    if table_name not in allowed_tables:
        raise ValueError("Table non autorisée.")

    row = fetch_one(f"SELECT COUNT(*) AS total FROM {table_name}")
    return int(row["total"]) if row else 0


if __name__ == "__main__":
    init_database()


# ============================================================
# PATCH - Sessions persistantes utilisateur
# ============================================================

def ensure_login_sessions_table():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS login_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT UNIQUE NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT NOT NULL,
            last_used_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def create_login_session(user_id, days=30):
    import secrets
    import hashlib
    from datetime import datetime, timedelta

    ensure_login_sessions_table()

    token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = (datetime.now() + timedelta(days=int(days))).strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO login_sessions (
            user_id, token_hash, expires_at, last_used_at
        )
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        int(user_id),
        token_hash,
        expires_at,
    ))

    conn.commit()
    conn.close()

    return token


def get_user_from_login_token(token):
    import hashlib
    from datetime import datetime

    if not token:
        return None

    ensure_login_sessions_table()

    token_hash = hashlib.sha256(str(token).encode("utf-8")).hexdigest()

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    row = cur.execute("""
        SELECT
            u.id,
            u.username,
            u.email,
            u.role,
            u.categorie,
            u.status,
            u.photo_profil,
            u.logo_perso,
            u.telephone
        FROM login_sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token_hash = ?
          AND datetime(s.expires_at) > datetime('now')
          AND COALESCE(u.status, '') = 'validated'
        LIMIT 1
    """, (token_hash,)).fetchone()

    if row:
        cur.execute("""
            UPDATE login_sessions
            SET last_used_at = CURRENT_TIMESTAMP
            WHERE token_hash = ?
        """, (token_hash,))
        conn.commit()

    conn.close()

    return dict(row) if row else None


def delete_login_session(token):
    import hashlib

    if not token:
        return

    ensure_login_sessions_table()

    token_hash = hashlib.sha256(str(token).encode("utf-8")).hexdigest()

    conn = get_connection()
    conn.execute("DELETE FROM login_sessions WHERE token_hash = ?", (token_hash,))
    conn.commit()
    conn.close()
