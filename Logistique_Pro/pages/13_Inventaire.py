# pages/13_Inventaire.py
"""
Page Inventaire
Vue réelle de l'inventaire global en combinant articles et outils.
"""

from io import StringIO

import pandas as pd
import streamlit as st

import utils.database as db


def _normalize_state(raw_state: str, stock: int, stock_min: int) -> str:
    raw = (raw_state or "").strip().lower()

    if raw in ["à réparer", "a reparer", "reparation", "maintenance"]:
        return "À réparer"

    if stock <= 0:
        return "Rupture"

    if stock <= stock_min:
        return "Stock bas"

    return "Bon"


def _state_class(state: str) -> str:
    mapping = {
        "Bon": "stock-ok",
        "Stock bas": "stock-low",
        "À réparer": "stock-critical",
        "Rupture": "stock-critical",
    }
    return mapping.get(state, "")


def _load_articles() -> pd.DataFrame:
    rows = db.fetch_all(
        """
        SELECT
            id,
            nom,
            categorie,
            quantite_stock,
            stock_minimum,
            etat_maintenance,
            prix_unitaire,
            photo_path,
            'Article' AS type,
            '' AS emplacement
        FROM articles
        WHERE actif = 1
        ORDER BY nom ASC
        """
    )

    if not rows:
        return pd.DataFrame(
            columns=[
                "id",
                "nom",
                "categorie",
                "quantite_stock",
                "stock_minimum",
                "etat_source",
                "prix_unitaire",
                "photo_path",
                "type",
                "emplacement",
            ]
        )

    df = pd.DataFrame([dict(row) for row in rows])
    df = df.rename(columns={"etat_maintenance": "etat_source"})
    return df


def _load_outils() -> pd.DataFrame:
    rows = db.fetch_all(
        """
        SELECT
            id,
            nom,
            categorie,
            quantite_stock,
            stock_minimum,
            etat,
            0.0 AS prix_unitaire,
            photo_path,
            'Outil' AS type,
            emplacement
        FROM outils
        WHERE actif = 1
        ORDER BY nom ASC
        """
    )

    if not rows:
        return pd.DataFrame(
            columns=[
                "id",
                "nom",
                "categorie",
                "quantite_stock",
                "stock_minimum",
                "etat_source",
                "prix_unitaire",
                "photo_path",
                "type",
                "emplacement",
            ]
        )

    df = pd.DataFrame([dict(row) for row in rows])
    df = df.rename(columns={"etat": "etat_source"})
    return df


def _build_inventory_dataframe() -> pd.DataFrame:
    df_articles = _load_articles()
    df_outils = _load_outils()

    if df_articles.empty and df_outils.empty:
        return pd.DataFrame()

    df = pd.concat([df_articles, df_outils], ignore_index=True)

    df["categorie"] = df["categorie"].fillna("Non classé")
    df["emplacement"] = df["emplacement"].fillna("")
    df["etat_source"] = df["etat_source"].fillna("")
    df["prix_unitaire"] = pd.to_numeric(df["prix_unitaire"], errors="coerce").fillna(0.0)
    df["quantite_stock"] = pd.to_numeric(df["quantite_stock"], errors="coerce").fillna(0).astype(int)
    df["stock_minimum"] = pd.to_numeric(df["stock_minimum"], errors="coerce").fillna(0).astype(int)

    df["etat"] = df.apply(
        lambda row: _normalize_state(
            row["etat_source"],
            int(row["quantite_stock"]),
            int(row["stock_minimum"]),
        ),
        axis=1,
    )

    df["valeur_estimee"] = df["quantite_stock"] * df["prix_unitaire"]

    return df


def show() -> None:
    st.title("📦 Inventaire Global")
    st.caption("Articles & Outils - Suivi complet")

    user = st.session_state.get("user")
    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    role = user.get("role")
    if role not in ["admin", "interne", "equipe_interne"]:
        st.error("Accès réservé aux administrateurs et équipes internes.")
        st.stop()

    df = _build_inventory_dataframe()

    if df.empty:
        st.info("Aucun article ou outil actif n'est enregistré dans la base de données.")
        st.stop()

    # ====================== FILTRES ======================
    col1, col2, col3 = st.columns(3)

    with col1:
        type_filter = st.selectbox("Type", ["Tous", "Article", "Outil"])

    with col2:
        categories = ["Toutes"] + sorted(df["categorie"].dropna().unique().tolist())
        categorie_filter = st.selectbox("Catégorie", categories)

    with col3:
        etat_filter = st.selectbox("État", ["Tous", "Bon", "Stock bas", "À réparer", "Rupture"])

    search = st.text_input("🔍 Rechercher par nom ou emplacement").strip()

    filtered_df = df.copy()

    if type_filter != "Tous":
        filtered_df = filtered_df[filtered_df["type"] == type_filter]

    if categorie_filter != "Toutes":
        filtered_df = filtered_df[filtered_df["categorie"] == categorie_filter]

    if etat_filter != "Tous":
        filtered_df = filtered_df[filtered_df["etat"] == etat_filter]

    if search:
        mask = (
            filtered_df["nom"].str.contains(search, case=False, na=False)
            | filtered_df["categorie"].str.contains(search, case=False, na=False)
            | filtered_df["emplacement"].str.contains(search, case=False, na=False)
        )
        filtered_df = filtered_df[mask]

    # ====================== RÉSUMÉ ======================
    st.subheader("Résumé")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Éléments affichés", len(filtered_df))
    with c2:
        st.metric("Stock bas", int((filtered_df["etat"] == "Stock bas").sum()))
    with c3:
        st.metric("À réparer", int((filtered_df["etat"] == "À réparer").sum()))
    with c4:
        total_value = float(filtered_df["valeur_estimee"].sum())
        st.metric("Valeur estimée", f"{total_value:,.2f} €".replace(",", " "))

    # ====================== TABLEAU ======================
    st.subheader("État actuel de l'inventaire")

    display_df = filtered_df[
        [
            "type",
            "nom",
            "categorie",
            "quantite_stock",
            "stock_minimum",
            "etat",
            "emplacement",
            "prix_unitaire",
            "valeur_estimee",
        ]
    ].copy()

    display_df = display_df.rename(
        columns={
            "type": "Type",
            "nom": "Nom",
            "categorie": "Catégorie",
            "quantite_stock": "Stock",
            "stock_minimum": "Stock min",
            "etat": "État",
            "emplacement": "Emplacement",
            "prix_unitaire": "Prix unitaire (€)",
            "valeur_estimee": "Valeur estimée (€)",
        }
    )

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # ====================== AFFICHAGE DÉTAILLÉ ======================
    st.subheader("Détail des éléments")

    if filtered_df.empty:
        st.warning("Aucun élément ne correspond aux filtres sélectionnés.")
    else:
        for _, row in filtered_df.iterrows():
            state_class = _state_class(row["etat"])
            with st.container(border=True):
                col_a, col_b, col_c = st.columns([3, 2, 2])

                with col_a:
                    st.markdown(f"### {row['nom']}")
                    st.write(f"**Type :** {row['type']}")
                    st.write(f"**Catégorie :** {row['categorie']}")
                    if row["emplacement"]:
                        st.write(f"**Emplacement :** {row['emplacement']}")

                with col_b:
                    st.write(f"**Stock :** {row['quantite_stock']}")
                    st.write(f"**Stock minimum :** {row['stock_minimum']}")
                    st.markdown(
                        f"**État :** <span class='{state_class}'>{row['etat']}</span>",
                        unsafe_allow_html=True,
                    )

                with col_c:
                    st.write(f"**Prix unitaire :** {row['prix_unitaire']:.2f} €")
                    st.write(f"**Valeur estimée :** {row['valeur_estimee']:.2f} €")
                    st.caption(f"Identifiant : {row['type']} #{row['id']}")

    # ====================== EXPORTS ======================
    st.subheader("📊 Rapports d'inventaire")
    col_a, col_b = st.columns(2)

    with col_a:
        csv_buffer = StringIO()
        display_df.to_csv(csv_buffer, index=False)

        st.download_button(
            "📥 Exporter inventaire complet (CSV)",
            data=csv_buffer.getvalue().encode("utf-8"),
            file_name="inventaire_global.csv",
            mime="text/csv",
            use_container_width=True,
            key="download_inventaire_csv",
        )

    with col_b:
        if st.button("📄 Générer rapport PDF", use_container_width=True):
            st.info("La génération PDF peut maintenant être branchée sur WeasyPrint.")

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
