# pages/Inventaire.py

import csv
import io
import math

import streamlit as st

from utils.inventaire_manager import load_inventory


ITEMS_PER_PAGE = 10


def filter_inventory(items, search, type_filter, categorie_filter, etat_filter):
    result = list(items)

    if search:
        s = search.lower().strip()

        def match(item):
            fields = [
                item.get("nom", ""),
                item.get("categorie", ""),
                item.get("sous_categorie", ""),
                item.get("emplacement", ""),
                item.get("notes", ""),
            ]
            return any(s in str(v).lower() for v in fields)

        result = [item for item in result if match(item)]

    if type_filter != "Tous":
        result = [item for item in result if item.get("type") == type_filter]

    if categorie_filter != "Toutes":
        result = [item for item in result if item.get("categorie") == categorie_filter]

    if etat_filter != "Tous":
        result = [item for item in result if item.get("etat_calcule") == etat_filter]

    return result


def to_csv(items):
    output = io.StringIO()
    fieldnames = [
        "id",
        "nom",
        "type",
        "categorie",
        "sous_categorie",
        "quantite",
        "stock_min",
        "etat_calcule",
        "emplacement",
        "notes",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=";")
    writer.writeheader()

    for item in items:
        writer.writerow({k: item.get(k, "") for k in fieldnames})

    return output.getvalue().encode("utf-8-sig")


def show():
    st.title("📦 Inventaire")
    st.caption("Inventaire réel administré depuis Administration Site")

    user = st.session_state.get("user")

    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    items = load_inventory()

    st.info("Mode réel actif : les données viennent de l’inventaire géré dans Administration Site.")

    if not items:
        st.warning("Aucun élément trouvé dans l’inventaire.")
        st.info("Va dans Administration Site → 📋 Inventaire pour ajouter tes premiers éléments.")
        return

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        search = st.text_input("🔍 Recherche", placeholder="Nom, catégorie, emplacement...")

    with col2:
        types = ["Tous"] + sorted(set(str(i.get("type", "")) for i in items if str(i.get("type", "")).strip()))
        type_filter = st.selectbox("Type", types)

    with col3:
        categories = ["Toutes"] + sorted(set(str(i.get("categorie", "")) for i in items if str(i.get("categorie", "")).strip()))
        categorie_filter = st.selectbox("Catégorie", categories)

    with col4:
        etats = ["Tous"] + sorted(set(str(i.get("etat_calcule", "")) for i in items if str(i.get("etat_calcule", "")).strip()))
        etat_filter = st.selectbox("État", etats)

    filtered = filter_inventory(items, search, type_filter, categorie_filter, etat_filter)

    st.divider()

    total_items = len(filtered)
    total_stock = sum(int(i.get("quantite") or 0) for i in filtered)
    alertes = len([i for i in filtered if i.get("etat_calcule") in ["Stock bas", "Rupture"]])

    c1, c2, c3 = st.columns(3)
    c1.metric("Éléments", total_items)
    c2.metric("Quantité totale", total_stock)
    c3.metric("Alertes stock", alertes)

    if not filtered:
        st.warning("Aucun résultat avec ces filtres.")
        return

    total_pages = max(1, math.ceil(len(filtered) / ITEMS_PER_PAGE))

    if "inventaire_page" not in st.session_state:
        st.session_state["inventaire_page"] = 1

    current_page = int(st.session_state["inventaire_page"])

    if current_page > total_pages:
        current_page = total_pages
        st.session_state["inventaire_page"] = current_page

    if current_page < 1:
        current_page = 1
        st.session_state["inventaire_page"] = current_page

    start = (current_page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_items = filtered[start:end]

    display_rows = []

    for item in page_items:
        display_rows.append({
            "ID": item.get("id", ""),
            "Nom": item.get("nom", ""),
            "Type": item.get("type", ""),
            "Catégorie": item.get("categorie", ""),
            "Sous-catégorie": item.get("sous_categorie", ""),
            "Quantité": item.get("quantite", 0),
            "Stock min": item.get("stock_min", 0),
            "État": item.get("etat_calcule", ""),
            "Emplacement": item.get("emplacement", ""),
        })

    st.dataframe(display_rows, width="stretch", hide_index=True)

    st.caption(
        f"Affichage de {start + 1} à {min(end, len(filtered))} "
        f"sur {len(filtered)} élément(s). Maximum {ITEMS_PER_PAGE} par page."
    )

    col_prev, col_page, col_next = st.columns([1, 2, 1])

    with col_prev:
        if st.button("⬅️ Précédent", disabled=current_page <= 1, width="stretch"):
            st.session_state["inventaire_page"] = current_page - 1
            st.rerun()

    with col_page:
        st.markdown(
            f"<div style='text-align:center; padding-top:0.5rem;'>"
            f"Page <b>{current_page}</b> / <b>{total_pages}</b>"
            f"</div>",
            unsafe_allow_html=True,
        )

    with col_next:
        if st.button("Suivant ➡️", disabled=current_page >= total_pages, width="stretch"):
            st.session_state["inventaire_page"] = current_page + 1
            st.rerun()

    st.divider()

    st.download_button(
        "📥 Télécharger l’inventaire filtré CSV",
        data=to_csv(filtered),
        file_name="inventaire_filtre.csv",
        mime="text/csv",
        width="stretch",
    )
