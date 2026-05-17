# -*- coding: utf-8 -*-
from __future__ import annotations

import math
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from modules.catalogue_batiments_pdf_export import render_pdf_export_button
from modules.batiments_documents_view import render_documents_view


PROJECT_DIR = Path("/opt/logistique-pro")
DATA_DIR = PROJECT_DIR / "data"

DB_PATH = DATA_DIR / "patrimoine_bati.db"

PHOTO_DIRS = [
    DATA_DIR / "patrimoine_photos",
    DATA_DIR / "batiments_photos",
    DATA_DIR / "images",
    PROJECT_DIR / "assets" / "photos",
    PROJECT_DIR / "assets" / "images",
]


# ============================================================
# Helpers
# ============================================================

def clean(value: Any, default: str = "") -> str:
    try:
        if value is None:
            return default
        if value != value:
            return default
        value = str(value).strip()
        if value.lower() in ("", "none", "nan", "null", "<na>", "nat"):
            return default
        return value
    except Exception:
        return default


def clean_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if value != value:
            return default
        value = str(value).strip().replace(",", ".")
        if value.lower() in ("", "none", "nan", "null", "<na>", "nat"):
            return default
        return float(value)
    except Exception:
        return default


def norm_key(value: Any) -> str:
    value = clean(value).lower()
    value = value.replace("’", "'").replace("`", "'")
    value = value.replace("-", " ")
    value = value.replace("_", " ")
    value = value.replace("é", "e").replace("è", "e").replace("ê", "e")
    value = value.replace("à", "a").replace("â", "a")
    value = value.replace("ù", "u").replace("û", "u")
    value = value.replace("î", "i").replace("ï", "i")
    value = value.replace("ç", "c")
    return " ".join(value.split())


def format_float(value: Any, suffix: str = "") -> str:
    number = clean_float(value)
    return f"{number:,.2f}".replace(",", " ").replace(".", ",") + suffix


def format_date(value: Any) -> str:
    value = clean(value)
    if not value:
        return "Non renseigné"

    try:
        dt = pd.to_datetime(value, errors="coerce", dayfirst=True)
        if pd.isna(dt):
            return value
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return value


def sort_date(value: Any) -> pd.Timestamp:
    value = clean(value)
    if not value:
        return pd.Timestamp.max

    try:
        dt = pd.to_datetime(value, errors="coerce", dayfirst=True)
        if pd.isna(dt):
            return pd.Timestamp.max
        return dt
    except Exception:
        return pd.Timestamp.max


def get_first(row: pd.Series, names: list[str], default: str = "") -> str:
    for name in names:
        if name in row.index:
            value = clean(row.get(name))
            if value:
                return value
    return default


def connect() -> sqlite3.Connection | None:
    if not DB_PATH.exists():
        return None

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(table: str) -> bool:
    conn = connect()
    if conn is None:
        return False

    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def list_tables() -> list[str]:
    conn = connect()
    if conn is None:
        return []

    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        return [r["name"] for r in rows]
    finally:
        conn.close()


def read_table(table: str) -> pd.DataFrame:
    conn = connect()
    if conn is None:
        return pd.DataFrame()

    try:
        df = pd.read_sql_query(f'SELECT * FROM "{table}"', conn)
        df.columns = [str(c).strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]

        for col in df.columns:
            df[col] = df[col].apply(clean)

        return df
    except Exception as exc:
        st.error(f"Erreur lecture table {table} : {exc}")
        return pd.DataFrame()
    finally:
        conn.close()


# ============================================================
# Chargement données
# ============================================================

def load_batiments() -> pd.DataFrame:
    candidates = [
        "batiments",
        "patrimoine_batiments_clean",
        "patrimoine_batiments",
        "batiment",
    ]

    for table in candidates:
        if table_exists(table):
            df = read_table(table)
            if not df.empty:
                if "id" not in df.columns:
                    df["id"] = range(1, len(df) + 1)
                return df

    return pd.DataFrame()


def load_controles() -> pd.DataFrame:
    candidates = [
        "controle_batiments",
        "patrimoine_controles_clean",
        "patrimoine_controles",
        "controles_batiments",
        "controles",
    ]

    for table in candidates:
        if table_exists(table):
            df = read_table(table)
            if not df.empty:
                return df

    return pd.DataFrame()


def load_entretiens() -> pd.DataFrame:
    candidates = [
        "batiment_entretiens",
        "patrimoine_entretiens_clean",
        "patrimoine_entretiens",
        "entretiens_batiments",
        "entretiens",
    ]

    for table in candidates:
        if table_exists(table):
            df = read_table(table)
            if not df.empty:
                return df

    return pd.DataFrame()


# ============================================================
# Bâtiment
# ============================================================

def get_batiment_id(row: pd.Series) -> str:
    return get_first(row, ["id", "batiment_id", "id_batiment", "patrimoine_id"], "")


def get_batiment_name(row: pd.Series) -> str:
    return get_first(
        row,
        ["nom", "batiment_nom", "nom_batiment", "designation", "libelle", "name"],
        "Sans nom",
    )


def get_batiment_type(row: pd.Series) -> str:
    return get_first(
        row,
        ["type_batiment", "type", "categorie", "catégorie", "classification"],
        "",
    )


def get_batiment_address(row: pd.Series) -> str:
    return get_first(row, ["adresse", "address", "rue", "localisation"], "")


def get_batiment_city(row: pd.Series) -> str:
    return get_first(row, ["ville", "city", "commune"], "")


def get_batiment_state(row: pd.Series) -> str:
    return get_first(row, ["etat", "état", "statut", "status"], "Bon")


def get_batiment_surface(row: pd.Series) -> float:
    for col in ["surface", "surface_m2", "surface_m²", "surface_totale"]:
        if col in row.index:
            return clean_float(row.get(col))
    return 0.0


def get_batiment_value(row: pd.Series) -> float:
    for col in ["valeur_estimee", "valeur_estimée", "valeur", "prix", "montant"]:
        if col in row.index:
            return clean_float(row.get(col))
    return 0.0


# ============================================================
# Images
# ============================================================

def find_photo(row: pd.Series) -> Path | None:
    candidates: list[str] = []

    for col in [
        "photo",
        "image",
        "image_path",
        "photo_path",
        "fichier_photo",
        "photo_file",
        "nom_photo",
        "photo_principale",
    ]:
        if col in row.index:
            value = clean(row.get(col))
            if value:
                candidates.append(value)

    name = get_batiment_name(row)
    if name:
        safe = norm_key(name).replace(" ", "_")
        candidates.extend([
            f"{safe}.jpg",
            f"{safe}.jpeg",
            f"{safe}.png",
            f"{safe}.webp",
        ])

    for candidate in candidates:
        path = Path(candidate)

        if path.is_absolute() and path.exists():
            return path

        for folder in PHOTO_DIRS:
            full = folder / candidate
            if full.exists():
                return full

    return None



def _st_image_stretch(img) -> None:
    try:
        st.image(img, width="stretch")
    except TypeError:
        st.image(img, use_container_width=True)


def render_catalogue_image(image_path) -> None:
    try:
        from PIL import Image, ImageOps

        img = Image.open(image_path).convert("RGB")

        try:
            resampling = Image.Resampling.LANCZOS
        except Exception:
            resampling = Image.LANCZOS

        # Même principe que Catalogue Véhicules : toutes les images ont le même ratio.
        img = ImageOps.fit(img, (900, 560), method=resampling)
        _st_image_stretch(img)

    except Exception:
        try:
            _st_image_stretch(str(image_path))
        except Exception:
            render_catalogue_placeholder("Image non lisible")


def render_catalogue_placeholder(text: str = "Aucune image") -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (900, 560), color=(232, 241, 251))
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
            fill=(0, 51, 102),
            font=font,
        )

        _st_image_stretch(img)

    except Exception:
        st.info(text)


def render_image(row) -> None:
    photo = find_photo(row)

    if photo:
        render_catalogue_image(photo)
    else:
        render_catalogue_placeholder("Aucune image")


def link_controls(row: pd.Series, controles: pd.DataFrame) -> pd.DataFrame:
    if controles is None or controles.empty:
        return pd.DataFrame()

    df = controles.copy()

    bid = get_batiment_id(row)
    bname = get_batiment_name(row)
    bkey = norm_key(bname)

    # Liaison principale : batiment_id
    if bid:
        for col in ["batiment_id", "id_batiment", "patrimoine_id", "id_patimoine"]:
            if col in df.columns:
                linked = df[df[col].astype(str).str.strip() == str(bid)].copy()
                if not linked.empty:
                    linked["_date_sort"] = linked.apply(control_date_sort, axis=1)
                    return linked.sort_values("_date_sort").drop(columns=["_date_sort"], errors="ignore")

    # Secours par nom
    if bkey:
        for col in ["batiment_nom", "nom_batiment", "nom_site", "batiment", "nom"]:
            if col in df.columns:
                keys = df[col].apply(norm_key)
                linked = df[keys == bkey].copy()

                if linked.empty:
                    linked = df[keys.apply(lambda x: bool(x) and (bkey in x or x in bkey))].copy()

                if not linked.empty:
                    linked["_date_sort"] = linked.apply(control_date_sort, axis=1)
                    return linked.sort_values("_date_sort").drop(columns=["_date_sort"], errors="ignore")

    return pd.DataFrame()


def control_date_sort(row: pd.Series) -> pd.Timestamp:
    for col in ["date_prochain", "date_intervention", "date_debut", "date_controle", "date_echeance"]:
        if col in row.index:
            value = clean(row.get(col))
            if value:
                return sort_date(value)
    return pd.Timestamp.max


def control_score(row: pd.Series) -> int:
    score = 0

    for col in [
        "domaine",
        "type_controle",
        "libelle_prestation",
        "detail_controle",
        "date_intervention",
        "date_debut",
        "date_controle",
        "date_prochain",
        "organisme",
        "statut",
        "reference",
        "identifiant_activite",
        "notes",
        "commentaire",
    ]:
        if col in row.index and clean(row.get(col)):
            score += 1

    return score


def render_controls(row: pd.Series, controles: pd.DataFrame) -> None:
    linked = link_controls(row, controles)

    if linked.empty:
        st.info("Aucun contrôle lié à ce bâtiment.")
        return

    linked = linked.copy()
    linked["_score"] = linked.apply(control_score, axis=1)
    linked["_date_sort"] = linked.apply(control_date_sort, axis=1)

    linked = linked.sort_values(["_score", "_date_sort"], ascending=[False, True])

    ctrl = linked.iloc[0]

    type_controle = get_first(ctrl, ["type_controle", "domaine", "type", "controle"], "Non renseigné")
    detail = get_first(ctrl, ["detail_controle", "libelle_prestation", "detail", "description"], "")
    date_controle = get_first(ctrl, ["date_controle", "date_intervention", "date_debut"], "")
    date_prochain = get_first(ctrl, ["date_prochain", "date_intervention", "date_debut", "date_echeance"], "")
    organisme = get_first(ctrl, ["organisme", "prestataire", "societe", "entreprise"], "Non renseigné")
    statut = get_first(ctrl, ["statut", "status", "etat"], "Non renseigné")
    reference = get_first(ctrl, ["reference", "ref"], "")
    identifiant = get_first(ctrl, ["identifiant_activite", "identifiant", "id_activite"], "")
    commentaire = get_first(ctrl, ["commentaire", "notes", "observation", "observations"], "")

    st.markdown("#### 📋 Contrôle prochain")

    c1, c2 = st.columns(2)

    with c1:
        st.write(f"**Type :** {type_controle}")

        if detail:
            st.write(f"**Détail :** {detail}")

        st.write(f"**Date contrôle :** {format_date(date_controle)}")
        st.write(f"**Prochain contrôle :** {format_date(date_prochain)}")

    with c2:
        st.write(f"**Organisme :** {organisme}")
        st.write(f"**Statut :** {statut}")

        if reference:
            st.write(f"**Référence :** {reference}")

        if identifiant:
            st.write(f"**Identifiant activité :** {identifiant}")

    if commentaire:
        st.write(f"**Commentaire :** {commentaire}")

    st.markdown("#### 📋 Historique des contrôles")

    priority_cols = [
        "id",
        "batiment_id",
        "nom_site",
        "ville_site",
        "domaine",
        "type_controle",
        "libelle_prestation",
        "detail_controle",
        "date_debut",
        "date_intervention",
        "date_controle",
        "date_prochain",
        "organisme",
        "statut",
        "reference",
        "identifiant_activite",
        "notes",
        "commentaire",
    ]

    display_cols = [c for c in priority_cols if c in linked.columns]

    for col in linked.columns:
        if col not in display_cols and not col.startswith("_"):
            display_cols.append(col)

    st.dataframe(
        linked.drop(columns=["_score", "_date_sort"], errors="ignore")[display_cols].head(20),
        width="stretch",
        hide_index=True,
    )


# ============================================================
# Entretiens
# ============================================================

def link_entretiens(row: pd.Series, entretiens: pd.DataFrame) -> pd.DataFrame:
    if entretiens is None or entretiens.empty:
        return pd.DataFrame()

    df = entretiens.copy()

    bid = get_batiment_id(row)
    bname = get_batiment_name(row)
    bkey = norm_key(bname)

    if bid:
        for col in ["batiment_id", "id_batiment", "patrimoine_id", "id_patimoine"]:
            if col in df.columns:
                linked = df[df[col].astype(str).str.strip() == str(bid)].copy()
                if not linked.empty:
                    return linked

    if bkey:
        for col in ["batiment_nom", "nom_batiment", "nom_site", "batiment", "nom"]:
            if col in df.columns:
                linked = df[df[col].apply(norm_key) == bkey].copy()
                if not linked.empty:
                    return linked

    return pd.DataFrame()


def render_entretiens(row: pd.Series, entretiens: pd.DataFrame) -> None:
    linked = link_entretiens(row, entretiens)

    if linked.empty:
        st.info("Aucun entretien lié.")
        return

    st.dataframe(linked.head(20), width="stretch", hide_index=True)



def inject_catalogue_batiments_image_css() -> None:
    st.markdown(
        """
        <style>
        /* Images des cartes bâtiments */
        section.main div[data-testid="stImage"] img,
        div[data-testid="stMain"] div[data-testid="stImage"] img {
            width: 100% !important;
            height: 220px !important;
            object-fit: cover !important;
            object-position: center center !important;
            border-radius: 10px !important;
            border: 1px solid #dbe3ef !important;
            background: #e8f1fb !important;
        }

        /* Conteneur image */
        section.main div[data-testid="stImage"],
        div[data-testid="stMain"] div[data-testid="stImage"] {
            width: 100% !important;
            min-height: 220px !important;
            max-height: 220px !important;
            overflow: hidden !important;
            border-radius: 10px !important;
        }

        /* Harmonise les blocs sans image si présents */
        .cat-bat-no-image,
        .no-photo,
        .no-image {
            width: 100% !important;
            height: 220px !important;
            min-height: 220px !important;
            max-height: 220px !important;
            border-radius: 10px !important;
            background: #e8f1fb !important;
            color: #003366 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            font-weight: 700 !important;
            border: 1px solid #dbe3ef !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# Carte bâtiment
# ============================================================

def render_responsable(row: pd.Series) -> None:
    responsable = get_first(row, ["responsable", "gestionnaire", "agent", "contact"], "")
    telephone = get_first(row, ["telephone", "tel", "phone"], "")
    email = get_first(row, ["email", "mail"], "")

    if not responsable and not telephone and not email:
        st.info("Aucun responsable renseigné.")
        return

    if responsable:
        st.write(f"**Responsable :** {responsable}")
    if telephone:
        st.write(f"**Téléphone :** {telephone}")
    if email:
        st.write(f"**Email :** {email}")


def render_detail(row: pd.Series) -> None:
    data = {}

    for col in row.index:
        value = clean(row.get(col))
        if value:
            data[col] = value

    if data:
        st.dataframe(pd.DataFrame([data]), width="stretch", hide_index=True)
    else:
        st.info("Aucun détail disponible.")


def render_card(row: pd.Series, controles: pd.DataFrame, entretiens: pd.DataFrame) -> None:
    render_image(row)

    st.markdown(f"### {get_batiment_name(row)}")

    st.write(f"**Type :** {get_batiment_type(row)}")
    st.write(f"**Adresse :** {get_batiment_address(row)}")
    st.write(f"**Ville :** {get_batiment_city(row)}")
    st.write(f"**Surface :** {format_float(get_batiment_surface(row), ' m²')}")
    st.write(f"**Valeur estimée :** {format_float(get_batiment_value(row), ' €')}")
    st.write(f"**État :** {get_batiment_state(row)}")

    with st.expander("👤 Responsable"):
        render_responsable(row)

    with st.expander("✅ Contrôles", expanded=False):
        render_controls(row, controles)

    with st.expander("🛠️ Entretiens"):
        render_entretiens(row, entretiens)

    with st.expander("📎 Documents", expanded=False):
        render_documents_view(
            batiment_nom=get_batiment_name(row),
            batiment_id=row.get("id", None) if hasattr(row, "get") else None,
        )

    with st.expander("🔎 Détail complet"):
        render_detail(row)


# ============================================================
# Filtres et statistiques
# ============================================================


def build_filter_options(df: pd.DataFrame, getter) -> list[str]:
    values = []

    for _, row in df.iterrows():
        value = clean(getter(row))
        if value and value not in values:
            values.append(value)

    return sorted(values)


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    search = st.session_state.get("cat_bat_search", "")
    type_filter = st.session_state.get("cat_bat_type_filter", "Tous")
    ville_filter = st.session_state.get("cat_bat_ville_filter", "Toutes")
    etat_filter = st.session_state.get("cat_bat_etat_filter", "Tous")

    filtered = df.copy()

    if search:
        q = norm_key(search)

        def match(row: pd.Series) -> bool:
            content = " ".join(clean(row.get(c)) for c in row.index)
            return q in norm_key(content)

        filtered = filtered[filtered.apply(match, axis=1)]

    if type_filter != "Tous":
        filtered = filtered[filtered.apply(lambda r: get_batiment_type(r) == type_filter, axis=1)]

    if ville_filter != "Toutes":
        filtered = filtered[filtered.apply(lambda r: get_batiment_city(r) == ville_filter, axis=1)]

    if etat_filter != "Tous":
        filtered = filtered[filtered.apply(lambda r: get_batiment_state(r) == etat_filter, axis=1)]

    return filtered


def render_filters(df: pd.DataFrame) -> None:
    type_options = ["Tous"] + build_filter_options(df, get_batiment_type)
    ville_options = ["Toutes"] + build_filter_options(df, get_batiment_city)
    etat_options = ["Tous"] + build_filter_options(df, get_batiment_state)

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.text_input(
            "🔍 Rechercher",
            placeholder="Nom, adresse, ville, type...",
            key="cat_bat_search",
        )

    with c2:
        st.selectbox(
            "Type",
            type_options,
            key="cat_bat_type_filter",
        )

    with c3:
        st.selectbox(
            "Ville",
            ville_options,
            key="cat_bat_ville_filter",
        )

    with c4:
        st.selectbox(
            "État",
            etat_options,
            key="cat_bat_etat_filter",
        )


def render_stats(df: pd.DataFrame, controles: pd.DataFrame, entretiens: pd.DataFrame) -> None:
    surfaces = 0.0
    values = 0.0

    for _, row in df.iterrows():
        surfaces += get_batiment_surface(row)
        values += get_batiment_value(row)

    st.markdown("## 📊 Vue rapide")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Bâtiments affichés", len(df))
    c2.metric("Contrôles", len(controles))
    c3.metric("Surface totale", format_float(surfaces, " m²"))
    c4.metric("Base", DB_PATH.name)


def export_csv_button(df: pd.DataFrame) -> None:
    csv = df.to_csv(index=False, sep=";").encode("utf-8-sig")

    st.download_button(
        "📥 Exporter le catalogue bâtiments CSV",
        data=csv,
        file_name="catalogue_batiments.csv",
        mime="text/csv",
        width="stretch",
    )


# ============================================================
# Affichage cartes
# ============================================================


st.divider()

_pdf_df = None
for _pdf_var_name in ["filtered", "filtered_df", "df_filtered", "batiments_filtered", "batiments", "df"]:
    _pdf_value = locals().get(_pdf_var_name)
    if _pdf_value is not None:
        _pdf_df = _pdf_value
        break

if _pdf_df is not None:
    render_pdf_export_button(_pdf_df)
else:
    st.warning("Export PDF indisponible : aucune liste de bâtiments trouvée.")


def render_cards(df: pd.DataFrame, controles: pd.DataFrame, entretiens: pd.DataFrame) -> None:
    if df.empty:
        st.info("Aucun bâtiment à afficher.")
        return

    st.markdown("## 🏢 Bâtiments disponibles")

    per_page = st.selectbox(
        "Affichage",
        [4, 8, 12, 16, 20],
        index=1,
        format_func=lambda x: f"{x} cartes",
        key="cat_bat_per_page",
    )

    total = len(df)
    pages = max(1, math.ceil(total / per_page))

    if "cat_bat_page" not in st.session_state:
        st.session_state.cat_bat_page = 1

    st.session_state.cat_bat_page = max(1, min(st.session_state.cat_bat_page, pages))

    cprev, cpage, cnext = st.columns([1, 1, 1])

    with cprev:
        if st.button("⬅️ Précédent", disabled=st.session_state.cat_bat_page <= 1, width="stretch"):
            st.session_state.cat_bat_page -= 1
            st.rerun()

    with cpage:
        st.markdown(
            f"<div style='text-align:center;font-weight:700;'>Page {st.session_state.cat_bat_page} / {pages}</div>",
            unsafe_allow_html=True,
        )

    with cnext:
        if st.button("Suivant ➡️", disabled=st.session_state.cat_bat_page >= pages, width="stretch"):
            st.session_state.cat_bat_page += 1
            st.rerun()

    start = (st.session_state.cat_bat_page - 1) * per_page
    end = start + per_page
    page_df = df.iloc[start:end]

    for i in range(0, len(page_df), 4):
        cols = st.columns(4)

        for col, (_, row) in zip(cols, page_df.iloc[i:i + 4].iterrows()):
            with col:
                render_card(row, controles, entretiens)


# ============================================================
# Page principale
# ============================================================

def render() -> None:
    inject_catalogue_batiments_image_css()

    st.title("🏢 Bâtiments de catalogue")
    st.caption("Patrimoine bâti disponible.")

    if not DB_PATH.exists():
        st.error(f"Base introuvable : {DB_PATH}")
        return

    batiments = load_batiments()
    controles = load_controles()
    entretiens = load_entretiens()

    if batiments.empty:
        st.error("Aucun bâtiment trouvé dans la base patrimoine.")
        st.write("Tables disponibles :", list_tables())
        return

    render_filters(batiments)

    filtered = apply_filters(batiments)

    render_stats(filtered, controles, entretiens)

    st.divider()

    export_csv_button(filtered)

    st.divider()

    render_pdf_export_button(filtered)



    st.divider()

    render_cards(filtered, controles, entretiens)


def show() -> None:
    return render()


def main() -> None:
    return render()


if __name__ == "__main__":
    render()
