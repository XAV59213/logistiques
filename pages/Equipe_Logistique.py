# pages/Equipe_Logistique.py

import sqlite3
import uuid
from pathlib import Path
from datetime import datetime, date
from io import BytesIO

import pandas as pd
import streamlit as st
from utils.activity_logger import log_activity

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


BASE_DIR = Path("/opt/logistique-pro")
DEMANDES_DB = BASE_DIR / "data" / "demandes.db"
CATALOGUE_DB = BASE_DIR / "data" / "catalogue_articles.db"
LIVRAISON_PHOTOS_DIR = BASE_DIR / "assets/photos/livraisons"
RETOUR_PHOTOS_DIR = BASE_DIR / "assets/photos/retours"
LIVRAISON_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
RETOUR_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)


def connect_demandes():
    conn = sqlite3.connect(DEMANDES_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def connect_catalogue():
    conn = sqlite3.connect(CATALOGUE_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_columns():
    conn = connect_demandes()
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(demandes)")
    cols = [r["name"] for r in cur.fetchall()]

    needed = {
        "livraison_statut": "TEXT DEFAULT 'À livrer'",
        "livraison_date": "TEXT",
        "livraison_par": "TEXT",
        "livraison_commentaire": "TEXT",
        "retour_statut": "TEXT DEFAULT 'En attente retour'",
        "retour_date": "TEXT",
        "retour_par": "TEXT",
        "retour_commentaire": "TEXT",
        "retour_stock_reintegre": "INTEGER DEFAULT 0",
        "materiel_manquant": "TEXT",
        "materiel_casse": "TEXT",
        "cloture_statut": "TEXT DEFAULT 'Ouverte'",
        "cloture_date": "TEXT",
        "cloture_par": "TEXT",
        "cloture_commentaire": "TEXT",
        "signature_livraison": "TEXT",
        "photo_livraison": "TEXT",
        "signature_retour": "TEXT",
        "photo_retour": "TEXT",
    }

    for col, typ in needed.items():
        if col not in cols:
            cur.execute(f"ALTER TABLE demandes ADD COLUMN {col} {typ}")

    conn.commit()
    conn.close()


def load_stock_evenement():
    if not CATALOGUE_DB.exists():
        return pd.DataFrame()

    conn = connect_catalogue()

    df = pd.read_sql_query("""
        SELECT id, nom, categorie, sous_categorie, stock, stock_min, prix_location,
               unite, emplacement, etat
        FROM catalogue_articles
        WHERE TRIM(COALESCE(sous_categorie, '')) = 'Événement'
        ORDER BY categorie, nom
    """, conn)

    conn.close()

    if df.empty:
        return df

    reserves = get_stock_reserve()

    df["reserve"] = df["id"].map(reserves).fillna(0).astype(int)
    df["disponible"] = df["stock"].astype(int) - df["reserve"].astype(int)
    df["disponible"] = df["disponible"].apply(lambda x: max(0, x))

    return df


def get_stock_reserve():
    if not DEMANDES_DB.exists():
        return {}

    conn = connect_demandes()
    cur = conn.cursor()

    cur.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name='demande_lignes'
    """)
    if cur.fetchone() is None:
        conn.close()
        return {}

    query = """
        SELECT 
            dl.article_id,
            SUM(dl.quantite) AS reserve
        FROM demande_lignes dl
        INNER JOIN demandes d ON d.id = dl.demande_id
        WHERE d.statut = 'Validée'
          AND COALESCE(d.retour_stock_reintegre, 0) = 0
          AND dl.article_id IS NOT NULL
          AND LOWER(COALESCE(dl.article_nom, '')) NOT LIKE '%transport%'
        GROUP BY dl.article_id
    """

    rows = cur.execute(query).fetchall()
    conn.close()

    return {
        int(row["article_id"]): int(row["reserve"] or 0)
        for row in rows
        if row["article_id"] is not None
    }


def load_evenements_valides():
    if not DEMANDES_DB.exists():
        return pd.DataFrame()

    conn = connect_demandes()

    df = pd.read_sql_query("""
        SELECT *
        FROM demandes
        WHERE statut = 'Validée'
        ORDER BY COALESCE(date_debut, date_evenement), heure_evenement, id
    """, conn)

    conn.close()
    return df


def load_lignes(demande_id):
    conn = connect_demandes()

    df = pd.read_sql_query("""
        SELECT id, article_id, article_nom, quantite, prix_unitaire, total
        FROM demande_lignes
        WHERE demande_id = ?
        ORDER BY id
    """, conn, params=[int(demande_id)])

    conn.close()
    return df


def add_history(demande_id, action, commentaire, utilisateur):
    conn = connect_demandes()
    cur = conn.cursor()

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
        INSERT INTO demande_historique (demande_id, action, commentaire, utilisateur)
        VALUES (?, ?, ?, ?)
    """, (
        int(demande_id),
        action,
        commentaire,
        utilisateur,
    ))

    conn.commit()
    conn.close()


def create_notification(destinataire, titre, message, niveau="info"):
    conn = connect_demandes()
    cur = conn.cursor()

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

    cur.execute("""
        INSERT INTO notifications (destinataire, titre, message, niveau)
        VALUES (?, ?, ?, ?)
    """, (
        destinataire,
        titre,
        message,
        niveau,
    ))

    conn.commit()
    conn.close()



def save_livraison_photo(file):
    if file is None:
        return ""

    ext = Path(file.name).suffix.lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        return ""

    filename = f"livraison_{uuid.uuid4().hex}{ext}"
    path = LIVRAISON_PHOTOS_DIR / filename

    with open(path, "wb") as f:
        f.write(file.getbuffer())

    return str(path.relative_to(BASE_DIR))



def valider_livraison(demande, agent, commentaire, signature, photo_livraison):
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    conn = connect_demandes()
    cur = conn.cursor()

    cur.execute("""
        UPDATE demandes
        SET livraison_statut = 'Livrée',
            livraison_date = ?,
            livraison_par = ?,
            livraison_commentaire = ?,
            signature_livraison = ?,
            photo_livraison = ?
        WHERE id = ?
    """, (
        now,
        agent,
        commentaire,
        signature,
        photo_livraison,
        int(demande["id"]),
    ))

    conn.commit()
    conn.close()

    log_activity(
        {"email": agent, "role": "equipe_interne"},
        "Livraison validée",
        "Équipe Logistique",
        f"Demande #{demande['id']} livrée"
    )

    add_history(
        demande["id"],
        "Livraison validée",
        commentaire or "Livraison validée par l'équipe logistique.",
        agent,
    )

    create_notification(
        demande.get("email") or demande.get("demandeur"),
        "Livraison validée",
        f"La livraison de votre demande #{demande['id']} a été validée.",
        "success",
    )


def reintegrer_stock_retour(demande_id):
    lignes = load_lignes(demande_id)

    if lignes.empty or not CATALOGUE_DB.exists():
        return "Aucun article à réintégrer."

    conn = connect_catalogue()
    cur = conn.cursor()

    mouvements = []

    for _, ligne in lignes.iterrows():
        article_nom = str(ligne.get("article_nom", ""))
        article_id = ligne.get("article_id")
        quantite = int(ligne.get("quantite", 0) or 0)

        if quantite <= 0:
            continue

        if "transport" in article_nom.lower():
            continue

        if pd.notna(article_id) and article_id:
            cur.execute("""
                SELECT id, nom, stock, stock_min
                FROM catalogue_articles
                WHERE id = ?
            """, (int(article_id),))
        else:
            cur.execute("""
                SELECT id, nom, stock, stock_min
                FROM catalogue_articles
                WHERE nom = ?
                LIMIT 1
            """, (article_nom,))

        article = cur.fetchone()

        if not article:
            mouvements.append(f"{article_nom} introuvable")
            continue

        stock_actuel = int(article["stock"] or 0)
        stock_min = int(article["stock_min"] or 0)
        nouveau_stock = stock_actuel + quantite

        if nouveau_stock <= 0:
            etat = "Critique"
        elif nouveau_stock <= stock_min:
            etat = "Bas"
        else:
            etat = "OK"

        cur.execute("""
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

        mouvements.append(f"{article['nom']} : {stock_actuel} -> {nouveau_stock} (+{quantite})")

    conn.commit()
    conn.close()

    return " | ".join(mouvements) if mouvements else "Aucun stock modifié."



def save_retour_photo(file):
    if file is None:
        return ""

    ext = Path(file.name).suffix.lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        return ""

    filename = f"retour_{uuid.uuid4().hex}{ext}"
    path = RETOUR_PHOTOS_DIR / filename

    with open(path, "wb") as f:
        f.write(file.getbuffer())

    return str(path.relative_to(BASE_DIR))



def valider_retour(demande, agent, commentaire, materiel_manquant, materiel_casse, signature, photo_retour):
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    deja_reintegre = int(demande.get("retour_stock_reintegre", 0) or 0) == 1

    if deja_reintegre:
        stock_msg = "Stock déjà réintégré précédemment."
    else:
        stock_msg = reintegrer_stock_retour(demande["id"])

    conn = connect_demandes()
    cur = conn.cursor()

    cur.execute("""
        UPDATE demandes
        SET retour_statut = 'Retournée',
            retour_date = ?,
            retour_par = ?,
            retour_commentaire = ?,
            retour_stock_reintegre = 1,
            materiel_manquant = ?,
            materiel_casse = ?,
            signature_retour = ?,
            photo_retour = ?
        WHERE id = ?
    """, (
        now,
        agent,
        commentaire,
        materiel_manquant,
        materiel_casse,
        signature,
        photo_retour,
        int(demande["id"]),
    ))

    conn.commit()
    conn.close()

    log_activity(
        {"email": agent, "role": "equipe_interne"},
        "Retour validé",
        "Équipe Logistique",
        f"Demande #{demande['id']} retournée"
    )

    add_history(
        demande["id"],
        "Retour validé",
        f"{commentaire} | Manquant : {materiel_manquant or '-'} | Cassé : {materiel_casse or '-'} | Stock : {stock_msg}",
        agent,
    )

    create_notification(
        demande.get("email") or demande.get("demandeur"),
        "Retour matériel validé",
        f"Le retour matériel de votre demande #{demande['id']} a été validé.",
        "success",
    )

    return stock_msg


def show_saved_photo(photo_value, caption):
    if photo_value is None:
        return

    photo_value = str(photo_value).strip()

    if not photo_value or photo_value.lower() in ["nan", "none", "null"]:
        return

    path = BASE_DIR / photo_value

    if path.exists():
        st.image(str(path), caption=caption, width=250)



def cloturer_demande(demande, agent, commentaire):
    demande_id = int(demande["id"])
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    conn = connect_demandes()
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(demandes)")
    cols = [r["name"] for r in cur.fetchall()]

    needed = {
        "cloture_statut": "TEXT DEFAULT 'Ouverte'",
        "cloture_date": "TEXT",
        "cloture_par": "TEXT",
        "cloture_commentaire": "TEXT",
    }

    for col, typ in needed.items():
        if col not in cols:
            cur.execute(f"ALTER TABLE demandes ADD COLUMN {col} {typ}")

    cur.execute("""
        UPDATE demandes
        SET cloture_statut = 'Clôturée',
            cloture_date = ?,
            cloture_par = ?,
            cloture_commentaire = ?
        WHERE id = ?
    """, (
        now,
        agent,
        commentaire or "Demande clôturée par l'administrateur.",
        demande_id,
    ))

    conn.commit()
    conn.close()

    add_history(
        demande_id,
        "Demande clôturée",
        commentaire or "Demande clôturée par l'administrateur.",
        agent,
    )

    return True, "Demande clôturée avec succès."


def badge(text):
    colors = {
        "À livrer": "#f59e0b",
        "Livrée": "#16a34a",
        "En attente retour": "#f59e0b",
        "Retournée": "#16a34a",
        "OK": "#16a34a",
        "Bas": "#f59e0b",
        "Critique": "#dc2626",
    }
    color = colors.get(str(text), "#64748b")
    return f"<span style='background:{color};color:white;padding:4px 10px;border-radius:999px'>{text}</span>"



def preparation_pdf(demande, lignes):
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.2 * cm,
        leftMargin=1.2 * cm,
        topMargin=1.0 * cm,
        bottomMargin=1.0 * cm,
    )

    styles = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, leading=10)

    elements = []

    logo_paths = [
        BASE_DIR / "assets/logo/logo.png",
        BASE_DIR / "assets/logo_mairie.png",
        BASE_DIR / "assets/photos/default/mairie.png",
    ]

    logo = None
    for lp in logo_paths:
        if lp.exists():
            logo = lp
            break

    title = Paragraph(
        f"""
        <b>BON DE PRÉPARATION ÉQUIPE</b><br/>
        Demande n° {demande.get('id')}<br/>
        Édité le {datetime.now().strftime('%d/%m/%Y %H:%M')}
        """,
        styles["Heading2"],
    )

    if logo:
        header = Table(
            [[Image(str(logo), width=2.8 * cm, height=2.8 * cm), title]],
            colWidths=[3.2 * cm, 14 * cm],
        )
    else:
        header = Table([[Paragraph("<b>Ville de Marly</b>", styles["Heading2"]), title]], colWidths=[5 * cm, 12 * cm])

    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    elements.append(header)

    infos = [
        ["Demandeur", str(demande.get("demandeur", "-"))],
        ["Email", str(demande.get("email", "-"))],
        ["Téléphone", str(demande.get("telephone", "-"))],
        ["Événement", str(demande.get("motif", "-"))],
        ["Date début", str(demande.get("date_debut") or demande.get("date_evenement") or "-")],
        ["Date fin", str(demande.get("date_fin") or demande.get("date_evenement") or "-")],
        ["Heure", str(demande.get("heure_evenement", "-"))],
        ["Lieu", str(demande.get("lieu", "-"))],
        ["Adresse livraison", str(demande.get("adresse_livraison") or demande.get("adresse_lieu") or "-")],
        ["Transport", "Oui" if int(demande.get("besoin_transport", 0) or 0) == 1 else "Non"],
        ["Statut livraison", str(demande.get("livraison_statut") or "À livrer")],
        ["Statut retour", str(demande.get("retour_statut") or "En attente retour")],
    ]

    info_table = Table(infos, colWidths=[4 * cm, 13.2 * cm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#003366")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    elements.append(info_table)
    elements.append(Spacer(1, 0.5 * cm))

    elements.append(Paragraph("<b>Matériel à préparer</b>", styles["Heading2"]))

    data = [["Article", "Quantité", "À préparer", "Retour OK", "Observation"]]

    if lignes.empty:
        data.append([str(demande.get("articles", "-")), "-", "☐", "☐", ""])
    else:
        for _, row in lignes.iterrows():
            data.append([
                str(row.get("article_nom", "-")),
                str(row.get("quantite", "-")),
                "☐",
                "☐",
                "",
            ])

    table = Table(data, colWidths=[7.0 * cm, 2.0 * cm, 2.5 * cm, 2.5 * cm, 3.2 * cm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#00A651")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 0.7 * cm))

    sign_data = [
        ["Préparé par", "Date", "Signature"],
        ["", "", ""],
        ["Livré par", "Date", "Signature"],
        ["", "", ""],
        ["Retour contrôlé par", "Date", "Signature"],
        ["", "", ""],
    ]

    sign_table = Table(sign_data, colWidths=[6 * cm, 4 * cm, 7.2 * cm], rowHeights=[0.7 * cm, 1.2 * cm, 0.7 * cm, 1.2 * cm, 0.7 * cm, 1.2 * cm])
    sign_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#f1f5f9")),
        ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
        ("FONTNAME", (0, 4), (-1, 4), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))

    elements.append(Paragraph("<b>Signatures</b>", styles["Heading2"]))
    elements.append(sign_table)

    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph("© 2026 Ville de Marly - Logistique Pro", small))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()



def show_stock_evenement():
    st.subheader("📦 Stock Événement")

    df = load_stock_evenement()

    if df.empty:
        st.info("Aucun article événement disponible.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Articles événement", len(df))
    c2.metric("Stock réservé", int(df["reserve"].sum()))
    c3.metric("Stock disponible", int(df["disponible"].sum()))
    c4.metric("Critique", int((df["etat"] == "Critique").sum()))

    df_display = df.rename(columns={
        "nom": "Article",
        "categorie": "Catégorie",
        "sous_categorie": "Sous-catégorie",
        "stock": "Stock réel",
        "reserve": "Réservé",
        "disponible": "Disponible",
        "stock_min": "Stock min",
        "prix_location": "Prix location",
        "unite": "Unité",
        "emplacement": "Emplacement",
        "etat": "État",
    })

    cols = [
        "Article", "Catégorie", "Stock réel", "Réservé", "Disponible",
        "Stock min", "Unité", "Emplacement", "État"
    ]

    st.dataframe(df_display[cols], width="stretch", hide_index=True)


def show_evenements():
    st.subheader("📅 Événements à venir")

    df = load_evenements_valides()

    if df.empty:
        st.info("Aucun événement validé à venir.")
        return

    cols = [
        c for c in [
            "id", "demandeur", "motif", "date_debut", "date_fin",
            "date_evenement", "heure_evenement", "lieu", "adresse_livraison",
            "livraison_statut", "retour_statut"
        ]
        if c in df.columns
    ]

    st.dataframe(df[cols], width="stretch", hide_index=True)


def show_livraisons_retours(agent):
    st.subheader("🚚 Livraisons et retours")

    df = load_evenements_valides()

    if df.empty:
        st.info("Aucune demande validée.")
        return

    selected_id = st.selectbox(
        "Sélectionner une demande validée",
        df["id"].tolist(),
        format_func=lambda x: f"Demande #{x}",
        key="equipe_select_demande",
    )

    demande = df[df["id"] == selected_id].iloc[0].to_dict()
    lignes = load_lignes(selected_id)

    with st.container(border=True):
        st.markdown(f"### Demande #{selected_id} - {demande.get('motif', '-')}")
        c1, c2 = st.columns(2)

        with c1:
            st.write(f"**Demandeur :** {demande.get('demandeur', '-')}")
            st.write(f"**Email :** {demande.get('email', '-')}")
            st.write(f"**Téléphone :** {demande.get('telephone', '-')}")
            st.write(f"**Date début :** {demande.get('date_debut') or demande.get('date_evenement', '-')}")
            st.write(f"**Date fin :** {demande.get('date_fin') or demande.get('date_evenement', '-')}")

        with c2:
            st.write(f"**Lieu :** {demande.get('lieu', '-')}")
            st.write(f"**Adresse livraison :** {demande.get('adresse_livraison', '-')}")
            st.markdown(f"**Livraison :** {badge(demande.get('livraison_statut') or 'À livrer')}", unsafe_allow_html=True)
            st.markdown(f"**Retour :** {badge(demande.get('retour_statut') or 'En attente retour')}", unsafe_allow_html=True)
            cloture_affichage = demande.get("cloture_statut") or ("Clôturée" if demande.get("statut") == "Clôturée" else "Ouverte")
            st.markdown(f"**Clôture :** {badge(cloture_affichage)}", unsafe_allow_html=True)

    st.subheader("📦 Matériel prévu")

    if lignes.empty:
        st.write(demande.get("articles", "-"))
    else:
        st.dataframe(lignes, width="stretch", hide_index=True)

    st.download_button(
        "⬇️ Télécharger le bon de préparation PDF",
        data=preparation_pdf(demande, lignes),
        file_name=f"bon_preparation_demande_{selected_id}.pdf",
        mime="application/pdf",
        width="stretch",
        key=f"download_bon_prepa_{selected_id}",
    )

    st.divider()

    col_liv, col_ret = st.columns(2)

    with col_liv:
        st.subheader("✅ Valider la livraison")

        liv_comment = st.text_area(
            "Observation livraison",
            key=f"liv_comment_{selected_id}",
            placeholder="Exemple : matériel livré complet, RAS.",
        )

        photo_livraison_file = st.file_uploader(
            "Photo livraison",
            type=["png", "jpg", "jpeg", "webp"],
            key=f"photo_livraison_{selected_id}",
        )

        signature_livraison = st.text_input(
            "Nom du signataire livraison",
            value=agent,
            key=f"signature_livraison_{selected_id}",
        )

        confirm_livraison = st.checkbox(
            "Je confirme que la livraison est effectuée",
            key=f"confirm_livraison_{selected_id}",
        )

        already_livree = demande.get("livraison_statut") == "Livrée"

        if st.button(
            "✅ Confirmer livraison",
            disabled=already_livree or not confirm_livraison or not signature_livraison.strip(),
            width="stretch",
            key=f"btn_livraison_{selected_id}",
        ):
            photo_livraison_path = save_livraison_photo(photo_livraison_file)
            valider_livraison(demande, agent, liv_comment.strip(), signature_livraison.strip(), photo_livraison_path)
            st.success("Livraison validée.")
            st.rerun()

        if already_livree:
            st.success(f"Livrée le {demande.get('livraison_date', '-')} par {demande.get('livraison_par', '-')}")
            show_saved_photo(demande.get("photo_livraison"), "Photo livraison")

    with col_ret:
        st.subheader("↩️ Valider le retour")

        ret_comment = st.text_area(
            "Observation retour",
            key=f"ret_comment_{selected_id}",
            placeholder="Exemple : matériel récupéré complet.",
        )

        materiel_manquant = st.text_area(
            "Matériel manquant",
            key=f"manquant_{selected_id}",
            placeholder="Laisser vide si aucun.",
        )

        materiel_casse = st.text_area(
            "Matériel cassé / abîmé",
            key=f"casse_{selected_id}",
            placeholder="Laisser vide si aucun.",
        )

        photo_file = st.file_uploader(
            "Photo retour / matériel cassé",
            type=["png", "jpg", "jpeg", "webp"],
            key=f"photo_retour_{selected_id}",
        )

        signature_retour = st.text_input(
            "Nom du signataire retour",
            value=agent,
            key=f"signature_retour_{selected_id}",
        )

        confirm_retour = st.checkbox(
            "Je confirme que le retour est contrôlé",
            key=f"confirm_retour_{selected_id}",
        )

        already_retour = demande.get("retour_statut") == "Retournée"

        if st.button(
            "↩️ Confirmer retour et réintégrer stock",
            disabled=already_retour or not confirm_retour or not signature_retour.strip(),
            width="stretch",
            key=f"btn_retour_{selected_id}",
        ):
            photo_path = save_retour_photo(photo_file)

            stock_msg = valider_retour(
                demande,
                agent,
                ret_comment.strip(),
                materiel_manquant.strip(),
                materiel_casse.strip(),
                signature_retour.strip(),
                photo_path,
            )
            st.success(f"Retour validé. {stock_msg}")
            st.rerun()

        if already_retour:
            st.success(f"Retournée le {demande.get('retour_date', '-')} par {demande.get('retour_par', '-')}")
            show_saved_photo(demande.get("photo_retour"), "Photo retour")

    show_admin_cloture_block(demande, agent, selected_id)



def show_admin_cloture_block(demande, agent, selected_id):
    current_user = st.session_state.get("user") or {}
    current_role = str(current_user.get("role", "")).lower()

    preview_role = st.session_state.get("preview_role")
    if current_role == "admin" and preview_role:
        current_role = str(preview_role).lower()

    if current_role != "admin":
        return

    st.divider()
    st.subheader("🔒 Clôture finale administrateur")

    already_retour = demande.get("retour_statut") == "Retournée"
    already_closed = demande.get("cloture_statut") == "Clôturée"

    if already_closed:
        st.success(f"Clôturée le {demande.get('cloture_date', '-')} par {demande.get('cloture_par', '-')}")
        return

    if not already_retour:
        st.warning("La demande doit être retournée avant clôture.")
        return

    cloture_comment = st.text_area(
        "Commentaire de clôture",
        key=f"admin_cloture_comment_{selected_id}",
        placeholder="Exemple : dossier complet, matériel réintégré, RAS.",
    )

    confirm_cloture = st.checkbox(
        "Je confirme la clôture définitive de cette demande",
        key=f"admin_confirm_cloture_{selected_id}",
    )

    if st.button(
        "🔒 Clôturer définitivement",
        disabled=not confirm_cloture,
        width="stretch",
        key=f"admin_btn_cloture_{selected_id}",
    ):
        ok, msg = cloturer_demande(demande, agent, cloture_comment.strip())
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)


def show_livraisons_only(agent):
    st.subheader("🚚 Livraisons à effectuer")

    df = load_evenements_valides()

    if df.empty:
        st.info("Aucune livraison à afficher.")
        return

    df = df[df["livraison_statut"].fillna("À livrer") != "Livrée"]

    if df.empty:
        st.success("Aucune livraison en attente.")
        return

    selected_id = st.selectbox(
        "Sélectionner une livraison",
        df["id"].tolist(),
        format_func=lambda x: f"Demande #{x}",
        key="select_livraison_only",
    )

    demande = df[df["id"] == selected_id].iloc[0].to_dict()
    lignes = load_lignes(selected_id)

    with st.container(border=True):
        st.markdown(f"### Demande #{selected_id} - {demande.get('motif', '-')}")
        st.write(f"**Demandeur :** {demande.get('demandeur', '-')}")
        st.write(f"**Email :** {demande.get('email', '-')}")
        st.write(f"**Téléphone :** {demande.get('telephone', '-')}")
        st.write(f"**Lieu :** {demande.get('lieu', '-')}")
        st.write(f"**Adresse livraison :** {demande.get('adresse_livraison', '-')}")
        st.markdown(f"**Livraison :** {badge(demande.get('livraison_statut') or 'À livrer')}", unsafe_allow_html=True)

    st.subheader("📦 Matériel à livrer")
    if lignes.empty:
        st.write(demande.get("articles", "-"))
    else:
        st.dataframe(lignes, width="stretch", hide_index=True)

    liv_comment = st.text_area(
        "Observation livraison",
        key=f"liv_only_comment_{selected_id}",
        placeholder="Exemple : matériel livré complet, RAS.",
    )

    photo_livraison_file = st.file_uploader(
        "Photo livraison",
        type=["png", "jpg", "jpeg", "webp"],
        key=f"liv_only_photo_{selected_id}",
    )

    signature_livraison = st.text_input(
        "Nom du signataire livraison",
        value=agent,
        key=f"liv_only_signature_{selected_id}",
    )

    confirm_livraison = st.checkbox(
        "Je confirme que la livraison est effectuée",
        key=f"liv_only_confirm_{selected_id}",
    )

    if st.button(
        "✅ Confirmer livraison",
        disabled=not confirm_livraison or not signature_livraison.strip(),
        width="stretch",
        key=f"liv_only_btn_{selected_id}",
    ):
        photo_livraison_path = save_livraison_photo(photo_livraison_file)
        valider_livraison(
            demande,
            agent,
            liv_comment.strip(),
            signature_livraison.strip(),
            photo_livraison_path,
        )
        st.success("Livraison validée.")
        st.rerun()


def show_retours_only(agent):
    st.subheader("↩️ Retours à contrôler")

    df = load_evenements_valides()

    if df.empty:
        st.info("Aucun retour à afficher.")
        return

    df = df[
        (df["livraison_statut"].fillna("") == "Livrée") &
        (df["retour_statut"].fillna("En attente retour") != "Retournée")
    ]

    if df.empty:
        st.success("Aucun retour en attente.")
        return

    selected_id = st.selectbox(
        "Sélectionner un retour",
        df["id"].tolist(),
        format_func=lambda x: f"Demande #{x}",
        key="select_retour_only",
    )

    demande = df[df["id"] == selected_id].iloc[0].to_dict()
    lignes = load_lignes(selected_id)

    with st.container(border=True):
        st.markdown(f"### Demande #{selected_id} - {demande.get('motif', '-')}")
        st.write(f"**Demandeur :** {demande.get('demandeur', '-')}")
        st.write(f"**Email :** {demande.get('email', '-')}")
        st.write(f"**Téléphone :** {demande.get('telephone', '-')}")
        st.write(f"**Lieu :** {demande.get('lieu', '-')}")
        st.markdown(f"**Livraison :** {badge(demande.get('livraison_statut') or 'À livrer')}", unsafe_allow_html=True)
        st.markdown(f"**Retour :** {badge(demande.get('retour_statut') or 'En attente retour')}", unsafe_allow_html=True)

    st.subheader("📦 Matériel à récupérer")
    if lignes.empty:
        st.write(demande.get("articles", "-"))
    else:
        st.dataframe(lignes, width="stretch", hide_index=True)

    ret_comment = st.text_area(
        "Observation retour",
        key=f"ret_only_comment_{selected_id}",
        placeholder="Exemple : matériel récupéré complet.",
    )

    materiel_manquant = st.text_area(
        "Matériel manquant",
        key=f"ret_only_manquant_{selected_id}",
        placeholder="Laisser vide si aucun.",
    )

    materiel_casse = st.text_area(
        "Matériel cassé / abîmé",
        key=f"ret_only_casse_{selected_id}",
        placeholder="Laisser vide si aucun.",
    )

    photo_file = st.file_uploader(
        "Photo retour / matériel cassé",
        type=["png", "jpg", "jpeg", "webp"],
        key=f"ret_only_photo_{selected_id}",
    )

    signature_retour = st.text_input(
        "Nom du signataire retour",
        value=agent,
        key=f"ret_only_signature_{selected_id}",
    )

    confirm_retour = st.checkbox(
        "Je confirme que le retour est contrôlé",
        key=f"ret_only_confirm_{selected_id}",
    )

    if st.button(
        "↩️ Confirmer retour et réintégrer stock",
        disabled=not confirm_retour or not signature_retour.strip(),
        width="stretch",
        key=f"ret_only_btn_{selected_id}",
    ):
        photo_path = save_retour_photo(photo_file)
        stock_msg = valider_retour(
            demande,
            agent,
            ret_comment.strip(),
            materiel_manquant.strip(),
            materiel_casse.strip(),
            signature_retour.strip(),
            photo_path,
        )
        st.success(f"Retour validé. {stock_msg}")
        st.rerun()


def show_clotures_admin(agent):
    st.subheader("🔒 Clôtures à effectuer")

    current_user = st.session_state.get("user") or {}
    current_role = str(current_user.get("role", "")).lower()

    preview_role = st.session_state.get("preview_role")
    if current_role == "admin" and preview_role:
        current_role = str(preview_role).lower()

    if current_role != "admin":
        st.error("Accès réservé administrateur.")
        st.stop()

    df = load_evenements_valides()

    if df.empty:
        st.info("Aucune demande à afficher.")
        return

    df = df[
        (df["livraison_statut"].fillna("") == "Livrée") &
        (df["retour_statut"].fillna("") == "Retournée") &
        (df["cloture_statut"].fillna("Ouverte") != "Clôturée")
    ]

    if df.empty:
        st.success("Aucune clôture en attente.")
        return

    selected_id = st.selectbox(
        "Sélectionner une demande à clôturer",
        df["id"].tolist(),
        format_func=lambda x: f"Demande #{x}",
        key="select_cloture_admin",
    )

    demande = df[df["id"] == selected_id].iloc[0].to_dict()
    lignes = load_lignes(selected_id)

    with st.container(border=True):
        st.markdown(f"### Demande #{selected_id} - {demande.get('motif', '-')}")
        st.write(f"**Demandeur :** {demande.get('demandeur', '-')}")
        st.write(f"**Email :** {demande.get('email', '-')}")
        st.write(f"**Lieu :** {demande.get('lieu', '-')}")
        st.markdown(f"**Livraison :** {badge(demande.get('livraison_statut') or '-')}", unsafe_allow_html=True)
        st.markdown(f"**Retour :** {badge(demande.get('retour_statut') or '-')}", unsafe_allow_html=True)
        st.markdown(f"**Clôture :** {badge(demande.get('cloture_statut') or 'Ouverte')}", unsafe_allow_html=True)

    st.subheader("📦 Matériel")
    if lignes.empty:
        st.write(demande.get("articles", "-"))
    else:
        st.dataframe(lignes, width="stretch", hide_index=True)

    cloture_comment = st.text_area(
        "Commentaire de clôture",
        key=f"cloture_admin_comment_{selected_id}",
        placeholder="Exemple : dossier complet, matériel réintégré, facture disponible.",
    )

    confirm_cloture = st.checkbox(
        "Je confirme la clôture définitive de cette demande",
        key=f"cloture_admin_confirm_{selected_id}",
    )

    if st.button(
        "🔒 Clôturer définitivement",
        disabled=not confirm_cloture,
        width="stretch",
        key=f"cloture_admin_btn_{selected_id}",
    ):
        ok, msg = cloturer_demande(demande, agent, cloture_comment.strip())
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

def show():
    ensure_columns()

    st.title("🚚 Espace Équipe Logistique")
    st.caption("Stock événement, livraisons et retours matériel")

    user = st.session_state.get("user")

    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    role = str(user.get("role", "")).lower()
    preview_role = st.session_state.get("preview_role")

    if role == "admin" and preview_role:
        role = str(preview_role).lower()

    if role not in ["admin", "interne", "equipe_interne"]:
        st.error("Accès réservé à l'équipe interne et aux administrateurs.")
        st.stop()

    agent = user.get("email") or user.get("username") or "équipe"

    tabs_names = [
        "📦 Stock Événement",
        "📅 Événements à venir",
        "🚚 Livraisons",
        "↩️ Retours",
    ]

    if role == "admin":
        tabs_names.append("🔒 Clôtures")

    onglet = st.tabs(tabs_names)

    with onglet[0]:
        show_stock_evenement()

    with onglet[1]:
        show_evenements()

    with onglet[2]:
        show_livraisons_only(agent)

    with onglet[3]:
        show_retours_only(agent)

    if role == "admin":
        with onglet[4]:
            show_clotures_admin(agent)
