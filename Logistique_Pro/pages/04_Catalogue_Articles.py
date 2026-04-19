# pages/04_Catalogue_Articles.py
"""
Page Catalogue Articles
Lecture réelle des articles depuis SQLite avec filtres, photos et état du stock.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

import utils.database as db
from config import PHOTOS_DIR


def _get_stock_state(stock: int, stock_min: int) -> str:
    if stock <= 0:
        return "Rupture"
    if stock <= stock_min:
        return "Stock critique"
    if stock <= stock_min * 2:
        return "Stock bas"
    return "Stock OK"


def _get_stock_state_class(state: str) -> str:
    mapping = {
        "Stock OK": "stock-ok",
        "Stock bas": "stock-low",
        "Stock critique": "stock-critical",
        "Rupture": "stock-critical",
    }
    return mapping.get(state, "")


def _load_articles() -> pd.DataFrame:
    query = """
        SELECT
            id,
            nom,
            categorie,
            sous_categorie,
            quantite_stock,
            stock_minimum,
            prix_unitaire,
            photo_path,
            description,
            etat_maintenance,
            actif
        FROM articles
        WHERE actif = 1
        ORDER BY nom ASC
    """
    rows = db.fetch_all(query)
    if not rows:
        return pd.DataFrame(
            columns=[
                "id",
                "nom",
                "categorie",
                "sous_categorie",
                "quantite_stock",
                "stock_minimum",
                "prix_unitaire",
                "photo_path",
                "description",
                "etat_maintenance",
                "actif",
            ]
        )
    return pd.DataFrame([dict(row) for row in rows])


def _resolve_image_path(photo_path: str | None) -> str | None:
    if not photo_path:
        return None

    path = Path(photo_path)
    if path.exists():
        return str(path)

    alt_path = PHOTOS_DIR / Path(photo_path).name
    if alt_path.exists():
        return str(alt_path)

    return None


def show() -> None:
    st.title("📦 Catalogue Articles")
    st.caption("Logistique Événements - Stock en temps réel")

    user = st.session_state.get("user")
    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    role = user.get("role", "")
    is_admin = role == "admin"

    df = _load_articles()

    if df.empty:
        st.info("Aucun article actif n'est enregistré dans la base de données.")
        st.stop()

    df["categorie"] = df["categorie"].fillna("Non classé")
    df["sous_categorie"] = df["sous_categorie"].fillna("")
    df["description"] = df["description"].fillna("")
    df["etat_maintenance"] = df["etat_maintenance"].fillna("Non renseigné")
    df["prix_unitaire"] = pd.to_numeric(df["prix_unitaire"], errors="coerce").fillna(0.0)
    df["quantite_stock"] = pd.to_numeric(df["quantite_stock"], errors="coerce").fillna(0).astype(int)
    df["stock_minimum"] = pd.to_numeric(df["stock_minimum"], errors="coerce").fillna(0).astype(int)

    df["etat_stock"] = df.apply(
        lambda row: _get_stock_state(int(row["quantite_stock"]), int(row["stock_minimum"])),
        axis=1,
    )

    # ====================== FILTRES ======================
    col1, col2, col3 = st.columns(3)

    with col1:
        search = st.text_input("🔍 Rechercher un article").strip()

    with col2:
        categories = ["Toutes"] + sorted(df["categorie"].dropna().unique().tolist())
        categorie = st.selectbox("Catégorie", categories)

    with col3:
        stock_filter = st.selectbox(
            "Niveau de stock",
            ["Tous", "Stock OK", "Stock bas", "Stock critique", "Rupture"]
        )

    filtered_df = df.copy()

    if search:
        mask = (
            filtered_df["nom"].str.contains(search, case=False, na=False)
            | filtered_df["categorie"].str.contains(search, case=False, na=False)
            | filtered_df["sous_categorie"].str.contains(search, case=False, na=False)
            | filtered_df["description"].str.contains(search, case=False, na=False)
        )
        filtered_df = filtered_df[mask]

    if categorie != "Toutes":
        filtered_df = filtered_df[filtered_df["categorie"] == categorie]

    if stock_filter != "Tous":
        filtered_df = filtered_df[filtered_df["etat_stock"] == stock_filter]

    # ====================== RÉSUMÉ ======================
    st.subheader("Vue d'ensemble")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Articles affichés", len(filtered_df))
    with c2:
        st.metric("Stock critique", int((filtered_df["etat_stock"] == "Stock critique").sum()))
    with c3:
        st.metric("Ruptures", int((filtered_df["etat_stock"] == "Rupture").sum()))
    with c4:
        st.metric("Valeur stock affiché", f"{(filtered_df['quantite_stock'] * filtered_df['prix_unitaire']).sum():,.2f} €".replace(",", " "))

    st.markdown("---")
    st.subheader("Articles disponibles")

    if filtered_df.empty:
        st.warning("Aucun article ne correspond aux filtres sélectionnés.")
        st.stop()

    for _, row in filtered_df.iterrows():
        stock_state = row["etat_stock"]
        stock_class = _get_stock_state_class(stock_state)
        image_path = _resolve_image_path(row["photo_path"])

        with st.container(border=True):
            col_a, col_b = st.columns([1, 4])

            with col_a:
                if image_path:
                    st.image(image_path, width=130)
                else:
                    st.image("https://via.placeholder.com/150?text=Article", width=130)

            with col_b:
                st.markdown(f"### {row['nom']}")
                st.write(f"**Catégorie :** {row['categorie']}")
                if row["sous_categorie"]:
                    st.write(f"**Sous-catégorie :** {row['sous_categorie']}")

                st.markdown(
                    f"**Stock :** {row['quantite_stock']} unités "
                    f"(minimum {row['stock_minimum']})"
                )
                st.markdown(
                    f"**État du stock :** "
                    f"<span class='{stock_class}'>{stock_state}</span>",
                    unsafe_allow_html=True,
                )
                st.write(f"**Prix unitaire :** {row['prix_unitaire']:.2f} €")
                st.write(f"**État maintenance :** {row['etat_maintenance']}")

                if row["description"]:
                    st.write(f"**Description :** {row['description']}")

                if is_admin:
                    admin_col1, admin_col2, admin_col3 = st.columns([1, 1, 2])

                    with admin_col1:
                        if st.button("✏️ Modifier", key=f"edit_{row['id']}", use_container_width=True):
                            st.info(
                                f"Modification de « {row['nom']} » à connecter à un formulaire admin."
                            )

                    with admin_col2:
                        if st.button("🗑️ Désactiver", key=f"disable_{row['id']}", use_container_width=True):
                            try:
                                db.execute_query(
                                    "UPDATE articles SET actif = 0 WHERE id = ?",
                                    (int(row["id"]),)
                                )
                                st.success(f"Article « {row['nom']} » désactivé.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erreur lors de la désactivation : {e}")

                    with admin_col3:
                        stock_value = int(row["quantite_stock"]) * float(row["prix_unitaire"])
                        st.caption(f"Valeur estimée du stock : {stock_value:.2f} €")

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
