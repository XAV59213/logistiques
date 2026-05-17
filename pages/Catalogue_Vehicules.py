# -*- coding: utf-8 -*-
from __future__ import annotations

import math
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from modules.catalogue_vehicules_pdf_export import render_vehicules_pdf_export_button


PROJECT_DIR = Path("/opt/logistique-pro")
DB_PATH = PROJECT_DIR / "data" / "garage_vehicules.db"

PHOTO_DIRS = [
    PROJECT_DIR / "data" / "garage_photos",
    PROJECT_DIR / "data" / "vehicules_photos",
    PROJECT_DIR / "data" / "images",
    PROJECT_DIR / "assets" / "photos",
]

def inject_css() -> None:
    # PATCH101 : volontairement vide.
    # On évite le HTML/CSS dynamique pour ne plus déclencher les erreurs removeChild côté navigateur.
    return


def render_catalogue_image(image_path: Path | str) -> None:
    try:
        from PIL import Image, ImageOps

        img = Image.open(image_path).convert("RGB")

        try:
            resampling = Image.Resampling.LANCZOS
        except Exception:
            resampling = Image.LANCZOS

        img = ImageOps.fit(img, (900, 560), method=resampling)
        st.image(img, use_container_width=True)

    except Exception:
        st.image(str(image_path), use_container_width=True)


def render_catalogue_placeholder(text: str = "Aucune image") -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (900, 560), color=(234, 242, 251))
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
        except Exception:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]

        draw.text(
            ((900 - w) / 2, (560 - h) / 2),
            text,
            fill=(47, 93, 135),
            font=font,
        )

        st.image(img, use_container_width=True)

    except Exception:
        st.info(text)



def _clean(value: Any) -> str:
    if value is None:
        return ""
    value = str(value)
    if value.lower() in ["none", "nan", "nat"]:
        return ""
    return value.strip()


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None


@st.cache_data(ttl=30)
def load_table(table: str) -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()

    conn = _connect()
    try:
        if not _table_exists(conn, table):
            return pd.DataFrame()
        return pd.read_sql_query(f"SELECT * FROM {table} ORDER BY id DESC", conn)
    finally:
        conn.close()


def load_vehicules() -> pd.DataFrame:
    return load_table("vehicules")


def load_entretiens() -> pd.DataFrame:
    return load_table("vehicule_entretiens")





def find_photo(row: pd.Series) -> Path | None:
    candidates: list[Path] = []

    for col in ["photo", "image", "image_path", "photo_path", "fichier_photo", "photo_file"]:
        value = _clean(row.get(col))
        if value:
            candidates.append(Path(value))

    vehicule_id = _clean(row.get("id"))
    immat_raw = _clean(row.get("immatriculation"))
    immat_clean = immat_raw.replace("-", "").replace(" ", "").lower()
    nom = _clean(row.get("nom")).lower()

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
        if candidate.exists() and candidate.is_file():
            return candidate

        if not candidate.is_absolute():
            full = PROJECT_DIR / candidate
            if full.exists() and full.is_file():
                return full

    return None


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    filtered = df.copy()

    c1, c2, c3, c4 = st.columns([1.3, 1, 1, 1])

    with c1:
        search = st.text_input(
            "🔍 Rechercher",
            placeholder="Immatriculation, nom, marque, modèle...",
            key="cat_veh_search",
        )

    with c2:
        categories = ["Toutes"]
        if "categorie" in filtered.columns:
            categories += sorted([x for x in filtered["categorie"].dropna().astype(str).unique() if x and x != "None"])
        categorie = st.selectbox("Catégorie", categories, key="cat_veh_categorie")

    with c3:
        services = ["Tous"]
        if "service" in filtered.columns:
            services += sorted([x for x in filtered["service"].dropna().astype(str).unique() if x and x != "None"])
        service = st.selectbox("Service", services, key="cat_veh_service")

    with c4:
        statuts = ["Tous"]
        if "statut" in filtered.columns:
            statuts += sorted([x for x in filtered["statut"].dropna().astype(str).unique() if x and x != "None"])
        statut = st.selectbox("Statut", statuts, key="cat_veh_statut")

    if search:
        q = search.lower()
        cols = [
            c for c in [
                "immatriculation",
                "nom",
                "marque",
                "modele",
                "categorie",
                "service",
                "energie",
                "statut",
                "notes",
                "commentaire",
            ]
            if c in filtered.columns
        ]

        mask = pd.Series(False, index=filtered.index)
        for col in cols:
            mask |= filtered[col].astype(str).str.lower().str.contains(q, na=False)
        filtered = filtered[mask]

    if categorie != "Toutes" and "categorie" in filtered.columns:
        filtered = filtered[filtered["categorie"].astype(str) == categorie]

    if service != "Tous" and "service" in filtered.columns:
        filtered = filtered[filtered["service"].astype(str) == service]

    if statut != "Tous" and "statut" in filtered.columns:
        filtered = filtered[filtered["statut"].astype(str) == statut]

    return filtered


def render_stats(df: pd.DataFrame) -> None:
    st.markdown("### 📊 Vue rapide")

    total = len(df)

    actifs = total
    if "actif" in df.columns:
        actifs = int(df["actif"].fillna(0).astype(str).isin(["1", "true", "True", "Actif"]).sum())
    elif "statut" in df.columns:
        actifs = int(df["statut"].astype(str).str.lower().eq("actif").sum())

    km_total = 0
    if "kilometrage_actuel" in df.columns:
        km_total = int(pd.to_numeric(df["kilometrage_actuel"], errors="coerce").fillna(0).sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Véhicules affichés", total)
    c2.metric("Actifs", actifs)
    c3.metric("Kilométrage total", f"{km_total:,}".replace(",", " "))
    c4.metric("Base", DB_PATH.name)


def get_linked_entretiens(row: pd.Series, entretiens: pd.DataFrame) -> pd.DataFrame:
    if entretiens.empty or "id" not in row:
        return pd.DataFrame()

    for col in ["vehicule_id", "id_vehicule", "vehicle_id"]:
        if col in entretiens.columns:
            linked = entretiens[entretiens[col].astype(str) == str(row.get("id"))].copy()
            if not linked.empty:
                return linked

    immat = _clean(row.get("immatriculation"))
    for col in ["immatriculation", "vehicule_immatriculation"]:
        if col in entretiens.columns and immat:
            linked = entretiens[entretiens[col].astype(str).str.lower() == immat.lower()].copy()
            if not linked.empty:
                return linked

    return pd.DataFrame()


def render_card(row: pd.Series, entretiens: pd.DataFrame) -> None:
    immat = _clean(row.get("immatriculation"))
    nom = _clean(row.get("nom")) or _clean(row.get("modele")) or f"Véhicule #{_clean(row.get('id'))}"
    marque = _clean(row.get("marque"))
    modele = _clean(row.get("modele"))
    categorie = _clean(row.get("categorie"))
    service = _clean(row.get("service"))
    energie = _clean(row.get("energie"))
    km = _clean(row.get("kilometrage_actuel"))
    date_ct = _clean(row.get("date_ct"))
    statut = _clean(row.get("statut")) or ("Actif" if _clean(row.get("actif")) == "1" else "")
    notes = _clean(row.get("notes")) or _clean(row.get("commentaire"))

    with st.container():
        photo = find_photo(row)

        if photo:
            render_catalogue_image(photo)
        else:
            render_catalogue_placeholder("Aucune photo")

        st.markdown(f"#### {immat or nom}")
        st.write(f"**Nom :** {nom}")
        st.write(f"**Marque / modèle :** {marque} {modele}")
        st.write(f"**Catégorie :** {categorie}")
        st.write(f"**Service :** {service}")
        st.write(f"**Énergie :** {energie}")
        st.write(f"**Kilométrage :** {km}")
        st.write(f"**Contrôle technique :** {date_ct or 'Non renseigné'}")
        st.write(f"**Statut :** {statut}")

        with st.expander("📝 Notes"):
            st.write(notes or "Aucune note.")

        with st.expander("🛠️ Entretiens"):
            linked = get_linked_entretiens(row, entretiens)
            if linked.empty:
                st.info("Aucun entretien lié.")
            else:
                cols = [
                    c for c in [
                        "date_entretien",
                        "type_entretien",
                        "type",
                        "km_entretien",
                        "date_prochain",
                        "km_prochain",
                        "statut",
                        "garage",
                        "commentaire",
                    ]
                    if c in linked.columns
                ]
                st.dataframe(linked[cols].head(5), width="stretch", hide_index=True)

        with st.expander("🔎 Détail complet"):
            data = {}
            for col in row.index:
                value = _clean(row.get(col))
                if value:
                    data[col] = value

            if data:
                st.json(data)
            else:
                st.info("Aucun détail.")


def render_cards(df: pd.DataFrame, entretiens: pd.DataFrame) -> None:
    st.markdown("### 🚗 Véhicules disponibles")

    if df.empty:
        st.warning("Aucun véhicule à afficher.")
        return

    per_page_options = [4, 8, 12, 16, 24]
    per_page = st.selectbox(
        "Affichage",
        per_page_options,
        index=1,
        format_func=lambda x: f"{x} cartes",
        key="cat_veh_per_page",
    )

    total_pages = max(1, math.ceil(len(df) / per_page))

    page_key = "cat_veh_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1

    if st.session_state[page_key] > total_pages:
        st.session_state[page_key] = total_pages

    c1, c2, c3 = st.columns([1, 1, 1])

    with c1:
        if st.button("⬅️ Précédent", disabled=st.session_state[page_key] <= 1, width="stretch", key="cat_veh_prev"):
            st.session_state[page_key] -= 1

    with c2:
        st.write(f"Page {st.session_state[page_key]} / {total_pages}")

    with c3:
        if st.button("Suivant ➡️", disabled=st.session_state[page_key] >= total_pages, width="stretch", key="cat_veh_next"):
            st.session_state[page_key] += 1

    page = min(max(1, int(st.session_state[page_key])), total_pages)
    start = (page - 1) * per_page
    end = start + per_page

    rows = list(df.iloc[start:end].iterrows())

    for i in range(0, len(rows), 4):
        cols = st.columns(4)
        for col, (_, row) in zip(cols, rows[i:i + 4]):
            with col:
                render_card(row, entretiens)


def render() -> None:
    inject_css()

    st.title("🚗 Catalogue Véhicules")
    st.caption("Parc véhicules disponible.")

    if not DB_PATH.exists():
        st.error(f"Base véhicules introuvable : {DB_PATH}")
        return

    df = load_vehicules()

    if df.empty:
        st.warning("Aucun véhicule enregistré.")
        return

    entretiens = load_entretiens()
    filtered = apply_filters(df)

    render_stats(filtered)

    st.divider()

    csv = filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📥 Exporter le catalogue véhicules CSV",
        data=csv,
        file_name="catalogue_vehicules.csv",
        mime="text/csv",
        width="stretch",
        key="cat_veh_download_csv",
    )

    st.divider()

    render_vehicules_pdf_export_button(filtered)
    st.divider()
    render_cards(filtered, entretiens)


def show() -> None:
    render()


if __name__ == "__main__":
    render()
