import sqlite3
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st
from utils.devis_tools import ensure_devis_columns, ensure_devis_number
from utils.messages import send_message
from utils.devis_workflow import ensure_devis_columns, set_devis_validated, set_devis_signed_validated
from utils.messages import send_message
from utils.emailer import send_email
from utils.activity_logger import log_activity


BASE_DIR = Path("/opt/logistique-pro")
DB_PATH = BASE_DIR / "data" / "demandes.db"
PLANNING_DB = BASE_DIR / "data" / "planning_equipes.db"
CATALOGUE_DB = BASE_DIR / "data" / "catalogue_articles.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_db():
    ensure_devis_columns()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS demandes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            demandeur TEXT NOT NULL,
            email TEXT,
            telephone TEXT,
            type_demande TEXT,
            motif TEXT NOT NULL,
            date_evenement TEXT NOT NULL,
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
            transport_valide INTEGER DEFAULT 0,
            transport_gratuit INTEGER DEFAULT 0,
            montant_transport REAL DEFAULT 0,
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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS demande_historique (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            demande_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            commentaire TEXT,
            utilisateur TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            destinataire TEXT,
            titre TEXT NOT NULL,
            message TEXT NOT NULL,
            niveau TEXT DEFAULT 'info',
            lu INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("PRAGMA table_info(demandes)")
    cols = [r["name"] for r in cur.fetchall()]

    for col, typ in {
        "telephone": "TEXT",
        "type_demande": "TEXT",
        "heure_evenement": "TEXT",
        "lieu": "TEXT",
        "adresse_lieu": "TEXT",
        "code_postal": "TEXT",
        "ville": "TEXT",
        "besoin_transport": "INTEGER DEFAULT 0",
        "adresse_livraison": "TEXT",
        "commentaire": "TEXT",
        "montant_estime": "REAL DEFAULT 0",
        "gratuit": "INTEGER DEFAULT 0",
        "transport_valide": "INTEGER DEFAULT 0",
        "transport_gratuit": "INTEGER DEFAULT 0",
        "montant_transport": "REAL DEFAULT 0",
    }.items():
        if col not in cols:
            cur.execute(f"ALTER TABLE demandes ADD COLUMN {col} {typ}")

    cur.execute("PRAGMA table_info(demande_lignes)")
    cols_l = [r["name"] for r in cur.fetchall()]

    for col, typ in {
        "prix_unitaire": "REAL DEFAULT 0",
        "total": "REAL DEFAULT 0",
    }.items():
        if col not in cols_l:
            cur.execute(f"ALTER TABLE demande_lignes ADD COLUMN {col} {typ}")

    conn.commit()
    conn.close()


def ensure_planning_db():
    conn = sqlite3.connect(PLANNING_DB)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS planning_equipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            heure TEXT NOT NULL,
            equipe TEXT NOT NULL,
            mission TEXT NOT NULL,
            lieu TEXT,
            vehicule TEXT,
            statut TEXT DEFAULT 'Planifiée',
            date_cloture TEXT,
            cloture_par TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def load_demandes(statut_filter):
    conn = get_connection()

    query = "SELECT * FROM demandes WHERE 1=1"
    params = []

    if statut_filter != "Toutes":
        query += " AND statut = ?"
        params.append(statut_filter)

    query += " ORDER BY created_at DESC"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def load_lignes(demande_id):
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT id, article_nom, quantite, prix_unitaire, total
        FROM demande_lignes
        WHERE demande_id = ?
        ORDER BY id
        """,
        conn,
        params=[int(demande_id)],
    )
    conn.close()
    return df


def add_history(demande_id, action, commentaire, utilisateur):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO demande_historique (demande_id, action, commentaire, utilisateur)
        VALUES (?, ?, ?, ?)
    """, (int(demande_id), action, commentaire, utilisateur))
    conn.commit()
    conn.close()


def create_notification(destinataire, titre, message, niveau="info"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO notifications (destinataire, titre, message, niveau)
        VALUES (?, ?, ?, ?)
    """, (destinataire, titre, message, niveau))
    conn.commit()
    conn.close()


def update_transport_line(demande_id, transport_gratuit, montant_transport):
    conn = get_connection()
    cur = conn.cursor()

    prix = 0.0 if transport_gratuit else float(montant_transport or 0)

    cur.execute("""
        SELECT id
        FROM demande_lignes
        WHERE demande_id = ?
          AND LOWER(article_nom) LIKE '%transport%'
        LIMIT 1
    """, (int(demande_id),))

    row = cur.fetchone()

    if row:
        cur.execute("""
            UPDATE demande_lignes
            SET prix_unitaire = ?, total = ?
            WHERE id = ?
        """, (prix, prix, row["id"]))
    else:
        cur.execute("""
            INSERT INTO demande_lignes (
                demande_id, article_id, article_nom, quantite, prix_unitaire, total
            )
            VALUES (?, NULL, 'Transport logistique', 1, ?, ?)
        """, (int(demande_id), prix, prix))

    conn.commit()
    conn.close()


def recalc_total(demande_id, demande_gratuite):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COALESCE(SUM(total), 0)
        FROM demande_lignes
        WHERE demande_id = ?
    """, (int(demande_id),))

    total = float(cur.fetchone()[0] or 0)

    if demande_gratuite:
        total = 0.0

    cur.execute("""
        UPDATE demandes
        SET montant_estime = ?
        WHERE id = ?
    """, (total, int(demande_id)))

    conn.commit()
    conn.close()
    return total


def add_to_planning(demande):
    conn = sqlite3.connect(PLANNING_DB)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO planning_equipes (
            date, heure, equipe, mission, lieu, vehicule, statut
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        demande.get("date_evenement", ""),
        demande.get("heure_evenement", "08:00") or "08:00",
        "Équipe Logistique",
        f"{demande.get('motif', '')} - {demande.get('demandeur', '')}",
        demande.get("lieu", "") or demande.get("adresse_lieu", "") or "À définir",
        "À définir",
        "Planifiée",
    ))

    conn.commit()
    conn.close()



def decrement_stock_after_validation(demande_id):
    """
    Décrémente automatiquement le stock du catalogue après validation.
    Ignore les lignes transport.
    """
    if not CATALOGUE_DB.exists():
        return False, "Base catalogue introuvable."

    conn_dem = get_connection()
    cur_dem = conn_dem.cursor()

    cur_dem.execute("""
        SELECT article_id, article_nom, quantite
        FROM demande_lignes
        WHERE demande_id = ?
    """, (int(demande_id),))

    lignes = cur_dem.fetchall()
    conn_dem.close()

    if not lignes:
        return True, "Aucune ligne article à décrémenter."

    conn_cat = sqlite3.connect(CATALOGUE_DB)
    conn_cat.row_factory = sqlite3.Row
    cur_cat = conn_cat.cursor()

    mouvements = []

    for ligne in lignes:
        article_id = ligne["article_id"]
        article_nom = str(ligne["article_nom"] or "")
        quantite = int(ligne["quantite"] or 0)

        if quantite <= 0:
            continue

        if "transport" in article_nom.lower():
            continue

        if article_id:
            cur_cat.execute("""
                SELECT id, nom, stock, stock_min
                FROM catalogue_articles
                WHERE id = ?
            """, (int(article_id),))
        else:
            cur_cat.execute("""
                SELECT id, nom, stock, stock_min
                FROM catalogue_articles
                WHERE nom = ?
                LIMIT 1
            """, (article_nom,))

        article = cur_cat.fetchone()

        if not article:
            mouvements.append(f"{article_nom} : article introuvable")
            continue

        stock_actuel = int(article["stock"] or 0)
        stock_min = int(article["stock_min"] or 0)
        nouveau_stock = max(0, stock_actuel - quantite)

        if nouveau_stock <= 0:
            etat = "Critique"
        elif nouveau_stock <= stock_min:
            etat = "Bas"
        else:
            etat = "OK"

        cur_cat.execute("""
            UPDATE catalogue_articles
            SET stock = ?,
                etat = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            nouveau_stock,
            etat,
            int(article["id"]),
        ))

        mouvements.append(
            f"{article['nom']} : {stock_actuel} -> {nouveau_stock} (-{quantite})"
        )

    conn_cat.commit()
    conn_cat.close()

    return True, " | ".join(mouvements) if mouvements else "Aucun stock modifié."



def check_stock_available(demande_id):
    """
    Vérifie si le stock est suffisant avant validation.
    Ignore le transport.
    """
    if not CATALOGUE_DB.exists():
        return True, []

    lignes = load_lignes(demande_id)

    if lignes.empty:
        return True, []

    conn = sqlite3.connect(CATALOGUE_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    problems = []

    for _, ligne in lignes.iterrows():
        article_nom = str(ligne.get("article_nom", ""))
        quantite = int(ligne.get("quantite", 0) or 0)
        article_id = ligne.get("article_id")

        if quantite <= 0:
            continue

        if "transport" in article_nom.lower():
            continue

        if pd.isna(article_id) or not article_id:
            cur.execute("""
                SELECT id, nom, stock
                FROM catalogue_articles
                WHERE nom = ?
                LIMIT 1
            """, (article_nom,))
        else:
            cur.execute("""
                SELECT id, nom, stock
                FROM catalogue_articles
                WHERE id = ?
            """, (int(article_id),))

        article = cur.fetchone()

        if not article:
            problems.append(f"{article_nom} : article introuvable")
            continue

        stock = int(article["stock"] or 0)

        if stock < quantite:
            problems.append(
                f"{article['nom']} : demandé {quantite}, disponible {stock}"
            )

    conn.close()

    return len(problems) == 0, problems


def show_stock_warning_before_validation(demande_id):
    ok, problems = check_stock_available(demande_id)

    if ok:
        st.success("Stock suffisant pour cette demande.")
    else:
        st.error("Stock insuffisant pour valider cette demande.")
        for p in problems:
            st.warning(p)

    return ok


def valider_devis_admin(demande, commentaire, admin_email, transport_gratuit, montant_transport):
    demande_id = int(demande["id"])
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    numero_devis = ensure_devis_number(demande_id)

    besoin_transport = float(montant_transport or 0) > 0 or bool(transport_gratuit)

    if besoin_transport:
        update_transport_line(demande_id, transport_gratuit, montant_transport)

    demande_gratuite = int(demande.get("gratuit", 0) or 0) == 1
    recalc_total(demande_id, demande_gratuite)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE demandes
        SET statut = 'Devis à signer',
            devis_valide = 1,
            devis_valide_at = ?,
            commentaire_admin = ?,
            decide_par = ?,
            date_decision = ?
        WHERE id = ?
    """, (
        now,
        commentaire,
        admin_email,
        now,
        demande_id,
    ))

    conn.commit()
    conn.close()

    add_history(
        demande_id,
        "Devis validé",
        f"Devis {numero_devis} validé. En attente du devis signé.",
        admin_email,
    )

    send_message(
        demande.get("email") or demande.get("demandeur"),
        f"Devis validé - Demande #{demande_id}",
        f"""Bonjour {demande.get('demandeur', '')},

Le devis {numero_devis} lié à votre demande #{demande_id} a été validé par l'administration.

Merci de télécharger le devis depuis votre espace "Mes Demandes", de le signer, puis de le transmettre via la plateforme sous 5 jours.

Votre facture sera disponible uniquement après validation du devis signé.

Cordialement,
Service Logistique - Ville de Marly"""
    )

    return True, "Devis validé. L'utilisateur peut maintenant télécharger et signer le devis."


def valider_devis_signe_admin(demande, admin_email):
    demande_id = int(demande["id"])
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    if not demande.get("devis_signe_path"):
        return False, "Aucun devis signé n'a été uploadé."

    stock_ok, problems = check_stock_available(demande_id)
    if not stock_ok:
        return False, "Stock insuffisant : " + " | ".join(problems)

    stock_ok2, stock_msg = decrement_stock_after_validation(demande_id)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE demandes
        SET statut = 'Validée',
            devis_signe_valide = 1,
            devis_signe_valide_at = ?,
            decide_par = ?,
            date_decision = ?
        WHERE id = ?
    """, (
        now,
        admin_email,
        now,
        demande_id,
    ))

    conn.commit()
    conn.close()

    add_history(
        demande_id,
        "Devis signé validé",
        f"Devis signé validé. Facture disponible. Stock : {stock_msg}",
        admin_email,
    )

    create_notification(
        demande.get("email") or demande.get("demandeur"),
        "Facture disponible",
        f"Votre devis signé pour la demande #{demande_id} a été validé. Votre facture est disponible.",
        "success",
    )

    send_message(
        demande.get("email") or demande.get("demandeur"),
        f"Devis signé validé - Facture disponible #{demande_id}",
        f"""Bonjour {demande.get('demandeur', '')},

Votre devis signé pour la demande #{demande_id} a été validé par nos services.

Vous pouvez maintenant télécharger votre facture dans votre espace "Mes Demandes".

Cordialement,
Service Logistique - Ville de Marly"""
    )

    add_to_planning(demande)

    return True, "Devis signé validé. La facture est maintenant disponible."

def valider_demande(demande, commentaire, admin_email, transport_gratuit, montant_transport):
    demande_id = int(demande["id"])

    if demande["statut"] != "En attente":
        return False, "Cette demande a déjà été traitée."

    stock_ok, stock_problems = check_stock_available(demande_id)
    if not stock_ok:
        return False, "Stock insuffisant : " + " | ".join(stock_problems)

    besoin_transport = float(montant_transport or 0) > 0 or bool(transport_gratuit)

    if besoin_transport:
        update_transport_line(demande_id, transport_gratuit, montant_transport)

    demande_gratuite = int(demande.get("gratuit", 0) or 0) == 1
    montant_final = recalc_total(demande_id, demande_gratuite)

    stock_ok, stock_msg = decrement_stock_after_validation(demande_id)

    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE demandes
        SET statut = 'Validée',
            commentaire_admin = ?,
            decide_par = ?,
            date_decision = ?,
            transport_valide = ?,
            transport_gratuit = ?,
            montant_transport = ?
        WHERE id = ?
    """, (
        commentaire,
        admin_email,
        now,
        1 if besoin_transport else 0,
        1 if transport_gratuit else 0,
        0.0 if transport_gratuit else float(montant_transport or 0),
        demande_id,
    ))

    conn.commit()
    conn.close()

    log_activity(
        {"email": admin_email, "role": "admin"},
        "Validation demande",
        "Validation Demandes",
        f"Demande #{demande_id} validée"
    )

    add_history(
        demande_id,
        "Validation",
        f"{commentaire} | Transport : {'gratuit' if transport_gratuit else 'payant'} | Montant final : {montant_final:.2f} € | Stock : {stock_msg}",
        admin_email,
    )

    create_notification(
        demande.get("email") or demande.get("demandeur"),
        "Demande validée",
        f"Votre demande #{demande_id} a été validée. La facture est disponible.",
        "success",
    )

    validation_subject = f"Demande #{demande_id} validée - Facture disponible"
    validation_body = f"""Bonjour {demande.get('demandeur', '')},

Votre demande #{demande_id} a été validée par le service logistique.

Vous pouvez vous connecter à votre espace "Mes Demandes" afin de télécharger votre facture ou récapitulatif PDF.

Événement : {demande.get('motif', '-')}
Date : {demande.get('date_debut') or demande.get('date_evenement', '-')}
Lieu : {demande.get('lieu', '-')}

Cordialement,
Service Logistique - Ville de Marly"""

    send_email(demande.get("email"), validation_subject, validation_body)

    send_message(
        demande.get("email") or demande.get("demandeur"),
        validation_subject,
        f"""Bonjour {demande.get('demandeur', '')},

Votre demande #{demande_id} a été validée par le service logistique le {now}.

Vous pouvez dès maintenant consulter votre espace "Mes Demandes" afin de télécharger votre facture ou récapitulatif PDF.

Informations :
- Événement : {demande.get('motif', '-')}
- Date : {demande.get('date_debut') or demande.get('date_evenement', '-')}
- Lieu : {demande.get('lieu', '-')}

Cordialement,
Service Logistique - Ville de Marly"""
    )

    add_to_planning(demande)

    return True, f"Demande validée. Transport, facture et stock mis à jour. {stock_msg}"


def refuser_demande(demande, motif_refus, admin_email):
    if not motif_refus.strip():
        return False, "Le motif du refus est obligatoire."

    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE demandes
        SET statut = 'Refusée',
            commentaire_admin = ?,
            decide_par = ?,
            date_decision = ?
        WHERE id = ?
    """, (
        motif_refus.strip(),
        admin_email,
        now,
        int(demande["id"]),
    ))

    conn.commit()
    conn.close()

    log_activity(
        {"email": admin_email, "role": "admin"},
        "Refus demande",
        "Validation Demandes",
        f"Demande #{demande['id']} refusée"
    )

    add_history(demande["id"], "Refus", motif_refus, admin_email)

    create_notification(
        demande.get("email") or demande.get("demandeur"),
        "Demande refusée",
        f"Votre demande #{demande['id']} a été refusée. Motif : {motif_refus}",
        "warning",
    )

    return True, "Demande refusée."


def load_history(demande_id):
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT action, commentaire, utilisateur, created_at
        FROM demande_historique
        WHERE demande_id = ?
        ORDER BY created_at DESC
        """,
        conn,
        params=[int(demande_id)],
    )
    conn.close()
    return df



def valider_devis_et_notifier(demande, commentaire, admin_email):
    demande_id = int(demande["id"])

    # Met à jour le transport si besoin avant devis
    besoin_transport = int(demande.get("besoin_transport", 0) or 0) == 1
    if besoin_transport:
        transport_gratuit = st.session_state.get(f"transport_mode_{demande_id}") == "Transport gratuit"
        montant_transport = st.session_state.get(f"montant_transport_{demande_id}", 0.0)
        try:
            update_transport_line(demande_id, transport_gratuit, montant_transport)
            recalc_total(demande_id, int(demande.get("gratuit", 0) or 0) == 1)
        except Exception:
            pass

    set_devis_validated(demande_id, commentaire, admin_email)

    try:
        add_history(
            demande_id,
            "Devis validé",
            commentaire or "Devis validé par l'administrateur.",
            admin_email,
        )
    except Exception:
        pass

    try:
        from utils.messages import send_message
        send_message(
            demande.get("email") or demande.get("demandeur"),
            f"Devis validé - Demande #{demande_id}",
            f"""Bonjour {demande.get('demandeur', '')},

Votre devis pour la demande #{demande_id} a été validé par l'administrateur.

Merci de télécharger le devis depuis votre espace "Mes Demandes", de le signer, puis de le transmettre via la plateforme sous 5 jours.

Une fois le devis signé contrôlé par nos services, votre facture sera disponible.

Cordialement,
Service Logistique - Ville de Marly"""
        )
    except Exception:
        pass

    return True, "Devis validé. L'utilisateur peut maintenant télécharger et signer le devis."


def valider_devis_signe_final(demande, admin_email):
    demande_id = int(demande["id"])

    if not demande.get("devis_signe_path"):
        return False, "Aucun devis signé n'a été transmis."

    set_devis_signed_validated(demande_id, admin_email)

    try:
        decrement_stock_after_validation(demande_id)
    except Exception:
        pass

    try:
        add_history(
            demande_id,
            "Devis signé validé",
            "Devis signé validé. Facture disponible.",
            admin_email,
        )
    except Exception:
        pass

    try:
        from utils.messages import send_message
        send_message(
            demande.get("email") or demande.get("demandeur"),
            f"Devis signé validé - Facture disponible #{demande_id}",
            f"""Bonjour {demande.get('demandeur', '')},

Votre devis signé pour la demande #{demande_id} a été validé.

Votre facture est maintenant disponible dans votre espace "Mes Demandes".

Cordialement,
Service Logistique - Ville de Marly"""
        )
    except Exception:
        pass

    return True, "Devis signé validé. La facture est maintenant disponible."

def show():
    ensure_db()
    ensure_planning_db()

    st.title("✅ Validation des Demandes")
    st.caption("Validation des demandes avec gestion du transport")

    user = st.session_state.get("user")

    if not user or str(user.get("role", "")).lower() != "admin":
        st.error("Accès réservé aux administrateurs.")
        st.stop()

    admin_email = user.get("email", "admin")

    col_filter, col_refresh = st.columns([3, 1])

    with col_filter:
        statut_filter = st.selectbox(
            "Filtrer les demandes",
            ["En attente", "Devis à signer", "Devis signé reçu", "Validée", "Refusée", "Toutes"],
            key="validation_statut_filter",
        )

    with col_refresh:
        if st.button("🔄 Actualiser", width="stretch"):
            st.rerun()

    df = load_demandes(statut_filter)

    if df.empty:
        st.info("Aucune demande trouvée.")
        return

    st.subheader("📋 Liste des demandes")

    cols = [
        c for c in [
            "id", "demandeur", "email", "motif", "date_evenement",
            "lieu", "articles", "statut", "montant_estime"
        ]
        if c in df.columns
    ]

    st.dataframe(df[cols], width="stretch", hide_index=True)

    selected_id = st.selectbox(
        "Sélectionner une demande",
        df["id"].tolist(),
        format_func=lambda x: f"Demande #{x}",
        key="validation_selected_demande",
    )

    demande = df[df["id"] == selected_id].iloc[0].to_dict()
    lignes = load_lignes(selected_id)

    st.divider()
    st.subheader(f"📝 Détail demande #{selected_id}")

    with st.container(border=True):
        c1, c2 = st.columns(2)

        with c1:
            st.write(f"**Demandeur :** {demande.get('demandeur', '-')}")
            st.write(f"**Email :** {demande.get('email', '-')}")
            st.write(f"**Téléphone :** {demande.get('telephone', '-')}")
            st.write(f"**Motif :** {demande.get('motif', '-')}")
            st.write(f"**Date début :** {demande.get('date_debut') or demande.get('date_evenement', '-')}")
            st.write(f"**Date fin :** {demande.get('date_fin') or demande.get('date_evenement', '-')}")
            st.write(f"**Heure :** {demande.get('heure_evenement', '')}")

        with c2:
            st.write(f"**Lieu :** {demande.get('lieu', '-')}")
            st.write(f"**Adresse :** {demande.get('adresse_lieu', '-')}")
            st.write(f"**Livraison :** {demande.get('adresse_livraison', '-')}")
            st.write(f"**Type demande :** {demande.get('type_demande', '-')}")
            st.write(f"**Transport demandé :** {'Oui' if int(demande.get('besoin_transport', 0) or 0) == 1 or 'transport' in str(demande.get('type_demande', '')).lower() else 'Non'}")
            st.write(f"**Statut :** {demande.get('statut', '-')}")

    st.subheader("📦 Articles / prestations")

    if lignes.empty:
        st.write(demande.get("articles", "-"))
    else:
        st.dataframe(lignes, width="stretch", hide_index=True)

    if demande["statut"] == "Devis signé reçu":
        st.divider()
        st.subheader("📝 Validation du devis signé")

        devis_path = demande.get("devis_signe_path")

        if devis_path:
            st.success("Un devis signé a été déposé par l'utilisateur.")
            st.write(f"Fichier : {devis_path}")

            full_path = BASE_DIR / devis_path
            if full_path.exists():
                with open(full_path, "rb") as f:
                    st.download_button(
                        "⬇️ Télécharger le devis signé",
                        data=f.read(),
                        file_name=Path(devis_path).name,
                        mime="application/octet-stream",
                        width="stretch",
                    )

        if st.button("✅ Valider le devis signé et rendre la facture disponible", type="primary", width="stretch"):
            ok, msg = valider_devis_signe_admin(demande, admin_email)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    elif demande["statut"] == "En attente":
        st.divider()
        st.subheader("⚙️ Décision administrateur")

        commentaire_validation = st.text_area(
            "Commentaire de validation",
            key=f"commentaire_validation_{selected_id}",
            placeholder="Exemple : Matériel disponible, intervention planifiée.",
        )

        st.subheader("📦 Contrôle stock")
        stock_ok_for_validation = show_stock_warning_before_validation(selected_id)

        st.subheader("🚚 Gestion du transport")

        transport_admin = st.radio(
            "Transport pour cette demande",
            ["Sans transport", "Transport payant", "Transport gratuit"],
            horizontal=True,
            index=1 if int(demande.get("besoin_transport", 0) or 0) == 1 else 0,
            key=f"transport_admin_{selected_id}",
        )

        besoin_transport = transport_admin != "Sans transport"
        transport_gratuit = transport_admin == "Transport gratuit"

        if transport_admin == "Sans transport":
            montant_transport = 0.0
            st.info("Aucun transport ne sera ajouté à la facture.")
        elif transport_gratuit:
            montant_transport = 0.0
            st.success("Le transport sera ajouté à la facture à 0,00 €.")
        else:
            montant_transport = st.number_input(
                "Montant transport HT",
                min_value=0.0,
                value=float(demande.get("montant_transport", 0) or 50.0),
                step=5.0,
                key=f"montant_transport_{selected_id}",
            )
            st.warning(f"Transport facturé : {montant_transport:.2f} € HT")

        motif_refus = st.text_area(
            "Motif de refus",
            key=f"motif_refus_{selected_id}",
            placeholder="Obligatoire en cas de refus.",
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Valider le devis", type="primary", width="stretch", disabled=not stock_ok_for_validation):
                ok, msg = valider_devis_et_notifier(
                    demande,
                    commentaire_validation.strip(),
                    admin_email,
                )

                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        with col2:
            if st.button("❌ Refuser la demande", width="stretch"):
                ok, msg = refuser_demande(
                    demande,
                    motif_refus.strip(),
                    admin_email,
                )

                if ok:
                    st.warning(msg)
                    st.rerun()
                else:
                    st.error(msg)
    elif demande["statut"] == "Devis signé reçu":
        st.divider()
        st.subheader("🖊️ Validation du devis signé")

        devis_path = demande.get("devis_signe_path")

        if devis_path:
            st.success("Un devis signé a été transmis par l'utilisateur.")
            full_path = BASE_DIR / devis_path
            if full_path.exists():
                with open(full_path, "rb") as f:
                    st.download_button(
                        "⬇️ Télécharger le devis signé",
                        data=f.read(),
                        file_name=Path(devis_path).name,
                        mime="application/octet-stream",
                        width="stretch",
                    )
        else:
            st.warning("Aucun devis signé transmis.")

        if st.button("✅ Valider le devis signé et rendre la facture disponible", type="primary", width="stretch"):
            ok, msg = valider_devis_signe_final(demande, admin_email)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    else:
        st.info("Cette demande a déjà été traitée.")

    st.divider()
    st.subheader("🧾 Historique")

    hist = load_history(selected_id)

    if hist.empty:
        st.info("Aucun historique.")
    else:
        st.dataframe(hist, width="stretch", hide_index=True)
