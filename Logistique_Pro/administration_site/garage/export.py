# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date, datetime, timedelta
from io import BytesIO

import pandas as pd
import streamlit as st

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .attributions import ensure_attributions_schema
from .db import DB_PATH, init_db, load_table
from .entretiens import ensure_entretiens_schema
from .kilometrage import ensure_kilometrage_schema
from .vehicules import load_vehicules


PRIMARY = colors.HexColor("#003B71")
ACCENT = colors.HexColor("#E30613")
LIGHT_BLUE = colors.HexColor("#EAF3FB")
LIGHT_GREY = colors.HexColor("#F3F5F7")
DARK = colors.HexColor("#1F2937")


def _safe_table(table_name: str) -> pd.DataFrame:
    try:
        return load_table(table_name)
    except Exception:
        return pd.DataFrame()


def _to_date(value):
    if value is None or value == "":
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    return df.fillna("").astype(str)


def _short(value, max_len=38):
    text = "" if value is None else str(value)
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _build_alertes_df() -> pd.DataFrame:
    today = date.today()
    limit = today + timedelta(days=30)

    vehicules = pd.DataFrame(load_vehicules(include_inactive=True))
    entretiens = _safe_table("vehicule_entretiens")

    rows = []

    if not vehicules.empty:
        for _, row in vehicules.iterrows():
            actif = int(row.get("actif") or 0)
            vehicule = f"{row.get('immatriculation') or ''} - {row.get('marque') or ''} {row.get('modele') or ''}".strip()
            ct = _to_date(row.get("date_ct"))

            if actif == 0:
                rows.append(
                    {
                        "Niveau": "Info",
                        "Type": "Vehicule inactif",
                        "Vehicule": vehicule,
                        "Date": "",
                        "Message": "Vehicule inactif ou supprime",
                    }
                )

            if ct:
                if ct < today:
                    rows.append(
                        {
                            "Niveau": "Urgent",
                            "Type": "Controle technique",
                            "Vehicule": vehicule,
                            "Date": ct.isoformat(),
                            "Message": f"Depasse de {(today - ct).days} jours",
                        }
                    )
                elif ct <= limit:
                    rows.append(
                        {
                            "Niveau": "A venir",
                            "Type": "Controle technique",
                            "Vehicule": vehicule,
                            "Date": ct.isoformat(),
                            "Message": f"Dans {(ct - today).days} jours",
                        }
                    )

    if not entretiens.empty:
        veh_df = vehicules.copy()
        if not veh_df.empty:
            cols = [c for c in ["id", "immatriculation", "marque", "modele", "kilometrage_actuel"] if c in veh_df.columns]
            veh_df = veh_df[cols].rename(columns={"id": "vehicule_id"})
            entretiens = entretiens.merge(veh_df, on="vehicule_id", how="left")

        for _, row in entretiens.iterrows():
            statut = str(row.get("statut") or "")
            if statut in ["Réalisé", "Realise", "Annulé", "Annule"]:
                continue

            vehicule = f"{row.get('immatriculation') or ''} - {row.get('marque') or ''} {row.get('modele') or ''}".strip()
            date_prochain = _to_date(row.get("date_prochain"))

            if date_prochain and date_prochain <= limit:
                rows.append(
                    {
                        "Niveau": "A venir" if date_prochain >= today else "Urgent",
                        "Type": "Entretien",
                        "Vehicule": vehicule,
                        "Date": date_prochain.isoformat(),
                        "Message": row.get("type_entretien") or "Entretien",
                    }
                )

    return pd.DataFrame(rows)


def _build_excel_export() -> bytes:
    init_db()
    ensure_entretiens_schema()
    ensure_kilometrage_schema()
    ensure_attributions_schema()

    vehicules = pd.DataFrame(load_vehicules(include_inactive=True))
    kilometrages = _safe_table("vehicule_kilometrages")
    carburants = _safe_table("vehicule_carburants")
    entretiens = _safe_table("vehicule_entretiens")
    attributions = _safe_table("vehicule_attributions")
    alertes = _build_alertes_df()

    output = BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        sheets = {
            "Vehicules": vehicules,
            "Kilometrages": kilometrages,
            "Carburants": carburants,
            "Entretiens": entretiens,
            "Attributions": attributions,
            "Alertes": alertes,
        }

        for sheet_name, df in sheets.items():
            if df.empty:
                df = pd.DataFrame([{"info": "Aucune donnee"}])
            df.to_excel(writer, index=False, sheet_name=sheet_name[:31])

            worksheet = writer.sheets[sheet_name[:31]]
            for idx, column in enumerate(df.columns):
                width = max(12, min(45, max(len(str(column)), *(len(str(v)) for v in df[column].head(100).fillna("").tolist())) + 2))
                worksheet.set_column(idx, idx, width)

            worksheet.freeze_panes(1, 0)

        info = pd.DataFrame(
            [
                {"cle": "export_date", "valeur": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                {"cle": "module", "valeur": "Garage / Vehicules"},
                {"cle": "base", "valeur": str(DB_PATH)},
            ]
        )
        info.to_excel(writer, index=False, sheet_name="Infos")

    return output.getvalue()


def _make_styles():
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="CoverTitle",
            fontSize=28,
            leading=34,
            textColor=PRIMARY,
            alignment=TA_CENTER,
            spaceAfter=20,
            fontName="Helvetica-Bold",
        )
    )

    styles.add(
        ParagraphStyle(
            name="CoverSubtitle",
            fontSize=13,
            leading=18,
            textColor=DARK,
            alignment=TA_CENTER,
            spaceAfter=12,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            fontSize=16,
            leading=20,
            textColor=PRIMARY,
            fontName="Helvetica-Bold",
            spaceBefore=10,
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SmallText",
            fontSize=8,
            leading=10,
            textColor=DARK,
            alignment=TA_LEFT,
        )
    )

    return styles


def _header_footer(canvas, doc):
    canvas.saveState()

    width, height = landscape(A4)

    canvas.setFillColor(PRIMARY)
    canvas.rect(0, height - 1.2 * cm, width, 1.2 * cm, fill=True, stroke=False)

    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(1.2 * cm, height - 0.75 * cm, "Garage / Vehicules - Ville de Marly")

    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(width - 1.2 * cm, height - 0.75 * cm, datetime.now().strftime("%d/%m/%Y %H:%M"))

    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(1.2 * cm, 0.8 * cm, "Export genere automatiquement depuis Logistique Pro")
    canvas.drawRightString(width - 1.2 * cm, 0.8 * cm, f"Page {doc.page}")

    canvas.restoreState()


def _make_table(df: pd.DataFrame, columns: list[str], headers: list[str], widths=None):
    df = _clean_df(df)

    if df.empty:
        data = [["Aucune donnee"]]
        table = Table(data, colWidths=[24 * cm])
    else:
        data = [headers]

        for _, row in df.iterrows():
            data.append([_short(row.get(col, ""), 45) for col in columns])

        if widths is None:
            widths = [24 * cm / len(headers)] * len(headers)

        table = Table(data, colWidths=widths, repeatRows=1)

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("FONTSIZE", (0, 1), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    return table


def _summary_table(vehicules: pd.DataFrame, carburants: pd.DataFrame, entretiens: pd.DataFrame, attributions: pd.DataFrame, alertes: pd.DataFrame):
    total_vehicules = len(vehicules)
    actifs = int(pd.to_numeric(vehicules.get("actif", pd.Series(dtype=int)), errors="coerce").fillna(0).sum()) if not vehicules.empty else 0
    km_total = int(pd.to_numeric(vehicules.get("kilometrage_actuel", pd.Series(dtype=int)), errors="coerce").fillna(0).sum()) if not vehicules.empty else 0
    carburant_total = float(pd.to_numeric(carburants.get("montant_total", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not carburants.empty else 0
    entretiens_total = float(pd.to_numeric(entretiens.get("montant", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not entretiens.empty else 0

    data = [
        ["Indicateur", "Valeur"],
        ["Vehicules", str(total_vehicules)],
        ["Vehicules actifs", str(actifs)],
        ["Kilometrage total", f"{km_total:,}".replace(",", " ")],
        ["Carburant total", f"{carburant_total:.2f} EUR"],
        ["Entretiens total", f"{entretiens_total:.2f} EUR"],
        ["Attributions", str(len(attributions))],
        ["Alertes", str(len(alertes))],
    ]

    table = Table(data, colWidths=[9 * cm, 6 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BLUE]),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    return table


def build_pdf_export() -> bytes:
    init_db()
    ensure_entretiens_schema()
    ensure_kilometrage_schema()
    ensure_attributions_schema()

    vehicules = pd.DataFrame(load_vehicules(include_inactive=True))
    kilometrages = _safe_table("vehicule_kilometrages")
    carburants = _safe_table("vehicule_carburants")
    entretiens = _safe_table("vehicule_entretiens")
    attributions = _safe_table("vehicule_attributions")
    alertes = _build_alertes_df()

    output = BytesIO()

    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=1.2 * cm,
        leftMargin=1.2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.4 * cm,
        title="Export Garage Vehicules",
    )

    styles = _make_styles()
    story = []

    story.append(Spacer(1, 2.2 * cm))
    story.append(Paragraph("🚗 Garage / Vehicules", styles["CoverTitle"]))
    story.append(Paragraph("Rapport complet du parc automobile", styles["CoverSubtitle"]))
    story.append(Paragraph("Ville de Marly - Logistique Pro", styles["CoverSubtitle"]))
    story.append(Spacer(1, 0.8 * cm))
    story.append(_summary_table(vehicules, carburants, entretiens, attributions, alertes))
    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph(f"Base utilisee : {DB_PATH}", styles["SmallText"]))
    story.append(Paragraph(f"Date export : {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["SmallText"]))

    story.append(PageBreak())

    story.append(Paragraph("1. Liste des vehicules", styles["SectionTitle"]))
    veh_cols = ["id", "immatriculation", "nom", "marque", "modele", "categorie", "service", "energie", "kilometrage_actuel", "date_ct", "statut"]
    veh_headers = ["ID", "Immat.", "Nom", "Marque", "Modele", "Categorie", "Service", "Energie", "Km", "CT", "Statut"]
    story.append(_make_table(vehicules, veh_cols, veh_headers, widths=[1.0*cm, 2.3*cm, 2.2*cm, 2.2*cm, 2.4*cm, 2.6*cm, 2.3*cm, 2.0*cm, 1.8*cm, 2.0*cm, 2.0*cm]))

    story.append(PageBreak())

    story.append(Paragraph("2. Alertes", styles["SectionTitle"]))
    al_cols = ["Niveau", "Type", "Vehicule", "Date", "Message"]
    story.append(_make_table(alertes, al_cols, al_cols, widths=[2.2*cm, 4.0*cm, 6.5*cm, 2.5*cm, 9.0*cm]))

    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("3. Entretiens", styles["SectionTitle"]))
    ent_cols = ["id", "vehicule_id", "type_entretien", "date_entretien", "date_prochain", "km_entretien", "km_prochain", "fournisseur", "montant", "statut"]
    ent_headers = ["ID", "Veh.", "Type", "Date", "Prochain", "Km", "Km proch.", "Fournisseur", "Montant", "Statut"]
    story.append(_make_table(entretiens, ent_cols, ent_headers))

    story.append(PageBreak())

    story.append(Paragraph("4. Carburants", styles["SectionTitle"]))
    car_cols = ["id", "vehicule_id", "date_plein", "kilometrage", "type_carburant", "litres", "prix_litre", "montant_total", "station", "conducteur"]
    car_headers = ["ID", "Veh.", "Date", "Km", "Type", "Litres", "Prix/L", "Total", "Station", "Conducteur"]
    story.append(_make_table(carburants, car_cols, car_headers))

    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("5. Attributions", styles["SectionTitle"]))
    att_cols = ["id", "vehicule_id", "utilisateur", "email", "date_debut", "date_fin", "actif", "commentaire"]
    att_headers = ["ID", "Veh.", "Utilisateur", "Email", "Debut", "Fin", "Actif", "Commentaire"]
    story.append(_make_table(attributions, att_cols, att_headers))

    story.append(PageBreak())

    story.append(Paragraph("6. Kilometrages", styles["SectionTitle"]))
    km_cols = ["id", "vehicule_id", "date_releve", "kilometrage", "commentaire", "created_at"]
    km_headers = ["ID", "Veh.", "Date", "Km", "Commentaire", "Creation"]
    story.append(_make_table(kilometrages, km_cols, km_headers))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)

    return output.getvalue()


def render_export() -> None:
    st.markdown("### 📥 Export Garage")

    init_db()

    vehicules = pd.DataFrame(load_vehicules(include_inactive=True))

    if vehicules.empty:
        st.info("Aucune donnée véhicule à exporter.")
    else:
        csv_data = vehicules.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            "📥 Télécharger les véhicules en CSV",
            data=csv_data,
            file_name="garage_vehicules.csv",
            mime="text/csv",
            width="stretch",
        )

    st.divider()

    col_excel, col_pdf = st.columns(2)

    with col_excel:
        try:
            excel_data = _build_excel_export()
            excel_filename = f"garage_export_complet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

            st.download_button(
                "📊 Télécharger l'export complet Excel",
                data=excel_data,
                file_name=excel_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )

        except Exception as exc:
            st.error("Erreur pendant la génération de l'export Excel.")
            st.exception(exc)

    with col_pdf:
        try:
            pdf_data = build_pdf_export()
            pdf_filename = f"garage_rapport_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

            st.download_button(
                "📄 Télécharger le rapport PDF",
                data=pdf_data,
                file_name=pdf_filename,
                mime="application/pdf",
                width="stretch",
            )

        except Exception as exc:
            st.error("Erreur pendant la génération du PDF.")
            st.exception(exc)

# ============================================================
# Compatibilité navigation Streamlit
# Patch 104
# Le routeur peut appeler render() ou show()
# ============================================================

def render(*args, **kwargs):
    """
    Point d'entrée standard attendu par le routeur Garage.
    """
    return render_export()

def show(*args, **kwargs):
    """
    Alias de compatibilité pour les anciens routeurs.
    """
    return render(*args, **kwargs)

