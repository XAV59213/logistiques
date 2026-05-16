# pages/Mes_Demandes.py

import sqlite3
import uuid
from pathlib import Path
from io import BytesIO
from datetime import datetime

import pandas as pd
import streamlit as st
from utils.devis_workflow import ensure_devis_columns, set_devis_uploaded
from utils.numbering import next_number

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from utils.facturation_settings import get_settings, get_tva_rate


BASE_DIR = Path("/opt/logistique-pro")
DEMANDES_DB = BASE_DIR / "data" / "demandes.db"
CATALOGUE_DB = BASE_DIR / "data" / "catalogue_articles.db"
DEVIS_SIGNES_DIR = BASE_DIR / "assets/devis_signes"
DEVIS_SIGNES_DIR.mkdir(parents=True, exist_ok=True)

tva_rate = 0.20  # valeur par défaut, remplacée par les paramètres

MAIRIE = {
    "nom": "Ville de Marly",
    "service": "Service Logistique & Événements",
    "adresse": "Place Gabriel Péri",
    "cp_ville": "59770 Marly",
    "email": "contact@marly.fr",
    "telephone": "03 27 23 99 00",
    "site": "www.marly.fr",
}


def connect():
    conn = sqlite3.connect(DEMANDES_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(table):
    if not DEMANDES_DB.exists():
        return False

    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists


def load_mes_demandes(email, is_admin_preview=False):
    if not table_exists("demandes"):
        return pd.DataFrame()

    conn = connect()

    if is_admin_preview:
        df = pd.read_sql_query("SELECT * FROM demandes ORDER BY created_at DESC", conn)
    else:
        df = pd.read_sql_query(
            "SELECT * FROM demandes WHERE email = ? ORDER BY created_at DESC",
            conn,
            params=[email],
        )

    conn.close()
    return df


def load_lignes(demande_id):
    if not table_exists("demande_lignes"):
        return pd.DataFrame()

    conn = connect()

    df = pd.read_sql_query(
        """
        SELECT 
            dl.article_id,
            dl.article_nom,
            dl.quantite,
            COALESCE(dl.prix_unitaire, 0) AS prix_unitaire,
            COALESCE(dl.total, 0) AS total
        FROM demande_lignes dl
        WHERE dl.demande_id = ?
        ORDER BY dl.id
        """,
        conn,
        params=[demande_id],
    )

    conn.close()

    if df.empty:
        return df

    if CATALOGUE_DB.exists():
        try:
            cconn = sqlite3.connect(CATALOGUE_DB)
            cdf = pd.read_sql_query(
                """
                SELECT id, image_path, notes, emplacement, categorie, sous_categorie
                FROM catalogue_articles
                """,
                cconn,
            )
            cconn.close()

            df = df.merge(
                cdf,
                how="left",
                left_on="article_id",
                right_on="id",
            )
        except Exception:
            pass

    return df


def safe(value, default="-"):
    if value is None:
        return default
    value = str(value)
    if value.strip() == "" or value.lower() == "nan":
        return default
    return value


def get_logo():
    candidates = [
        BASE_DIR / "assets/logo/logo.png",
        BASE_DIR / "assets/logo_mairie.png",
        BASE_DIR / "assets/photos/default/mairie.png",
    ]

    for p in candidates:
        if p.exists():
            return p

    return None


def build_article_image(path_value):
    if not path_value or str(path_value).lower() == "nan":
        return ""

    path = BASE_DIR / str(path_value)

    if not path.exists():
        return ""

    try:
        return Image(str(path), width=1.4 * cm, height=1.4 * cm)
    except Exception:
        return ""



def ensure_facture_number(demande_id):
    conn = connect()
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(demandes)")
    cols = [r["name"] for r in cur.fetchall()]

    if "numero_facture" not in cols:
        cur.execute("ALTER TABLE demandes ADD COLUMN numero_facture TEXT")

    cur.execute("SELECT numero_facture FROM demandes WHERE id = ?", (int(demande_id),))
    row = cur.fetchone()

    if row and row["numero_facture"]:
        numero = row["numero_facture"]
    else:
        numero = next_number("FAC")
        cur.execute(
            "UPDATE demandes SET numero_facture = ? WHERE id = ?",
            (numero, int(demande_id))
        )
        conn.commit()

    conn.close()
    return numero



def facture_pdf(demande, lignes, document_type="facture"):
    settings = get_settings()
    tva_rate = get_tva_rate()

    mairie = {
        "nom": settings.get("mairie_nom", "Ville de Marly"),
        "service": settings.get("mairie_service", "Service Logistique & Événements"),
        "adresse": settings.get("mairie_adresse", "Place Gabriel Péri"),
        "cp_ville": settings.get("mairie_cp_ville", "59770 Marly"),
        "email": settings.get("mairie_email", "contact@marly.fr"),
        "telephone": settings.get("mairie_telephone", "03 27 23 99 00"),
        "site": settings.get("mairie_site", "www.marly.fr"),
        "footer": settings.get("facture_footer", "© 2026 Ville de Marly - Logistique Pro"),
        "prefix": settings.get("facture_prefix", "FACT"),
    }

    if document_type == "devis":
        facture_numero = f"DEVIS-{datetime.now().strftime('%Y')}-{int(demande.get('id', 0)):06d}"
        titre_document = "DEVIS / RÉCAPITULATIF"
        libelle_numero = "N° devis"
    else:
        facture_numero = ensure_facture_number(demande.get("id"))
        titre_document = "FACTURE / RÉCAPITULATIF"
        libelle_numero = "N° facture"

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.3 * cm,
        leftMargin=1.3 * cm,
        topMargin=1.0 * cm,
        bottomMargin=1.0 * cm,
    )

    styles = getSampleStyleSheet()
    style_small = ParagraphStyle(
        "small",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
    )

    elements = []

    logo = get_logo()

    if logo:
        header = Table(
            [[
                Image(str(logo), width=3.0 * cm, height=3.0 * cm),
                Paragraph(
                    f"""
                    <b>{mairie['nom']}</b><br/>
                    {mairie['service']}<br/>
                    {mairie['adresse']}<br/>
                    {mairie['cp_ville']}<br/>
                    Email : {mairie['email']}<br/>
                    Tél : {mairie['telephone']}<br/>
                    Site : {mairie['site']}
                    """,
                    style_small,
                ),
                Paragraph(
                    f"""
                    <b>{titre_document}</b><br/>
                    {libelle_numero} : {facture_numero}<br/>
                    Demande n° {demande.get('id')}<br/>
                    Éditée le {datetime.now().strftime('%d/%m/%Y %H:%M')}
                    """,
                    styles["Heading2"],
                )
            ]],
            colWidths=[3.2 * cm, 7.2 * cm, 7.0 * cm],
        )
    else:
        header = Table(
            [[
                Paragraph(f"<b>{mairie['nom']}</b><br/>{mairie['service']}", styles["Heading2"]),
                Paragraph(f"<b>{titre_document}</b><br/>{libelle_numero} : {facture_numero}<br/>Demande n° {demande.get('id')}", styles["Heading2"]),
            ]],
            colWidths=[9 * cm, 8 * cm],
        )

    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))

    elements.append(header)
    elements.append(Spacer(1, 0.3 * cm))

    gratuit = int(demande.get("gratuit", 0) or 0) == 1

    infos = [
        ["Demandeur", safe(demande.get("demandeur"))],
        ["Email", safe(demande.get("email"))],
        ["Téléphone", safe(demande.get("telephone"))],
        ["Motif", safe(demande.get("motif"))],
        ["Date début", safe(demande.get("date_debut") or demande.get("date_evenement"))],
        ["Date fin", safe(demande.get("date_fin") or demande.get("date_evenement"))],
        ["Heure", safe(demande.get("heure_evenement"))],
        ["Lieu", safe(demande.get("lieu"))],
        ["Adresse du lieu", safe(demande.get("adresse_lieu"))],
        ["Ville", f"{safe(demande.get('code_postal'), '')} {safe(demande.get('ville'), '')}".strip()],
        ["Transport", "Oui" if (
            int(demande.get("besoin_transport", 0) or 0) == 1
            or int(demande.get("transport_valide", 0) or 0) == 1
            or (not lignes.empty and lignes["article_nom"].astype(str).str.lower().str.contains("transport").any())
        ) else "Non"],
        ["Adresse livraison", safe(demande.get("adresse_livraison"))],
        ["Statut", safe(demande.get("statut"))],
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

    elements.append(Paragraph("<b>Détail des articles et prestations</b>", styles["Heading2"]))

    article_data = [[
        "Image",
        "Article / description",
        "Qté",
        "PU HT",
        "Total HT",
        "TVA",
        "Total TTC",
    ]]

    total_ht = 0.0
    total_tva = 0.0
    total_ttc = 0.0

    if lignes.empty:
        article_data.append([
            "",
            Paragraph(safe(demande.get("articles")), style_small),
            "-",
            "-",
            "-",
            "-",
            "-",
        ])

        if int(demande.get("besoin_transport", 0) or 0) == 1:
            transport_ht = float(demande.get("montant_transport", 0) or 0)
            if int(demande.get("transport_gratuit", 0) or 0) == 1:
                transport_ht = 0.0

            transport_tva = transport_ht * tva_rate
            transport_ttc = transport_ht + transport_tva

            article_data.append([
                "",
                Paragraph("<b>Transport logistique</b><br/>Livraison / retrait du matériel", style_small),
                "1",
                f"{transport_ht:.2f} €",
                f"{transport_ht:.2f} €",
                f"{transport_tva:.2f} €",
                f"{transport_ttc:.2f} €",
            ])
    else:
        has_transport_line = False

        for _, row in lignes.iterrows():
            if "transport" in str(row.get("article_nom", "")).lower():
                has_transport_line = True
            qte = int(row.get("quantite", 0) or 0)
            pu_ht = float(row.get("prix_unitaire", 0) or 0)
            ligne_ht = pu_ht * qte
            ligne_tva = ligne_ht * tva_rate
            ligne_ttc = ligne_ht + ligne_tva

            total_ht += ligne_ht
            total_tva += ligne_tva
            total_ttc += ligne_ttc

            desc = safe(row.get("notes"), "")
            emplacement = safe(row.get("emplacement"), "")

            texte = f"<b>{safe(row.get('article_nom'))}</b>"
            if desc:
                texte += f"<br/>{desc}"
            if emplacement:
                texte += f"<br/><i>Emplacement : {emplacement}</i>"

            article_data.append([
                build_article_image(row.get("image_path")),
                Paragraph(texte, style_small),
                str(qte),
                f"{pu_ht:.2f} €",
                f"{ligne_ht:.2f} €",
                f"{ligne_tva:.2f} €",
                f"{ligne_ttc:.2f} €",
            ])

        if int(demande.get("besoin_transport", 0) or 0) == 1 and not has_transport_line:
            transport_ht = float(demande.get("montant_transport", 0) or 0)
            if int(demande.get("transport_gratuit", 0) or 0) == 1:
                transport_ht = 0.0

            transport_tva = transport_ht * tva_rate
            transport_ttc = transport_ht + transport_tva

            total_ht += transport_ht
            total_tva += transport_tva
            total_ttc += transport_ttc

            article_data.append([
                "",
                Paragraph("<b>Transport logistique</b><br/>Livraison / retrait du matériel", style_small),
                "1",
                f"{transport_ht:.2f} €",
                f"{transport_ht:.2f} €",
                f"{transport_tva:.2f} €",
                f"{transport_ttc:.2f} €",
            ])

    article_table = Table(
        article_data,
        colWidths=[1.7 * cm, 6.1 * cm, 1.2 * cm, 2.0 * cm, 2.1 * cm, 1.8 * cm, 2.3 * cm],
        repeatRows=1,
    )

    article_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#00A651")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    elements.append(article_table)
    elements.append(Spacer(1, 0.5 * cm))

    if gratuit:
        remise = total_ttc
        net_a_payer = 0.0
        total_rows = [
            ["Total HT", f"{total_ht:.2f} €"],
            ["TVA", f"{total_tva:.2f} €"],
            ["Total TTC", f"{total_ttc:.2f} €"],
            ["Remise association", f"-{remise:.2f} €"],
            ["Net à payer", "0.00 €"],
        ]
    else:
        net_a_payer = total_ttc
        total_rows = [
            ["Total HT", f"{total_ht:.2f} €"],
            ["TVA", f"{total_tva:.2f} €"],
            ["Total TTC", f"{total_ttc:.2f} €"],
            ["Net à payer", f"{net_a_payer:.2f} €"],
        ]

    total_table = Table(total_rows, colWidths=[12 * cm, 5.2 * cm])
    total_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#003366")),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("PADDING", (0, 0), (-1, -1), 7),
    ]))

    elements.append(total_table)

    if gratuit:
        elements.append(Spacer(1, 0.3 * cm))
        elements.append(Paragraph(
            "Cette facture est émise à titre récapitulatif. "
            "Le montant est pris en charge dans le cadre associatif après validation par la Ville de Marly.",
            style_small,
        ))

    if demande.get("commentaire_admin"):
        elements.append(Spacer(1, 0.5 * cm))
        elements.append(Paragraph("<b>Commentaire administrateur</b>", styles["Heading3"]))
        elements.append(Paragraph(str(demande.get("commentaire_admin")), styles["BodyText"]))

    elements.append(Spacer(1, 0.8 * cm))
    elements.append(Paragraph(mairie["footer"], style_small))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()



def mark_facture_lue(demande_id):
    conn = connect()
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(demandes)")
    cols = [r["name"] for r in cur.fetchall()]

    if "facture_lue" not in cols:
        cur.execute("ALTER TABLE demandes ADD COLUMN facture_lue INTEGER DEFAULT 0")

    if "facture_lue_at" not in cols:
        cur.execute("ALTER TABLE demandes ADD COLUMN facture_lue_at TEXT")

    cur.execute("""
        UPDATE demandes
        SET facture_lue = 1,
            facture_lue_at = ?
        WHERE id = ?
    """, (
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        int(demande_id),
    ))

    conn.commit()
    conn.close()




def save_devis_signe(file, demande_id):
    if file is None:
        return ""

    ext = Path(file.name).suffix.lower()
    if ext not in [".pdf", ".png", ".jpg", ".jpeg", ".webp"]:
        return ""

    filename = f"devis_signe_{demande_id}_{uuid.uuid4().hex}{ext}"
    path = DEVIS_SIGNES_DIR / filename

    with open(path, "wb") as f:
        f.write(file.getbuffer())

    return str(path.relative_to(BASE_DIR))


def devis_pdf(demande, lignes):
    return facture_pdf(demande, lignes, document_type="devis")

def show():
    ensure_devis_columns()
    st.title("📋 Mes Demandes")
    st.caption("Historique réel de vos demandes et factures")

    user = st.session_state.get("user")

    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    role = str(user.get("role", "")).lower()
    preview_role = st.session_state.get("preview_role")

    is_admin_preview = role == "admin" and bool(preview_role)
    email = user.get("email", "")

    if not DEMANDES_DB.exists():
        st.info("Aucune base de demandes disponible.")
        return

    df = load_mes_demandes(email, is_admin_preview)

    if df.empty:
        st.info("Aucune demande trouvée.")
        return

    statut_filter = st.selectbox(
        "Statut",
        ["Toutes", "En attente", "Devis à signer", "Devis signé reçu", "Validée", "Refusée", "Terminée"],
        key="mes_demandes_statut",
    )

    if statut_filter != "Toutes" and "statut" in df.columns:
        df = df[df["statut"] == statut_filter]

    st.metric("Nombre de demandes", len(df))

    if df.empty:
        st.info("Aucune demande avec ce statut.")
        return

    display_cols = [
        col for col in [
            "id", "created_at", "motif", "date_evenement", "lieu",
            "ville", "articles", "statut", "montant_estime", "gratuit"
        ]
        if col in df.columns
    ]

    display = df[display_cols].rename(columns={
        "id": "N° Demande",
        "created_at": "Créée le",
        "motif": "Motif",
        "date_evenement": "Date événement",
        "date_debut": "Date début",
        "date_fin": "Date fin",
        "lieu": "Lieu",
        "ville": "Ville",
        "articles": "Articles",
        "statut": "Statut",
        "montant_estime": "Montant estimé",
        "gratuit": "Gratuit",
    })

    if "Gratuit" in display.columns:
        display["Gratuit"] = display["Gratuit"].apply(lambda x: "Oui" if int(x or 0) == 1 else "Non")

    if "Montant estimé" in display.columns:
        display["Montant estimé"] = display["Montant estimé"].apply(lambda x: f"{float(x or 0):.2f} €")

    st.dataframe(display, width="stretch", hide_index=True)

    st.divider()
    st.subheader("🔎 Détail d'une demande")

    demande_options = {
        f"Demande #{int(row['id'])}": int(row["id"])
        for _, row in df.iterrows()
    }

    selected_label = st.selectbox(
        "Sélectionner une demande",
        list(demande_options.keys()),
        key="detail_demande_select"
    )

    selected_id = demande_options[selected_label]

    demande = df[df["id"] == selected_id].iloc[0].to_dict()
    lignes = load_lignes(selected_id)

    def safe(v):
        if v is None:
            return "-"
        txt = str(v).strip()
        return txt if txt else "-"

    with st.container(border=True):
        statut = safe(demande.get("statut"))
        transport_txt = "Oui" if int(demande.get("besoin_transport", 0) or 0) == 1 else "Non"

        st.markdown(
            f"""
            <div style="padding:10px 4px 16px 4px;">
                <h3 style="margin-bottom:4px;">📄 Demande #{selected_id}</h3>
                <span style="
                    display:inline-block;
                    padding:6px 14px;
                    border-radius:999px;
                    background:#e0f2fe;
                    color:#075985;
                    font-weight:700;
                    font-size:13px;
                ">{statut}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns(2)

        with c1:
            st.markdown("#### 👤 Informations demandeur")
            st.markdown(f"**Nom :** {safe(demande.get('demandeur'))}")
            st.markdown(f"**Email :** {safe(demande.get('email'))}")
            st.markdown(f"**Téléphone :** {safe(demande.get('telephone'))}")

            st.markdown("#### 🎉 Événement")
            st.markdown(f"**Motif :** {safe(demande.get('motif'))}")
            st.markdown(f"**Date début :** {safe(demande.get('date_debut') or demande.get('date_evenement'))}")
            st.markdown(f"**Date fin :** {safe(demande.get('date_fin') or demande.get('date_evenement'))}")

        with c2:
            st.markdown("#### 📍 Adresse")
            st.markdown(f"**Lieu :** {safe(demande.get('lieu'))}")
            st.markdown(f"**Adresse :** {safe(demande.get('adresse_lieu'))}")
            st.markdown(f"**Ville :** {safe(demande.get('code_postal'))} {safe(demande.get('ville'))}")

            st.markdown("#### 🚚 Livraison")
            st.markdown(f"**Transport :** {transport_txt}")
            st.markdown(f"**Adresse livraison :** {safe(demande.get('adresse_livraison'))}")

    st.subheader("📝 Devis")

    statut_demande = str(demande.get("statut", "")).strip()

    if statut_demande in ["Devis à signer", "Devis signé reçu", "Validée"]:
        st.download_button(
            "⬇️ Télécharger le devis PDF",
            data=devis_pdf(demande, lignes),
            file_name=f"demande_{selected_id}_devis.pdf",
            mime="application/pdf",
            width="stretch",
            key=f"download_devis_{selected_id}",
        )

    if statut_demande == "Devis à signer":
        st.warning("Merci de télécharger le devis, de le signer, puis de le transmettre ci-dessous sous 5 jours.")

        devis_file = st.file_uploader(
            "Uploader le devis signé",
            type=["pdf", "png", "jpg", "jpeg", "webp"],
            key=f"upload_devis_signe_{selected_id}",
        )

        if devis_file is not None:
            devis_path = save_devis_signe(devis_file, selected_id)
            if devis_path:
                set_devis_uploaded(selected_id, devis_path)
                try:
                    from utils.messages import send_message
                    send_message(
                        "Tous",
                        f"Devis signé reçu - Demande #{selected_id}",
                        f"""Bonjour,

Un devis signé a été transmis pour la demande #{selected_id}.

Merci de le contrôler dans Validation Demandes.

Cordialement,
Logistique Pro"""
                    )
                except Exception:
                    pass
                st.success("Devis signé transmis. Il sera contrôlé par l'administrateur.")
                st.rerun()
            else:
                st.error("Format de fichier non accepté.")

    elif statut_demande == "Devis signé reçu":
        st.info("Votre devis signé a été transmis. Il est en attente de validation administrateur.")

    st.subheader("🧾 Facture PDF")

    cloture_ok = str(demande.get("cloture_statut", "") or "").strip() == "Clôturée"

    if not cloture_ok:
        st.warning("La facture sera disponible uniquement après clôture finale par l'administrateur.")
        st.stop()

    statut_demande = str(demande.get("statut", "")).strip()

    if statut_demande == "Validée":
        facture_clicked = st.download_button(
            "⬇️ Télécharger la facture PDF",
            data=facture_pdf(demande, lignes),
            file_name=f"demande_{selected_id}_facture.pdf",
            mime="application/pdf",
            width="stretch",
        )

        if facture_clicked:
            mark_facture_lue(selected_id)
            st.success("Facture marquée comme lue.")
            st.rerun()
    else:
        st.warning("La facture PDF sera disponible uniquement après clôture finale par l'administrateur.")
