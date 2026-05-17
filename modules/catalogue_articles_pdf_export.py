# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image as PILImage, ImageOps

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    KeepInFrame,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


APP_DIR = Path("/opt/logistique-pro")
DATA_DIR = APP_DIR / "data"
EXPORT_DIR = DATA_DIR / "exports" / "catalogue_articles"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_IMAGE = APP_DIR / "assets/photos/default/mairie.png"

IMAGE_DIRS = [
    APP_DIR / "assets/photos/catalogue",
    APP_DIR / "assets/photos",
    APP_DIR / "assets/images",
    APP_DIR / "static/photos",
    APP_DIR / "static/images",
    DATA_DIR / "photos",
    DATA_DIR / "images",
    APP_DIR / "uploads",
]



def find_logo() -> Path | None:
    candidates = [
        APP_DIR / "assets" / "logo.png",
        APP_DIR / "assets" / "logo.jpg",
        APP_DIR / "assets" / "images" / "logo.png",
        APP_DIR / "assets" / "images" / "logo.jpg",
        APP_DIR / "assets" / "photos" / "logo.png",
        APP_DIR / "assets" / "photos" / "logo.jpg",
        APP_DIR / "assets" / "photos" / "default" / "mairie.png",
        APP_DIR / "assets" / "photos" / "default" / "mairie.jpg",
        DATA_DIR / "logo.png",
        DATA_DIR / "logo.jpg",
    ]

    for candidate in candidates:
        try:
            if candidate.exists() and candidate.is_file():
                return candidate
        except Exception:
            pass

    return None


def logo_flowable():
    logo = find_logo()

    if not logo:
        return Spacer(1, 1.2 * cm)

    try:
        img = PILImage.open(logo).convert("RGB")
        w, h = img.size

        max_w = 5.0 * cm
        max_h = 3.0 * cm

        ratio = min(max_w / w, max_h / h)
        return Image(str(logo), width=w * ratio, height=h * ratio)

    except Exception:
        return Spacer(1, 1.2 * cm)


def clean(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    value = str(value).strip()

    if value.lower() in ["none", "nan", "nat"]:
        return ""

    return value


def money(value) -> str:
    value = clean(value)
    if not value:
        return "0,00 €"

    try:
        return f"{float(value):.2f} €".replace(".", ",")
    except Exception:
        return value


def article_title(row: pd.Series) -> str:
    return (
        clean(row.get("nom"))
        or clean(row.get("designation"))
        or clean(row.get("libelle"))
        or f"Article #{clean(row.get('id'))}"
    )


def article_state(row: pd.Series) -> str:
    value = clean(row.get("etat"))

    if value:
        return value

    try:
        stock = float(clean(row.get("stock")) or 0)
        stock_min = float(clean(row.get("stock_min")) or clean(row.get("seuil")) or 0)

        if stock <= 0:
            return "Critique"
        if stock <= stock_min:
            return "Bas"
        return "OK"

    except Exception:
        return ""


def find_image(row: pd.Series) -> Path | None:
    candidates = []

    for col in [
        "image_path",
        "photo",
        "image",
        "photo_path",
        "fichier_photo",
        "image_file",
        "nom_image",
    ]:
        value = clean(row.get(col))
        if value:
            candidates.append(value)

    for col in row.index:
        low = str(col).lower()
        if "image" in low or "photo" in low:
            value = clean(row.get(col))
            if value and value not in candidates:
                candidates.append(value)

    for value in candidates:
        p = Path(value)

        possible = [
            p,
            APP_DIR / value,
            DATA_DIR / value,
            APP_DIR / p.name,
            DATA_DIR / p.name,
        ]

        for candidate in possible:
            try:
                if candidate.exists() and candidate.is_file():
                    return candidate
            except Exception:
                pass

        filename = p.name

        if filename:
            for folder in IMAGE_DIRS:
                if not folder.exists():
                    continue

                direct = folder / filename

                if direct.exists() and direct.is_file():
                    return direct

                try:
                    for found in folder.rglob(filename):
                        if found.exists() and found.is_file():
                            return found
                except Exception:
                    pass

    if DEFAULT_IMAGE.exists():
        return DEFAULT_IMAGE

    return None


def prepare_image_for_card(row: pd.Series, tmp: Path) -> Path | None:
    src = find_image(row)

    if not src:
        return None

    try:
        img = PILImage.open(src).convert("RGB")

        try:
            resampling = PILImage.Resampling.LANCZOS
        except Exception:
            resampling = PILImage.LANCZOS

        # Format horizontal compact, proche des cartes de l'application.
        img = ImageOps.fit(img, (420, 170), method=resampling)

        target = tmp / f"article_{abs(hash(str(src)))}.jpg"
        img.save(target, "JPEG", quality=84, optimize=True)

        return target

    except Exception:
        return None


def paragraph(text: str, style):
    text = clean(text)
    text = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return Paragraph(text, style)


def state_badge(text: str, styles):
    state = clean(text)
    low = state.lower()

    if low in ["ok", "bon", "actif"]:
        bg = colors.HexColor("#DCFCE7")
        fg = colors.HexColor("#166534")
    elif low in ["bas", "faible"]:
        bg = colors.HexColor("#FEF3C7")
        fg = colors.HexColor("#92400E")
    elif low in ["critique", "rupture"]:
        bg = colors.HexColor("#FEE2E2")
        fg = colors.HexColor("#991B1B")
    else:
        bg = colors.HexColor("#E0F2FE")
        fg = colors.HexColor("#075985")

    t = Table([[Paragraph(state, styles["Badge"])]], colWidths=[1.55 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("TEXTCOLOR", (0, 0), (-1, -1), fg),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.2, bg),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))

    return t


def line(label: str, value: str, styles):
    if not clean(value):
        return None
    return Paragraph(f"<b>{label} :</b> {clean(value)}", styles["Small"])


def article_card(row: pd.Series, styles, tmp: Path):
    image_path = prepare_image_for_card(row, tmp)

    if image_path:
        img = Image(str(image_path), width=5.05 * cm, height=2.05 * cm)
    else:
        img = Table(
            [[Paragraph("Aucune image", styles["NoImage"])]],
            colWidths=[5.05 * cm],
            rowHeights=[2.05 * cm],
        )
        img.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#E8F1FB")),
            ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#DBE3EF")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))

    title = article_title(row)

    categorie = clean(row.get("categorie"))
    sous_categorie = clean(row.get("sous_categorie")) or clean(row.get("sous-catégorie")) or clean(row.get("sous_catégorie"))
    stock = clean(row.get("stock"))
    stock_min = clean(row.get("stock_min")) or clean(row.get("seuil"))
    prix_facturation = clean(row.get("prix_facturation"))
    prix_achat = clean(row.get("prix_achat"))
    prix_location = clean(row.get("prix_location"))
    emplacement = clean(row.get("emplacement"))
    etat = article_state(row)

    elements = [
        img,
        Spacer(1, 0.10 * cm),
        Paragraph(title, styles["CardTitle"]),
        Spacer(1, 0.06 * cm),
    ]

    info_lines = [
        line("Catégorie", categorie, styles),
        line("Sous-catégorie", sous_categorie, styles),
        line("Stock", f"{stock or '0'} unité" + (f" — min {stock_min}" if stock_min else ""), styles),
        line("Prix facturation", money(prix_facturation), styles),
        line("Prix d'achat", money(prix_achat), styles),
        line("Prix location", money(prix_location), styles),
        line("Emplacement", emplacement, styles),
    ]

    for item in info_lines:
        if item is not None:
            elements.append(item)

    if etat:
        elements.append(Spacer(1, 0.07 * cm))
        elements.append(
            Table(
                [[Paragraph("<b>État :</b>", styles["Small"]), state_badge(etat, styles)]],
                colWidths=[1.0 * cm, 1.8 * cm],
            )
        )

    framed = KeepInFrame(
        5.25 * cm,
        5.95 * cm,
        elements,
        mode="shrink",
        hAlign="LEFT",
        vAlign="TOP",
    )

    card = Table([[framed]], colWidths=[5.55 * cm], rowHeights=[6.15 * cm])
    card.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.55, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    return card


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawCentredString(
        landscape(A4)[0] / 2,
        0.55 * cm,
        f"Catalogue articles - Logistique Pro - Page {canvas.getPageNumber()}",
    )
    canvas.restoreState()


def build_pdf(df: pd.DataFrame) -> Path:
    if df is None or df.empty:
        raise RuntimeError("Aucun article à exporter.")

    pdf_path = EXPORT_DIR / f"catalogue_articles_cartes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="CoverTitle",
        parent=styles["Title"],
        fontSize=24,
        leading=30,
        textColor=colors.HexColor("#003366"),
        alignment=TA_CENTER,
    ))

    styles.add(ParagraphStyle(
        name="CoverSub",
        parent=styles["Normal"],
        fontSize=12,
        leading=16,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#475569"),
    ))

    styles.add(ParagraphStyle(
        name="CardTitle",
        parent=styles["Heading3"],
        fontSize=8.4,
        leading=9.4,
        textColor=colors.HexColor("#1F2937"),
        spaceAfter=3,
    ))

    styles.add(ParagraphStyle(
        name="Small",
        parent=styles["Normal"],
        fontSize=5.8,
        leading=6.8,
        textColor=colors.HexColor("#111827"),
    ))

    styles.add(ParagraphStyle(
        name="Badge",
        parent=styles["Normal"],
        fontSize=5.6,
        leading=6.2,
        alignment=TA_CENTER,
    ))

    styles.add(ParagraphStyle(
        name="NoImage",
        parent=styles["Normal"],
        fontSize=9,
        leading=11,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#003366"),
    ))

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=landscape(A4),
        rightMargin=0.65 * cm,
        leftMargin=0.65 * cm,
        topMargin=0.65 * cm,
        bottomMargin=0.65 * cm,
        title="Catalogue articles",
        author="Logistique Pro",
    )

    story = [
        Spacer(1, 1.0 * cm),
        logo_flowable(),
        Spacer(1, 0.6 * cm),
        Paragraph("Catalogue complet des articles", styles["CoverTitle"]),
        Spacer(1, 0.45 * cm),
        Paragraph(f"Export généré le {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["CoverSub"]),
        Paragraph(f"Nombre d'articles : {len(df)}", styles["CoverSub"]),
        Spacer(1, 0.8 * cm),
        Paragraph("Logistique Pro - Ville de Marly", styles["CoverSub"]),
        PageBreak(),
    ]

    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)

        cards = [article_card(row, styles, tmp) for _, row in df.iterrows()]

                # 8 cartes par page : 4 colonnes x 2 lignes, comme un vrai catalogue compact.
        for i in range(0, len(cards), 8):
            chunk = cards[i:i + 8]

            while len(chunk) < 8:
                chunk.append(Spacer(1, 1))

            page_table = Table(
                [
                    [chunk[0], chunk[1], chunk[2], chunk[3]],
                    [chunk[4], chunk[5], chunk[6], chunk[7]],
                ],
                colWidths=[6.85 * cm, 6.85 * cm, 6.85 * cm, 6.85 * cm],
                rowHeights=[8.4 * cm, 8.4 * cm],
                hAlign="CENTER",
            )

            page_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))

            story.append(page_table)

            if i + 8 < len(cards):
                story.append(PageBreak())

        doc.build(story, onFirstPage=footer, onLaterPages=footer)


    return pdf_path


def render_articles_pdf_export_button(df: pd.DataFrame):
    st.markdown("### 📄 Télécharger le catalogue articles en PDF")

    st.info(
        "Génère un PDF en présentation catalogue : 8 articles par page, cadres, image, titre, stock, prix, emplacement et état."
    )

    if st.button("📄 Générer le PDF articles 8 par page", width="stretch", key="generate_catalogue_articles_cards_pdf"):
        try:
            pdf = build_pdf(df)
            st.session_state["catalogue_articles_pdf"] = str(pdf)
            st.success(f"PDF généré : {pdf.name}")
        except Exception as exc:
            st.error(f"Erreur génération PDF articles : {exc}")

    value = st.session_state.get("catalogue_articles_pdf")

    if value:
        path = Path(value)

        if path.exists():
            with open(path, "rb") as f:
                st.download_button(
                    "⬇️ Télécharger le PDF articles",
                    data=f.read(),
                    file_name=path.name,
                    mime="application/pdf",
                    width="stretch",
                    key="download_catalogue_articles_pdf",
                )
