# -*- coding: utf-8 -*-
from __future__ import annotations

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
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


APP_DIR = Path("/opt/logistique-pro")
DATA_DIR = APP_DIR / "data"
EXPORT_DIR = DATA_DIR / "exports" / "catalogue_vehicules"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

PHOTO_DIRS = [
    DATA_DIR / "garage_photos",
    DATA_DIR / "vehicules_photos",
    DATA_DIR / "images",
    APP_DIR / "assets" / "photos",
    APP_DIR / "static" / "photos",
    APP_DIR / "uploads",
]


def clean(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    value = str(value)
    if value.lower() in ["none", "nan", "nat"]:
        return ""
    return value.strip()


def vehicle_title(row: pd.Series) -> str:
    immat = clean(row.get("immatriculation"))
    nom = clean(row.get("nom"))
    modele = clean(row.get("modele"))
    return immat or nom or modele or f"Véhicule #{clean(row.get('id'))}"


def find_photo(row: pd.Series) -> Path | None:
    candidates: list[Path] = []

    for col in ["photo", "image", "image_path", "photo_path", "fichier_photo", "photo_file"]:
        value = clean(row.get(col))
        if value:
            candidates.append(Path(value))

    vehicule_id = clean(row.get("id"))
    immat_raw = clean(row.get("immatriculation"))
    immat_clean = immat_raw.replace("-", "").replace(" ", "").lower()
    nom = clean(row.get("nom")).lower()

    for folder in PHOTO_DIRS:
        if not folder.exists():
            continue

        for ext in ["jpg", "jpeg", "png", "webp"]:
            if vehicule_id:
                candidates.extend(folder.glob(f"*{vehicule_id}*.{ext}"))
            if immat_raw:
                candidates.extend(folder.glob(f"*{immat_raw}*.{ext}"))
            if immat_clean:
                candidates.extend(folder.glob(f"*{immat_clean}*.{ext}"))
            if nom:
                candidates.extend(folder.glob(f"*{nom[:20]}*.{ext}"))

    for candidate in candidates:
        try:
            if candidate.exists() and candidate.is_file():
                return candidate
            if not candidate.is_absolute():
                full = APP_DIR / candidate
                if full.exists() and full.is_file():
                    return full
        except Exception:
            pass

    return None


def prepare_image(src: Path, tmp: Path) -> Path | None:
    try:
        img = PILImage.open(src).convert("RGB")
        img.thumbnail((1200, 800))
        target = tmp / f"{src.stem}.jpg"
        img.save(target, "JPEG", quality=82, optimize=True)
        return target
    except Exception:
        return None


def image_flowable(row: pd.Series, tmp: Path):
    photo = find_photo(row)

    if not photo:
        return Paragraph("Aucune photo", ParagraphStyle("NoPhoto", alignment=TA_CENTER, textColor=colors.HexColor("#64748B")))

    prepared = prepare_image(photo, tmp)

    if not prepared:
        return Paragraph("Photo non lisible", ParagraphStyle("NoPhoto", alignment=TA_CENTER, textColor=colors.HexColor("#64748B")))

    try:
        img = PILImage.open(prepared)
        w, h = img.size
        max_w = 7.2 * cm
        max_h = 5.0 * cm
        ratio = min(max_w / w, max_h / h)
        return Image(str(prepared), width=w * ratio, height=h * ratio)
    except Exception:
        return Paragraph("Photo non lisible", ParagraphStyle("NoPhoto", alignment=TA_CENTER, textColor=colors.HexColor("#64748B")))


def details_table(row: pd.Series, styles):
    preferred = [
        "immatriculation", "nom", "marque", "modele", "categorie", "service",
        "energie", "kilometrage_actuel", "date_ct", "statut", "notes", "commentaire"
    ]

    cols = [c for c in preferred if c in row.index]
    cols += [c for c in row.index if c not in cols]

    data = []

    for col in cols:
        value = clean(row.get(col))
        if not value:
            continue
        label = str(col).replace("_", " ").capitalize()
        data.append([Paragraph(label, styles["FieldLabel"]), Paragraph(value, styles["FieldValue"])])

    if not data:
        data = [[Paragraph("Détail", styles["FieldLabel"]), Paragraph("Aucune information", styles["FieldValue"])]]

    table = Table(data, colWidths=[4.0 * cm, 10.2 * cm])
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


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawCentredString(A4[0] / 2, 0.55 * cm, f"Catalogue véhicules - Logistique Pro - Page {canvas.getPageNumber()}")
    canvas.restoreState()


def build_pdf(df: pd.DataFrame) -> Path:
    if df is None or df.empty:
        raise RuntimeError("Aucun véhicule à exporter.")

    pdf_path = EXPORT_DIR / f"catalogue_vehicules_complet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], fontSize=24, leading=30, textColor=colors.HexColor("#003366"), alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="CoverSub", parent=styles["Normal"], fontSize=12, leading=16, alignment=TA_CENTER, textColor=colors.HexColor("#475569")))
    styles.add(ParagraphStyle(name="ItemTitle", parent=styles["Heading2"], fontSize=17, leading=21, textColor=colors.HexColor("#003366"), spaceAfter=8))
    styles.add(ParagraphStyle(name="FieldLabel", parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#334155"), alignment=TA_LEFT))
    styles.add(ParagraphStyle(name="FieldValue", parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#111827"), alignment=TA_LEFT))

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, rightMargin=1.3 * cm, leftMargin=1.3 * cm, topMargin=1.2 * cm, bottomMargin=1.2 * cm)

    story = [
        Spacer(1, 3 * cm),
        Paragraph("Catalogue complet des véhicules", styles["CoverTitle"]),
        Spacer(1, 0.5 * cm),
        Paragraph(f"Export généré le {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["CoverSub"]),
        Paragraph(f"Nombre de véhicules : {len(df)}", styles["CoverSub"]),
        Spacer(1, 1 * cm),
        Paragraph("Logistique Pro - Ville de Marly", styles["CoverSub"]),
        PageBreak(),
    ]

    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)

        for index, (_, row) in enumerate(df.iterrows(), start=1):
            story.append(Paragraph(f"{index}. {vehicle_title(row)}", styles["ItemTitle"]))
            block = Table([[image_flowable(row, tmp), details_table(row, styles)]], colWidths=[7.8 * cm, 10.2 * cm])
            block.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(block)

            if index < len(df):
                story.append(PageBreak())

        doc.build(story, onFirstPage=footer, onLaterPages=footer)

    return pdf_path


def render_vehicules_pdf_export_button(df: pd.DataFrame):
    st.markdown("### 📄 Télécharger le catalogue véhicules en PDF")
    st.info("Génère directement un PDF avec tous les véhicules filtrés, leurs détails et les photos disponibles.")

    if st.button("📄 Générer le PDF véhicules avec photos", width="stretch", key="generate_catalogue_vehicules_pdf"):
        try:
            pdf = build_pdf(df)
            st.session_state["catalogue_vehicules_pdf"] = str(pdf)
            st.success(f"PDF généré : {pdf.name}")
        except Exception as exc:
            st.error(f"Erreur génération PDF véhicules : {exc}")

    value = st.session_state.get("catalogue_vehicules_pdf")
    if value:
        path = Path(value)
        if path.exists():
            with open(path, "rb") as f:
                st.download_button(
                    "⬇️ Télécharger le PDF véhicules",
                    data=f.read(),
                    file_name=path.name,
                    mime="application/pdf",
                    width="stretch",
                    key="download_catalogue_vehicules_pdf",
                )
