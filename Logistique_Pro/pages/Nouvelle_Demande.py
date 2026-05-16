# pages/21_Nouvelle_Demande.py

import sqlite3
from pathlib import Path
from datetime import date

import pandas as pd
import streamlit as st
from utils.messages import send_message
from utils.emailer import send_email
from utils.numbering import next_number


BASE_DIR = Path("/opt/logistique-pro")
DEMANDES_DB = BASE_DIR / "data" / "demandes.db"
CATALOGUE_DB = BASE_DIR / "data" / "catalogue_articles.db"


def get_connection():
    DEMANDES_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DEMANDES_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS demandes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_demande TEXT,
            demandeur TEXT NOT NULL,
            email TEXT,
            telephone TEXT,
            type_demande TEXT,
            motif TEXT NOT NULL,
            date_evenement TEXT NOT NULL,
            date_debut TEXT,
            date_fin TEXT,
            heure_evenement TEXT,
            lieu TEXT,
            adresse_lieu TEXT,
            code_postal TEXT,
            ville TEXT,
            besoin_transport INTEGER DEFAULT 0,
            adresse_livraison TEXT,
            commentaire TEXT,
            articles TEXT,
            montant_estime REAL DEFAULT 0,
            gratuit INTEGER DEFAULT 0,
            statut TEXT DEFAULT 'En attente',
            commentaire_admin TEXT,
            decide_par TEXT,
            date_decision TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS demande_lignes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            demande_id INTEGER NOT NULL,
            article_id INTEGER,
            article_nom TEXT NOT NULL,
            quantite INTEGER NOT NULL,
            prix_unitaire REAL DEFAULT 0,
            total REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def ensure_column(table, column, col_type):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"PRAGMA table_info({table})")
    cols = [r["name"] for r in cur.fetchall()]

    if column not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")

    conn.commit()
    conn.close()


def ensure_schema():
    init_db()

    columns = {
        "numero_demande": "TEXT",
        "telephone": "TEXT",
        "type_demande": "TEXT",
        "date_debut": "TEXT",
        "date_fin": "TEXT",
        "heure_evenement": "TEXT",
        "adresse_lieu": "TEXT",
        "code_postal": "TEXT",
        "ville": "TEXT",
        "besoin_transport": "INTEGER DEFAULT 0",
        "adresse_livraison": "TEXT",
        "montant_estime": "REAL DEFAULT 0",
        "gratuit": "INTEGER DEFAULT 0",
    }

    for col, typ in columns.items():
        ensure_column("demandes", col, typ)


def load_catalogue(user_role):
    if not CATALOGUE_DB.exists():
        return pd.DataFrame()

    try:
        conn = sqlite3.connect(CATALOGUE_DB)

        # Associations / externes / clients / prestataires :
        # accès uniquement aux articles de sous-catégorie Événement
        if user_role in ["association", "particulier", "societe", "prestataire"]:
            query = """
                SELECT id, nom, categorie, sous_categorie, stock, unite, prix, emplacement, etat
                FROM catalogue_articles
                WHERE TRIM(COALESCE(sous_categorie, '')) = 'Événement'
                ORDER BY nom
            """
            df = pd.read_sql_query(query, conn)

        # Admin / interne / équipe interne : accès complet
        else:
            query = """
                SELECT id, nom, categorie, sous_categorie, stock, unite, prix, emplacement, etat
                FROM catalogue_articles
                ORDER BY categorie, nom
            """
            df = pd.read_sql_query(query, conn)

        conn.close()
        return df

    except Exception:
        return pd.DataFrame()



def ensure_transport_article():
    conn = sqlite3.connect(CATALOGUE_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS catalogue_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            categorie TEXT DEFAULT 'Divers',
            sous_categorie TEXT DEFAULT 'Standard',
            stock INTEGER DEFAULT 0,
            stock_min INTEGER DEFAULT 0,
            prix REAL DEFAULT 0,
            unite TEXT DEFAULT 'unité',
            emplacement TEXT,
            etat TEXT DEFAULT 'OK',
            image_path TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        )
    """)

    cur.execute("PRAGMA table_info(catalogue_articles)")
    cols = [r["name"] for r in cur.fetchall()]

    if "sous_categorie" not in cols:
        cur.execute("ALTER TABLE catalogue_articles ADD COLUMN sous_categorie TEXT DEFAULT 'Standard'")

    cur.execute("""
        SELECT id, prix
        FROM catalogue_articles
        WHERE nom = 'Transport logistique'
        LIMIT 1
    """)

    row = cur.fetchone()

    if row:
        transport_id = row["id"]
        prix = float(row["prix"] or 0)
    else:
        cur.execute("""
            INSERT INTO catalogue_articles (
                nom, categorie, sous_categorie, stock, stock_min, prix,
                unite, emplacement, etat, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "Transport logistique",
            "Divers",
            "Événement",
            9999,
            1,
            50.00,
            "forfait",
            "Service logistique",
            "OK",
            "Forfait transport automatiquement ajouté aux demandes avec transport."
        ))

        transport_id = cur.lastrowid
        prix = 50.00

    conn.commit()
    conn.close()

    return {
        "id": int(transport_id),
        "nom": "Transport logistique",
        "quantite": 1,
        "prix": prix,
        "total": prix,
    }



def save_demande(data, selected_articles):
    articles_resume = ", ".join(
        [f"{a['nom']} ({a['quantite']})" for a in selected_articles]
    )

    numero_demande = next_number("DEM")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO demandes (
            numero_demande,
            demandeur,
            email,
            telephone,
            type_demande,
            motif,
            date_evenement,
            date_debut,
            date_fin,
            heure_evenement,
            lieu,
            adresse_lieu,
            code_postal,
            ville,
            besoin_transport,
            adresse_livraison,
            commentaire,
            articles,
            montant_estime,
            gratuit,
            statut
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'En attente')
    """, (
        numero_demande,
        data["demandeur"],
        data["email"],
        data["telephone"],
        data["type_demande"],
        data["motif"],
        data["date_evenement"],
        data["date_debut"],
        data["date_fin"],
        data["heure_evenement"],
        data["lieu"],
        data["adresse_lieu"],
        data["code_postal"],
        data["ville"],
        data["besoin_transport"],
        data["adresse_livraison"],
        data["commentaire"],
        articles_resume,
        data["montant_estime"],
        data["gratuit"],
    ))

    demande_id = cur.lastrowid

    for article in selected_articles:
        cur.execute("""
            INSERT INTO demande_lignes (
                demande_id,
                article_id,
                article_nom,
                quantite,
                prix_unitaire,
                total
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            demande_id,
            article["id"],
            article["nom"],
            article["quantite"],
            article["prix"],
            article["total"],
        ))

    conn.commit()
    conn.close()

    return demande_id


def show():
    ensure_schema()

    st.title("📝 Nouvelle Demande")
    st.caption("Demande de matériel, logistique ou transport")

    user = st.session_state.get("user")

    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    role = str(user.get("role", "")).lower()

    preview_role = st.session_state.get("preview_role")
    if role == "admin" and preview_role:
        role = str(preview_role).lower()

    is_association = role == "association"
    is_external_paid = role in ["particulier", "societe", "prestataire"]

    catalogue = load_catalogue(role)

    if is_association:
        st.info("Profil association : accès uniquement aux articles sous-catégorie Événement. Facturation gratuite après validation.")

    if is_external_paid:
        st.info("Profil externe/client/prestataire : accès uniquement aux articles sous-catégorie Événement. Facturation payante.")

    demandeur_default = user.get("username") or user.get("email") or ""
    email_default = user.get("email") or ""

    with st.form("nouvelle_demande_complete"):
        st.subheader("👤 Demandeur")

        c1, c2, c3 = st.columns(3)

        with c1:
            demandeur = st.text_input("Demandeur / Association *", value=demandeur_default)

        with c2:
            email = st.text_input("Email *", value=email_default)

        with c3:
            telephone = st.text_input("Téléphone")

        st.subheader("📌 Informations événement")

        c4, c5, c6 = st.columns(3)

        with c4:
            type_demande = st.selectbox(
                "Type de demande",
                ["Matériel", "Transport", "Matériel + transport"]
            )

        with c5:
            motif = st.text_input("Motif / Nom de l'événement *")

        with c6:
            date_debut = st.date_input("Date de début", value=date.today())
            date_fin = st.date_input("Date de fin", value=date.today())

        c7, c8, c9 = st.columns(3)

        with c7:
            heure_event = st.text_input("Heure de l'événement", value="08:00")

        with c8:
            lieu = st.text_input("Lieu de l'événement *")

        with c9:
            ville = st.text_input("Ville", value="Marly")

        adresse_lieu = st.text_input("Adresse complète du lieu")
        code_postal = st.text_input("Code postal", value="59770")

        besoin_transport = type_demande in ["Transport", "Matériel + transport"]

        adresse_livraison = ""
        if besoin_transport:
            st.subheader("🚚 Transport / Livraison")
            adresse_livraison = st.text_input(
                "Adresse de livraison / retrait",
                value=adresse_lieu
            )

        st.subheader("📦 Articles demandés")

        selected_articles = []
        montant_total = 0.0

        if catalogue.empty:
            st.warning("Aucun article disponible pour votre profil.")
        else:
            nb_lignes = st.number_input(
                "Nombre d'articles différents",
                min_value=1,
                max_value=20,
                value=1,
                step=1
            )

            article_names = catalogue["nom"].tolist()

            for i in range(int(nb_lignes)):
                c_art, c_qty = st.columns([3, 1])

                with c_art:
                    article_name = st.selectbox(
                        f"Article {i + 1}",
                        article_names,
                        key=f"new_demande_article_{i}"
                    )

                row = catalogue[catalogue["nom"] == article_name].iloc[0]

                stock = int(row["stock"])
                prix = float(row["prix"]) if "prix" in row and pd.notna(row["prix"]) else 0.0

                with c_qty:
                    qty = st.number_input(
                        "Quantité",
                        min_value=1,
                        max_value=max(1, stock),
                        value=1,
                        step=1,
                        key=f"new_demande_qty_{i}"
                    )

                total_ligne = prix * int(qty)
                montant_total += total_ligne

                st.caption(
                    f"Stock disponible : {stock} {row['unite']} | "
                    f"Emplacement : {row['emplacement'] or '-'} | "
                    f"Prix : {prix:.2f} €"
                )

                selected_articles.append({
                    "id": int(row["id"]),
                    "nom": row["nom"],
                    "quantite": int(qty),
                    "prix": prix,
                    "total": total_ligne,
                })

        commentaire = st.text_area("Commentaire / informations complémentaires")

        st.subheader("🧾 Facturation")

        gratuit = 1 if is_association else 0
        montant_facture = 0.0 if gratuit else montant_total

        if is_association:
            st.success("Association : demande gratuite après validation.")
        elif is_external_paid:
            st.warning(f"Facturation externe : montant estimatif {montant_facture:.2f} €.")
        else:
            st.info(f"Montant estimatif : {montant_facture:.2f} €")

        submitted = st.form_submit_button("📨 Envoyer la demande", width="stretch")

        if submitted:
            if not demandeur.strip() or not email.strip() or not motif.strip() or not lieu.strip():
                st.error("Les champs obligatoires doivent être remplis.")
                return

            if not selected_articles and type_demande != "Transport":
                st.error("Sélectionnez au moins un article.")
                return

            if besoin_transport:
                transport_article = ensure_transport_article()

                already_transport = any(
                    a["nom"] == "Transport logistique"
                    for a in selected_articles
                )

                if not already_transport:
                    selected_articles.append(transport_article)

                if not gratuit:
                    montant_facture += transport_article["total"]

            demande_id = save_demande(
                {
                    "demandeur": demandeur.strip(),
                    "email": email.strip(),
                    "telephone": telephone.strip(),
                    "type_demande": type_demande,
                    "motif": motif.strip(),
                    "date_evenement": date_debut.strftime("%d/%m/%Y"),
                    "date_debut": date_debut.strftime("%d/%m/%Y"),
                    "date_fin": date_fin.strftime("%d/%m/%Y"),
                    "heure_evenement": heure_event.strip(),
                    "lieu": lieu.strip(),
                    "adresse_lieu": adresse_lieu.strip(),
                    "code_postal": code_postal.strip(),
                    "ville": ville.strip(),
                    "besoin_transport": 1 if besoin_transport else 0,
                    "adresse_livraison": adresse_livraison.strip(),
                    "commentaire": commentaire.strip(),
                    "montant_estime": montant_facture,
                    "gratuit": gratuit,
                },
                selected_articles,
            )

            email_subject = f"Demande #{demande_id} enregistrée - En cours de validation"
            email_body = f"""Bonjour {demandeur.strip()},

Votre demande #{demande_id} a bien été enregistrée.

Statut actuel : En cours de validation.

Événement : {motif.strip()}
Lieu : {lieu.strip()}
Date de début : {date_debut.strftime('%d/%m/%Y') if 'date_debut' in locals() else '-'}
Date de fin : {date_fin.strftime('%d/%m/%Y') if 'date_fin' in locals() else '-'}

Cordialement,
Service Logistique - Ville de Marly"""

            send_email(email.strip(), email_subject, email_body)

            send_message(
                email.strip(),
                email_subject,
                f"""Bonjour {demandeur.strip()},

Votre demande #{demande_id} a bien été enregistrée le {date_event.strftime('%d/%m/%Y') if 'date_event' in locals() else date_debut.strftime('%d/%m/%Y')}.

Statut actuel : En cours de validation.

Notre service logistique va étudier votre demande. Vous recevrez un nouveau message dès qu'elle sera validée ou refusée.

Récapitulatif :
- Événement : {motif.strip()}
- Lieu : {lieu.strip()}
- Date de début : {date_debut.strftime('%d/%m/%Y') if 'date_debut' in locals() else '-'}
- Date de fin : {date_fin.strftime('%d/%m/%Y') if 'date_fin' in locals() else '-'}

Cordialement,
Service Logistique - Ville de Marly"""
            )

            st.success(f"Demande #{demande_id} créée avec succès.")
            st.info("Votre demande est en attente de validation par un administrateur.")
            st.rerun()
