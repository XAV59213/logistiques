# -*- coding: utf-8 -*-
from __future__ import annotations

import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image as PILImage

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


APP_DIR = Path("/opt/logistique-pro")
DATA_DIR = APP_DIR / "data"
EXPORT_DIR = DATA_DIR / "exports" / "catalogue_batiments"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


PHOTO_SEARCH_DIRS = [
    DATA_DIR,
    DATA_DIR / "photos",
    DATA_DIR / "images",
    DATA_DIR / "batiments",
    DATA_DIR / "patrimoine",
    DATA_DIR / "patrimoine_bati",
    DATA_DIR / "patrimoine_photos",
    APP_DIR / "assets",
    APP_DIR / "assets" / "photos",
    APP_DIR / "assets" / "images",
    APP_DIR / "static",
    APP_DIR / "static" / "photos",
    APP_DIR / "static" / "images",
    APP_DIR / "uploads",
]


PHOTO_COLUMNS = [
    "photo",
    "image",
    "image_path",
    "photo_path",
    "chemin_photo",
    "fichier_photo",
    "photo_file",
    "nom_photo",
    "url_photo",
]


NAME_COLUMNS = [
    "nom",
    "batiment_nom",
    "nom_batiment",
    "designation",
    "libelle",
    "name",
]


def clean(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def get_name(row: pd.Series) -> str:
    for col in NAME_COLUMNS:
        if col in row.index:
            value = clean(row.get(col))
            if value:
                return value
    return "Bâtiment"


def safe_filename(value: str) -> str:
    value = clean(value)
    value = value.replace("/", "_").replace("\\", "_")
    value = "".join(c for c in value if c.isalnum() or c in " _.-")
    return value or "catalogue_batiments"


def normalize_name(value: str) -> str:
    value = clean(value).lower()
    repl = {
        "é": "e",
        "è": "e",
        "ê": "e",
        "ë": "e",
        "à": "a",
        "â": "a",
        "ä": "a",
        "ç": "c",
        "ù": "u",
        "û": "u",
        "ü": "u",
        "ô": "o",
        "ö": "o",
        "î": "i",
        "ï": "i",
        "'": "",
        "’": "",
    }
    for a, b in repl.items():
        value = value.replace(a, b)
    value = value.replace(" ", "_").replace("-", "_")
    return value


def find_photo(row: pd.Series) -> Path | None:
    candidates = []

    for col in PHOTO_COLUMNS:
        if col in row.index:
            value = clean(row.get(col))
            if value:
                candidates.append(value)

    for col in row.index:
        low = str(col).lower()
        if "photo" in low or "image" in low:
            value = clean(row.get(col))
            if value and value not in candidates:
                candidates.append(value)

    building_name = get_name(row)
    normalized = normalize_name(building_name)

    if normalized:
        for ext in [".jpg", ".jpeg", ".png", ".webp"]:
            candidates.append(normalized + ext)

    for value in candidates:
        p = Path(value)

        direct_candidates = [
            p,
            APP_DIR / value,
            DATA_DIR / value,
            DATA_DIR / p.name,
        ]

        for candidate in direct_candidates:
            try:
                if candidate.exists() and candidate.is_file():
                    return candidate
            except Exception:
                pass

        filename = p.name

        if not filename:
            continue

        for folder in PHOTO_SEARCH_DIRS:
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

    return None


def prepare_image_for_pdf(src: Path, temp_dir: Path, max_width_px: int = 1200) -> Path | None:
    try:
        img = PILImage.open(src)
        img = img.convert("RGB")

        width, height = img.size

        if width > max_width_px:
            ratio = max_width_px / float(width)
            new_height = int(height * ratio)
            img = img.resize((max_width_px, new_height))

        target = temp_dir / f"{src.stem}.jpg"
        img.save(target, "JPEG", quality=82, optimize=True)
        return target

    except Exception:
        return None


def make_photo_flowable(row: pd.Series, temp_dir: Path):
    photo = find_photo(row)

    if not photo:
        return Paragraph("Aucune photo", ParagraphStyle("NoPhoto", alignment=TA_CENTER, textColor=colors.HexColor("#64748B")))

    prepared = prepare_image_for_pdf(photo, temp_dir)

    if not prepared:
        return Paragraph("Photo non lisible", ParagraphStyle("NoPhoto", alignment=TA_CENTER, textColor=colors.HexColor("#64748B")))

    try:
        img = PILImage.open(prepared)
        w, h = img.size

        max_w = 7.2 * cm
        max_h = 5.0 * cm

        ratio = min(max_w / w, max_h / h)
        draw_w = w * ratio
        draw_h = h * ratio

        return Image(str(prepared), width=draw_w, height=draw_h)

    except Exception:
        return Paragraph("Photo non lisible", ParagraphStyle("NoPhoto", alignment=TA_CENTER, textColor=colors.HexColor("#64748B")))


def row_details_table(row: pd.Series, styles):
    data = []

    for col in row.index:
        value = clean(row.get(col))
        if not value:
            continue

        label = str(col).replace("_", " ").capitalize()
        data.append([
            Paragraph(label, styles["FieldLabel"]),
            Paragraph(value, styles["FieldValue"]),
        ])

    if not data:
        data = [[Paragraph("Détail", styles["FieldLabel"]), Paragraph("Aucune information", styles["FieldValue"])]]

    table = Table(data, colWidths=[4.2 * cm, 10.2 * cm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    return table


def build_pdf(df: pd.DataFrame) -> Path:
    if df is None or df.empty:
        raise RuntimeError("Aucun bâtiment à exporter.")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = EXPORT_DIR / f"catalogue_batiments_complet_{stamp}.pdf"

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="CoverTitle",
        parent=styles["Title"],
        fontSize=24,
        leading=30,
        textColor=colors.HexColor("#003366"),
        alignment=TA_CENTER,
        spaceAfter=20,
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
        name="BuildingTitle",
        parent=styles["Heading2"],
        fontSize=17,
        leading=21,
        textColor=colors.HexColor("#003366"),
        spaceAfter=8,
    ))

    styles.add(ParagraphStyle(
        name="FieldLabel",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#334155"),
        alignment=TA_LEFT,
    ))

    styles.add(ParagraphStyle(
        name="FieldValue",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#111827"),
        alignment=TA_LEFT,
    ))

    styles.add(ParagraphStyle(
        name="SmallInfo",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#64748B"),
    ))

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=1.3 * cm,
        leftMargin=1.3 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        title="Catalogue complet des bâtiments",
        author="Logistique Pro",
    )

    story = []

    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph("Catalogue complet des bâtiments", styles["CoverTitle"]))
    story.append(Paragraph(f"Export généré le {now}", styles["CoverSub"]))
    story.append(Paragraph(f"Nombre de bâtiments : {len(df)}", styles["CoverSub"]))
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph("Logistique Pro - Ville de Marly", styles["CoverSub"]))
    story.append(PageBreak())

    with tempfile.TemporaryDirectory() as tmp:
        temp_dir = Path(tmp)

        for index, (_, row) in enumerate(df.iterrows(), start=1):
            name = get_name(row)

            story.append(Paragraph(f"{index}. {name}", styles["BuildingTitle"]))

            photo_flowable = make_photo_flowable(row, temp_dir)
            details_flowable = row_details_table(row, styles)

            main_table = Table(
                [[photo_flowable, details_flowable]],
                colWidths=[7.8 * cm, 10.2 * cm],
            )

            main_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))

            story.append(main_table)
            story.append(Spacer(1, 0.5 * cm))

            # Une fiche par page pour un catalogue propre
            if index < len(df):
                story.append(PageBreak())

        doc.build(story, onFirstPage=footer, onLaterPages=footer)

    return pdf_path


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748B"))

    page_num = canvas.getPageNumber()
    text = f"Catalogue bâtiments - Logistique Pro - Page {page_num}"

    canvas.drawCentredString(A4[0] / 2, 0.55 * cm, text)
    canvas.restoreState()


def render_pdf_export_button(df: pd.DataFrame):
    st.markdown("### 📄 Télécharger le catalogue complet en PDF")

    st.info(
        "Génère directement un PDF avec tous les bâtiments, leurs détails et les photos disponibles."
    )

    if st.button("📄 Générer le PDF complet avec photos", width="stretch", key="generate_catalogue_batiments_pdf"):
        try:
            pdf_path = build_pdf(df)
            st.session_state["catalogue_batiments_pdf"] = str(pdf_path)
            st.success(f"PDF généré : {pdf_path.name}")
        except Exception as exc:
            st.error(f"Erreur génération PDF : {exc}")

    pdf_value = st.session_state.get("catalogue_batiments_pdf")

    if pdf_value:
        pdf_path = Path(pdf_value)

        if pdf_path.exists():
            with open(pdf_path, "rb") as f:
                st.download_button(
                    "⬇️ Télécharger le PDF complet",
                    data=f.read(),
                    file_name=pdf_path.name,
                    mime="application/pdf",
                    width="stretch",
                    key="download_catalogue_batiments_pdf",
                )
