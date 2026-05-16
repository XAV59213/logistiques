# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from .batiments import load_batiments, get_batiment
from .controles import load_controles
from .entretiens import load_entretiens
from .db import get_db_path


PROJECT_DIR = Path("/opt/logistique-pro")
EXPORT_DIR = PROJECT_DIR / "data" / "exports" / "patrimoine"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def _clean(value: Any) -> str:
    if value is None:
        return ""
    value = str(value)
    if value.lower() in ["none", "nan", "nat"]:
        return ""
    return value.strip()


def _format_date(value: Any) -> str:
    value = _clean(value)
    if not value:
        return ""

    try:
        parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
        if pd.isna(parsed):
            return value
        return parsed.strftime("%d/%m/%Y")
    except Exception:
        return value


def _to_date(value: Any):
    value = _clean(value)
    if not value:
        return None

    try:
        parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
        if pd.isna(parsed):
            return None
        return parsed.date()
    except Exception:
        return None


def _get_photo_path(row: dict[str, Any]) -> str:
    for key in ["photo_path", "image_path", "photo", "image"]:
        val = _clean(row.get(key))
        if val:
            path = Path(val)
            if not path.is_absolute():
                path = PROJECT_DIR / val
            if path.exists():
                return str(path)
    return ""


def _safe_filename(name: str) -> str:
    name = _clean(name) or "document"
    for ch in ['/', '\\', ':', '*', '?', '"', '<', '>', '|', "'", " "]:
        name = name.replace(ch, "_")
    return name[:80]


def _ensure_reportlab():
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
            Image,
            PageBreak,
        )
        return {
            "A4": A4,
            "landscape": landscape,
            "colors": colors,
            "getSampleStyleSheet": getSampleStyleSheet,
            "ParagraphStyle": ParagraphStyle,
            "cm": cm,
            "SimpleDocTemplate": SimpleDocTemplate,
            "Paragraph": Paragraph,
            "Spacer": Spacer,
            "Table": Table,
            "TableStyle": TableStyle,
            "Image": Image,
            "PageBreak": PageBreak,
        }
    except Exception as exc:
        raise RuntimeError(
            "La librairie reportlab n'est pas installée. Lance : "
            "/opt/logistique-pro/.venv/bin/pip install reportlab"
        ) from exc


def _header_footer(canvas, doc):
    r = _ensure_reportlab()
    colors = r["colors"]
    cm = r["cm"]

    canvas.saveState()
    width, height = doc.pagesize

    canvas.setFillColor(colors.HexColor("#003B70"))
    canvas.rect(0, height - 1.2 * cm, width, 1.2 * cm, fill=1, stroke=0)

    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(1.2 * cm, height - 0.75 * cm, "Logistique Pro - Ville de Marly")

    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(1.2 * cm, 0.8 * cm, f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
    canvas.drawRightString(width - 1.2 * cm, 0.8 * cm, f"Page {doc.page}")

    canvas.restoreState()


def _styles():
    r = _ensure_reportlab()
    styles = r["getSampleStyleSheet"]()

    styles.add(
        r["ParagraphStyle"](
            name="TitleBlue",
            parent=styles["Title"],
            textColor=r["colors"].HexColor("#003B70"),
            fontSize=22,
            leading=26,
            spaceAfter=16,
        )
    )

    styles.add(
        r["ParagraphStyle"](
            name="Section",
            parent=styles["Heading2"],
            textColor=r["colors"].HexColor("#003B70"),
            fontSize=14,
            leading=18,
            spaceBefore=14,
            spaceAfter=8,
        )
    )

    styles.add(
        r["ParagraphStyle"](
            name="Small",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
        )
    )

    return styles


def _table_style():
    r = _ensure_reportlab()
    colors = r["colors"]

    return r["TableStyle"](
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003B70")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CCCCCC")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7FB")]),
        ]
    )


def build_batiment_pdf(batiment_id: int) -> Path:
    r = _ensure_reportlab()
    styles = _styles()

    bat = get_batiment(int(batiment_id))
    if not bat:
        raise ValueError("Bâtiment introuvable")

    filename = EXPORT_DIR / f"fiche_batiment_{batiment_id}_{_safe_filename(bat.get('nom'))}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    doc = r["SimpleDocTemplate"](
        str(filename),
        pagesize=r["A4"],
        rightMargin=1.4 * r["cm"],
        leftMargin=1.4 * r["cm"],
        topMargin=2 * r["cm"],
        bottomMargin=1.6 * r["cm"],
    )

    story = []
    story.append(r["Paragraph"]("🏢 Fiche bâtiment", styles["TitleBlue"]))
    story.append(r["Paragraph"](f"<b>{_clean(bat.get('nom'))}</b>", styles["Section"]))

    photo_path = _get_photo_path(bat)

    info_rows = [
        ["Champ", "Valeur"],
        ["Type", _clean(bat.get("type_batiment"))],
        ["Adresse", _clean(bat.get("adresse"))],
        ["Code postal", _clean(bat.get("code_postal"))],
        ["Ville", _clean(bat.get("ville"))],
        ["Surface", f"{_clean(bat.get('surface'))} m²"],
        ["Valeur estimée", f"{_clean(bat.get('valeur_estimee'))} €"],
        ["État", _clean(bat.get("etat"))],
        ["Responsable", _clean(bat.get("responsable"))],
        ["Téléphone", _clean(bat.get("telephone"))],
        ["Email", _clean(bat.get("email"))],
        ["Notes", _clean(bat.get("notes"))],
    ]

    if photo_path:
        img = r["Image"](photo_path, width=7 * r["cm"], height=5 * r["cm"])
        table = r["Table"](
            [
                [
                    img,
                    r["Table"](info_rows, colWidths=[4 * r["cm"], 7 * r["cm"]]),
                ]
            ],
            colWidths=[7.5 * r["cm"], 10 * r["cm"]],
        )
        story.append(table)
    else:
        table = r["Table"](info_rows, colWidths=[5 * r["cm"], 12 * r["cm"]])
        table.setStyle(_table_style())
        story.append(table)

    controles = load_controles()
    if not controles.empty and "batiment_id" in controles.columns:
        controles = controles[pd.to_numeric(controles["batiment_id"], errors="coerce") == int(batiment_id)]

    story.append(r["Spacer"](1, 0.5 * r["cm"]))
    story.append(r["Paragraph"]("✅ Contrôles liés", styles["Section"]))

    if controles.empty:
        story.append(r["Paragraph"]("Aucun contrôle lié.", styles["Normal"]))
    else:
        rows = [["Type", "Prestation", "Date", "Organisme", "Statut"]]
        for _, row in controles.head(20).iterrows():
            rows.append(
                [
                    _clean(row.get("type_controle")),
                    _clean(row.get("detail_controle")),
                    _format_date(row.get("date_prochain")),
                    _clean(row.get("organisme")),
                    _clean(row.get("statut")),
                ]
            )
        t = r["Table"](rows, colWidths=[3 * r["cm"], 6 * r["cm"], 3 * r["cm"], 3 * r["cm"], 2.5 * r["cm"]])
        t.setStyle(_table_style())
        story.append(t)

    entretiens = load_entretiens()
    if not entretiens.empty and "batiment_id" in entretiens.columns:
        entretiens = entretiens[pd.to_numeric(entretiens["batiment_id"], errors="coerce") == int(batiment_id)]

    story.append(r["Spacer"](1, 0.5 * r["cm"]))
    story.append(r["Paragraph"]("🛠️ Entretiens liés", styles["Section"]))

    if entretiens.empty:
        story.append(r["Paragraph"]("Aucun entretien lié.", styles["Normal"]))
    else:
        rows = [["Type", "Date intervention", "Prochain", "Fournisseur", "Statut"]]
        for _, row in entretiens.head(20).iterrows():
            rows.append(
                [
                    _clean(row.get("type_entretien")),
                    _format_date(row.get("date_entretien")),
                    _format_date(row.get("date_prochain")),
                    _clean(row.get("fournisseur")),
                    _clean(row.get("statut")),
                ]
            )
        t = r["Table"](rows, colWidths=[4 * r["cm"], 3 * r["cm"], 3 * r["cm"], 4 * r["cm"], 3 * r["cm"]])
        t.setStyle(_table_style())
        story.append(t)

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return filename


def build_batiments_list_pdf() -> Path:
    r = _ensure_reportlab()
    styles = _styles()

    df = load_batiments(include_inactive=True)
    filename = EXPORT_DIR / f"liste_batiments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    doc = r["SimpleDocTemplate"](
        str(filename),
        pagesize=r["landscape"](r["A4"]),
        rightMargin=1 * r["cm"],
        leftMargin=1 * r["cm"],
        topMargin=2 * r["cm"],
        bottomMargin=1.4 * r["cm"],
    )

    story = []
    story.append(r["Paragraph"]("🏢 Liste des bâtiments", styles["TitleBlue"]))
    story.append(r["Paragraph"](f"Base : {get_db_path()}", styles["Small"]))
    story.append(r["Spacer"](1, 0.4 * r["cm"]))

    if df.empty:
        story.append(r["Paragraph"]("Aucun bâtiment.", styles["Normal"]))
    else:
        rows = [["ID", "Nom", "Type", "Adresse", "Ville", "Surface", "État"]]
        for _, row in df.iterrows():
            rows.append(
                [
                    _clean(row.get("id")),
                    _clean(row.get("nom")),
                    _clean(row.get("type_batiment")),
                    _clean(row.get("adresse")),
                    _clean(row.get("ville")),
                    _clean(row.get("surface")),
                    _clean(row.get("etat")),
                ]
            )
        t = r["Table"](rows, colWidths=[1.5 * r["cm"], 6 * r["cm"], 4 * r["cm"], 6 * r["cm"], 3 * r["cm"], 2.5 * r["cm"], 2.5 * r["cm"]])
        t.setStyle(_table_style())
        story.append(t)

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return filename


def build_controles_pdf(alertes_only: bool = False) -> Path:
    r = _ensure_reportlab()
    styles = _styles()

    df = load_controles()

    if alertes_only and not df.empty:
        today = date.today()
        limit = today + timedelta(days=30)
        df = df.copy()
        df["_date"] = df["date_prochain"].apply(_to_date)
        df = df[df["_date"].notna()]
        df = df[(df["_date"] <= limit)]

    filename = EXPORT_DIR / f"{'alertes_' if alertes_only else ''}controles_patrimoine_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    doc = r["SimpleDocTemplate"](
        str(filename),
        pagesize=r["landscape"](r["A4"]),
        rightMargin=1 * r["cm"],
        leftMargin=1 * r["cm"],
        topMargin=2 * r["cm"],
        bottomMargin=1.4 * r["cm"],
    )

    story = []
    title = "🚨 Alertes contrôles patrimoine" if alertes_only else "✅ Contrôles patrimoine"
    story.append(r["Paragraph"](title, styles["TitleBlue"]))

    if df.empty:
        story.append(r["Paragraph"]("Aucun contrôle.", styles["Normal"]))
    else:
        rows = [["ID", "Bâtiment", "Domaine", "Prestation", "Date", "Organisme", "Statut"]]
        for _, row in df.iterrows():
            rows.append(
                [
                    _clean(row.get("id")),
                    _clean(row.get("batiment_nom")),
                    _clean(row.get("type_controle")),
                    _clean(row.get("detail_controle")),
                    _format_date(row.get("date_prochain")),
                    _clean(row.get("organisme")),
                    _clean(row.get("statut")),
                ]
            )
        t = r["Table"](rows, colWidths=[1.2 * r["cm"], 5 * r["cm"], 3 * r["cm"], 7 * r["cm"], 3 * r["cm"], 3 * r["cm"], 3 * r["cm"]])
        t.setStyle(_table_style())
        story.append(t)

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return filename


def build_entretiens_pdf(alertes_only: bool = False) -> Path:
    r = _ensure_reportlab()
    styles = _styles()

    df = load_entretiens()

    if alertes_only and not df.empty:
        today = date.today()
        limit = today + timedelta(days=30)
        df = df.copy()
        df["_date"] = df["date_prochain"].apply(_to_date)
        df = df[df["_date"].notna()]
        df = df[(df["_date"] <= limit)]

    filename = EXPORT_DIR / f"{'alertes_' if alertes_only else ''}entretiens_patrimoine_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    doc = r["SimpleDocTemplate"](
        str(filename),
        pagesize=r["landscape"](r["A4"]),
        rightMargin=1 * r["cm"],
        leftMargin=1 * r["cm"],
        topMargin=2 * r["cm"],
        bottomMargin=1.4 * r["cm"],
    )

    story = []
    title = "🚨 Alertes entretiens patrimoine" if alertes_only else "🛠️ Entretiens patrimoine"
    story.append(r["Paragraph"](title, styles["TitleBlue"]))

    if df.empty:
        story.append(r["Paragraph"]("Aucun entretien.", styles["Normal"]))
    else:
        rows = [["ID", "Bâtiment", "Type", "Date intervention", "Prochain", "Fournisseur", "Montant", "Statut"]]
        for _, row in df.iterrows():
            rows.append(
                [
                    _clean(row.get("id")),
                    _clean(row.get("batiment_nom")),
                    _clean(row.get("type_entretien")),
                    _format_date(row.get("date_entretien")),
                    _format_date(row.get("date_prochain")),
                    _clean(row.get("fournisseur")),
                    _clean(row.get("montant")),
                    _clean(row.get("statut")),
                ]
            )
        t = r["Table"](rows, colWidths=[1.2 * r["cm"], 5 * r["cm"], 4 * r["cm"], 3 * r["cm"], 3 * r["cm"], 4 * r["cm"], 2 * r["cm"], 3 * r["cm"]])
        t.setStyle(_table_style())
        story.append(t)

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return filename


def _download_pdf(path: Path, label: str):
    with open(path, "rb") as f:
        st.download_button(
            label,
            data=f.read(),
            file_name=path.name,
            mime="application/pdf",
            width="stretch",
        )


def render() -> None:
    st.markdown("### 📄 Export PDF patrimoine bâti")
    st.caption(f"Dossier exports : {EXPORT_DIR}")

    try:
        _ensure_reportlab()
    except Exception as exc:
        st.error(str(exc))
        st.code("/opt/logistique-pro/.venv/bin/pip install reportlab")
        return

    tabs = st.tabs(
        [
            "🏢 Fiche bâtiment",
            "📋 Liste bâtiments",
            "✅ Contrôles",
            "🛠️ Entretiens",
            "🚨 Alertes",
            "📁 Exports générés",
        ]
    )

    with tabs[0]:
        st.markdown("#### Générer une fiche bâtiment")

        df = load_batiments(include_inactive=True)

        if df.empty:
            st.info("Aucun bâtiment disponible.")
        else:
            options = {}
            for _, row in df.iterrows():
                label = f"#{row.get('id')} — {_clean(row.get('nom'))} — {_clean(row.get('ville'))}"
                options[label] = int(row.get("id"))

            selected = st.selectbox("Bâtiment", list(options.keys()))

            if st.button("📄 Générer la fiche PDF", width="stretch"):
                try:
                    path = build_batiment_pdf(options[selected])
                    st.success(f"PDF généré : {path}")
                    _download_pdf(path, "📥 Télécharger la fiche bâtiment")
                except Exception as exc:
                    st.error(f"Erreur génération PDF : {exc}")

    with tabs[1]:
        if st.button("📄 Générer la liste des bâtiments", width="stretch"):
            try:
                path = build_batiments_list_pdf()
                st.success(f"PDF généré : {path}")
                _download_pdf(path, "📥 Télécharger la liste bâtiments")
            except Exception as exc:
                st.error(f"Erreur génération PDF : {exc}")

    with tabs[2]:
        if st.button("📄 Générer le rapport contrôles", width="stretch"):
            try:
                path = build_controles_pdf(alertes_only=False)
                st.success(f"PDF généré : {path}")
                _download_pdf(path, "📥 Télécharger le rapport contrôles")
            except Exception as exc:
                st.error(f"Erreur génération PDF : {exc}")

    with tabs[3]:
        if st.button("📄 Générer le rapport entretiens", width="stretch"):
            try:
                path = build_entretiens_pdf(alertes_only=False)
                st.success(f"PDF généré : {path}")
                _download_pdf(path, "📥 Télécharger le rapport entretiens")
            except Exception as exc:
                st.error(f"Erreur génération PDF : {exc}")

    with tabs[4]:
        c1, c2 = st.columns(2)

        with c1:
            if st.button("🚨 PDF alertes contrôles", width="stretch"):
                try:
                    path = build_controles_pdf(alertes_only=True)
                    st.success(f"PDF généré : {path}")
                    _download_pdf(path, "📥 Télécharger alertes contrôles")
                except Exception as exc:
                    st.error(f"Erreur génération PDF : {exc}")

        with c2:
            if st.button("🚨 PDF alertes entretiens", width="stretch"):
                try:
                    path = build_entretiens_pdf(alertes_only=True)
                    st.success(f"PDF généré : {path}")
                    _download_pdf(path, "📥 Télécharger alertes entretiens")
                except Exception as exc:
                    st.error(f"Erreur génération PDF : {exc}")

    with tabs[5]:
        files = sorted(EXPORT_DIR.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)

        if not files:
            st.info("Aucun PDF généré pour le moment.")
        else:
            rows = []
            for p in files[:50]:
                rows.append(
                    {
                        "Fichier": p.name,
                        "Taille Ko": round(p.stat().st_size / 1024, 1),
                        "Date": datetime.fromtimestamp(p.stat().st_mtime).strftime("%d/%m/%Y %H:%M"),
                        "Chemin": str(p),
                    }
                )

            st.dataframe(rows, width="stretch", hide_index=True)

            selected_file = st.selectbox("Télécharger un PDF existant", [p.name for p in files[:50]])
            selected_path = EXPORT_DIR / selected_file

            _download_pdf(selected_path, "📥 Télécharger le PDF sélectionné")


def show() -> None:
    render()
