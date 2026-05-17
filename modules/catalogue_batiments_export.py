# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
import html
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


APP_DIR = Path("/opt/logistique-pro")
DATA_DIR = APP_DIR / "data"
EXPORT_DIR = DATA_DIR / "exports" / "catalogue_batiments"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def _clean(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def _safe_filename(value: str) -> str:
    value = value.strip().replace("/", "_").replace("\\", "_")
    value = "".join(c for c in value if c.isalnum() or c in " _.-")
    return value or "batiment"


def _image_to_base64(path: Path) -> str:
    try:
        suffix = path.suffix.lower().replace(".", "")
        if suffix == "jpg":
            suffix = "jpeg"
        data = base64.b64encode(path.read_bytes()).decode("utf-8")
        return f"data:image/{suffix};base64,{data}"
    except Exception:
        return ""


def _row_name(row: pd.Series) -> str:
    for col in ["nom", "batiment_nom", "nom_batiment", "designation", "libelle", "name"]:
        if col in row.index:
            value = _clean(row.get(col))
            if value:
                return value
    return "Bâtiment"


def _row_details_html(row: pd.Series) -> str:
    lines = []

    for col in row.index:
        value = _clean(row.get(col))
        if not value:
            continue

        label = html.escape(str(col).replace("_", " ").capitalize())
        val = html.escape(value)

        lines.append(
            f"""
            <tr>
                <th>{label}</th>
                <td>{val}</td>
            </tr>
            """
        )

    return "\n".join(lines)


def _find_photo_generic(row: pd.Series) -> Path | None:
    """
    Recherche photo en autonome.
    Même si la page Catalogue_Batiments possède déjà find_photo(),
    ce module reste indépendant pour éviter les imports circulaires.
    """
    candidates = []

    for col in [
        "photo",
        "image",
        "image_path",
        "photo_path",
        "fichier_photo",
        "photo_file",
        "nom_photo",
        "photo_principale",
        "chemin_photo",
    ]:
        if col in row.index:
            value = _clean(row.get(col))
            if value:
                candidates.append(value)

    for col in row.index:
        low = str(col).lower()
        if "photo" in low or "image" in low:
            value = _clean(row.get(col))
            if value and value not in candidates:
                candidates.append(value)

    name = _row_name(row)
    if name:
        safe = name.lower()
        safe = safe.replace(" ", "_").replace("-", "_")
        safe = safe.replace("é", "e").replace("è", "e").replace("ê", "e")
        safe = safe.replace("à", "a").replace("ç", "c")
        candidates.extend([
            f"{safe}.jpg",
            f"{safe}.jpeg",
            f"{safe}.png",
            f"{safe}.webp",
        ])

    search_dirs = [
        DATA_DIR / "patrimoine_photos",
        DATA_DIR / "batiments_photos",
        DATA_DIR / "images",
        DATA_DIR / "photos",
        DATA_DIR / "patrimoine",
        DATA_DIR / "patrimoine_bati",
        APP_DIR / "assets" / "photos",
        APP_DIR / "assets" / "images",
        APP_DIR / "static" / "photos",
        APP_DIR / "static" / "images",
        APP_DIR / "uploads",
    ]

    for candidate in candidates:
        p = Path(candidate)

        direct_candidates = [
            p,
            APP_DIR / candidate,
            DATA_DIR / candidate,
            DATA_DIR / p.name,
        ]

        for path in direct_candidates:
            try:
                if path.exists() and path.is_file():
                    return path
            except Exception:
                pass

        filename = p.name
        if not filename:
            continue

        for folder in search_dirs:
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


def build_catalogue_html(df: pd.DataFrame) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    cards = []

    for _, row in df.iterrows():
        name = _row_name(row)
        safe_name = html.escape(name)

        photo = _find_photo_generic(row)

        if photo:
            img_src = _image_to_base64(photo)
            if img_src:
                image_html = f'<img class="photo" src="{img_src}" alt="{safe_name}">'
            else:
                image_html = '<div class="no-photo">Photo non lisible</div>'
        else:
            image_html = '<div class="no-photo">Aucune photo</div>'

        details = _row_details_html(row)

        cards.append(
            f"""
            <section class="card">
                <div class="image-zone">
                    {image_html}
                </div>
                <div class="content">
                    <h2>{safe_name}</h2>
                    <table>
                        {details}
                    </table>
                </div>
            </section>
            """
        )

    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Catalogue complet des bâtiments</title>
<style>
body {{
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 24px;
    background: #f4f7fb;
    color: #1f2937;
}}
header {{
    background: #003366;
    color: white;
    padding: 24px;
    border-radius: 16px;
    margin-bottom: 24px;
}}
header h1 {{
    margin: 0 0 8px 0;
    font-size: 30px;
}}
header p {{
    margin: 0;
    opacity: .9;
}}
.card {{
    background: white;
    border-radius: 16px;
    padding: 18px;
    margin-bottom: 20px;
    display: grid;
    grid-template-columns: 320px 1fr;
    gap: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,.08);
    page-break-inside: avoid;
}}
.photo {{
    width: 100%;
    height: 230px;
    object-fit: cover;
    border-radius: 12px;
    border: 1px solid #dbe3ef;
}}
.no-photo {{
    width: 100%;
    height: 230px;
    border-radius: 12px;
    background: #e8f1fb;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #003366;
    font-weight: bold;
    border: 1px solid #dbe3ef;
}}
h2 {{
    margin: 0 0 12px 0;
    color: #003366;
    font-size: 22px;
}}
table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}}
th {{
    width: 220px;
    text-align: left;
    background: #f1f5f9;
    color: #334155;
    padding: 7px;
    border: 1px solid #e2e8f0;
    vertical-align: top;
}}
td {{
    padding: 7px;
    border: 1px solid #e2e8f0;
    vertical-align: top;
}}
footer {{
    text-align: center;
    color: #64748b;
    margin-top: 32px;
    font-size: 12px;
}}
@media print {{
    body {{
        background: white;
        padding: 0;
    }}
    header {{
        border-radius: 0;
    }}
    .card {{
        box-shadow: none;
        border: 1px solid #ddd;
    }}
}}
</style>
</head>
<body>
<header>
    <h1>Catalogue complet des bâtiments</h1>
    <p>Export généré le {now} — {len(df)} bâtiment(s)</p>
</header>

{''.join(cards)}

<footer>
    Catalogue bâtiments — Logistique Pro
</footer>
</body>
</html>
"""


def create_catalogue_zip(df: pd.DataFrame) -> Path:
    if df is None or df.empty:
        raise RuntimeError("Aucun bâtiment à exporter.")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = EXPORT_DIR / f"catalogue_batiments_{stamp}"
    photos_dir = work_dir / "photos"

    work_dir.mkdir(parents=True, exist_ok=True)
    photos_dir.mkdir(parents=True, exist_ok=True)

    html_file = work_dir / "catalogue_batiments.html"
    html_file.write_text(build_catalogue_html(df), encoding="utf-8")

    csv_file = work_dir / "catalogue_batiments.csv"
    df.to_csv(csv_file, index=False, sep=";", encoding="utf-8-sig")

    copied = 0
    seen = set()

    for _, row in df.iterrows():
        photo = _find_photo_generic(row)
        if not photo:
            continue

        try:
            key = str(photo.resolve())
            if key in seen:
                continue
            seen.add(key)

            target_name = _safe_filename(_row_name(row)) + photo.suffix.lower()
            target = photos_dir / target_name
            shutil.copy2(photo, target)
            copied += 1
        except Exception:
            pass

    readme = work_dir / "README.txt"
    readme.write_text(
        "Catalogue bâtiments exporté depuis Logistique Pro.\n"
        "Ouvre catalogue_batiments.html dans un navigateur.\n"
        "Pour obtenir un PDF : Ctrl + P puis Imprimer en PDF.\n"
        f"Nombre de bâtiments : {len(df)}\n"
        f"Photos copiées : {copied}\n",
        encoding="utf-8",
    )

    zip_path = EXPORT_DIR / f"catalogue_batiments_complet_{stamp}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in work_dir.rglob("*"):
            z.write(p, p.relative_to(work_dir))

    return zip_path


def render_export_button(df: pd.DataFrame):
    st.markdown("### 📥 Télécharger le catalogue complet")

    st.info(
        "Génère un ZIP avec un catalogue HTML imprimable, un CSV complet et les photos trouvées. "
        "Pour faire un PDF : ouvre le HTML puis fais Ctrl + P."
    )

    if st.button("📥 Générer le catalogue complet avec photos", width="stretch", key="generate_catalogue_batiments_full"):
        try:
            zip_path = create_catalogue_zip(df)
            st.session_state["catalogue_batiments_full_zip"] = str(zip_path)
            st.success(f"Catalogue généré : {zip_path.name}")
        except Exception as exc:
            st.error(f"Erreur export catalogue : {exc}")

    zip_value = st.session_state.get("catalogue_batiments_full_zip")

    if zip_value:
        zip_path = Path(zip_value)
        if zip_path.exists():
            with open(zip_path, "rb") as f:
                st.download_button(
                    "⬇️ Télécharger le catalogue complet ZIP",
                    data=f.read(),
                    file_name=zip_path.name,
                    mime="application/zip",
                    width="stretch",
                    key="download_catalogue_batiments_full_zip",
                )
