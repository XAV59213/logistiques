# pages/05_Mes_Demandes.py
"""
Page Mes Demandes
Gestion réelle des demandes utilisateur avec SQLite.
"""

from datetime import date

import pandas as pd
import streamlit as st

import utils.database as db


def _load_articles_options() -> list[dict]:
    rows = db.get_active_articles()
    items = []

    for row in rows:
        item = dict(row)
        prix = float(item.get("prix_unitaire") or 0.0)

        items.append(
            {
                "id": int(item["id"]),
                "nom": item["nom"],
                "categorie": item.get("categorie") or "Non classé",
                "stock": int(item.get("quantite_stock") or 0),
                "stock_minimum": int(item.get("stock_minimum") or 0),
                "prix_unitaire": prix,
                "label": (
                    f"{item['nom']} | {item.get('categorie') or 'Non classé'} | "
                    f"Stock: {int(item.get('quantite_stock') or 0)} | {prix:.2f} €"
                ),
            }
        )

    return items


def show() -> None:
    st.title("📋 Mes Demandes")
    st.caption("Historique et création de vos demandes")

    user = st.session_state.get("user")
    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    user_id = int(user["id"])

    tab_list, tab_new = st.tabs(["📌 Mes demandes", "➕ Nouvelle demande"])

    with tab_list:
        demandes = db.get_demandes_by_user(user_id)

        if not demandes:
            st.info("Vous n'avez encore aucune demande.")
        else:
            demandes_dict = [dict(d) for d in demandes]

            rows = []
            for d in demandes_dict:
                rows.append(
                    {
                        "N°": d["id"],
                        "Titre": d["titre"],
                        "Motif": d["motif"] or "",
                        "Date événement": d["date_evenement"] or "",
                        "Lieu": d["lieu"] or "",
                        "Statut": d["statut"],
                        "Montant estimé": f"{float(d['montant_estime'] or 0.0):.2f} €",
                        "Stock appliqué": "Oui" if int(d.get("stock_applied", 0) or 0) == 1 else "Non",
                        "Créée le": d["created_at"],
                    }
                )

            df = pd.DataFrame(rows)

            col1, col2 = st.columns(2)
            with col1:
                statut_filter = st.selectbox(
                    "Filtrer par statut",
                    ["Toutes", "En attente", "Validée", "Refusée", "Terminée"],
                )
            with col2:
                search = st.text_input("Rechercher une demande").strip()

            filtered_df = df.copy()

            if statut_filter != "Toutes":
                filtered_df = filtered_df[filtered_df["Statut"] == statut_filter]

            if search:
                mask = (
                    filtered_df["Titre"].str.contains(search, case=False, na=False)
                    | filtered_df["Motif"].str.contains(search, case=False, na=False)
                    | filtered_df["Lieu"].str.contains(search, case=False, na=False)
                )
                filtered_df = filtered_df[mask]

            st.dataframe(filtered_df, use_container_width=True, hide_index=True)

            st.subheader("Détail d'une demande")
            demande_ids = [d["id"] for d in demandes_dict]
            selected_id = st.selectbox("Sélectionner une demande", demande_ids)

            selected_demande = next(d for d in demandes_dict if int(d["id"]) == int(selected_id))
            lignes = db.get_demande_lignes(int(selected_id))

            with st.container(border=True):
                st.markdown(f"### Demande #{selected_demande['id']} - {selected_demande['titre']}")
                st.write(f"**Motif :** {selected_demande['motif'] or '-'}")
                st.write(f"**Date événement :** {selected_demande['date_evenement'] or '-'}")
                st.write(f"**Lieu :** {selected_demande['lieu'] or '-'}")
                st.write(f"**Statut :** {selected_demande['statut']}")
                st.write(f"**Montant estimé :** {float(selected_demande['montant_estime'] or 0.0):.2f} €")
                st.write(f"**Commentaire admin :** {selected_demande['commentaire_admin'] or '-'}")
                st.write(
                    f"**Stock déjà décrémenté :** {'Oui' if int(selected_demande.get('stock_applied', 0) or 0) == 1 else 'Non'}"
                )
                st.caption(f"Créée le : {selected_demande['created_at']}")

                if lignes:
                    lignes_rows = []
                    for ligne in lignes:
                        ligne = dict(ligne)
                        total = int(ligne["quantite_demandee"] or 0) * float(ligne["prix_unitaire"] or 0.0)
                        lignes_rows.append(
                            {
                                "Article": ligne["article_nom"],
                                "Quantité": int(ligne["quantite_demandee"] or 0),
                                "Prix unitaire": f"{float(ligne['prix_unitaire'] or 0.0):.2f} €",
                                "Total": f"{total:.2f} €",
                            }
                        )

                    st.dataframe(pd.DataFrame(lignes_rows), use_container_width=True, hide_index=True)
                else:
                    st.info("Aucune ligne enregistrée pour cette demande.")

    with tab_new:
        st.subheader("Créer une nouvelle demande")

        articles = _load_articles_options()

        if not articles:
            st.warning("Aucun article disponible pour créer une demande.")
        else:
            with st.form("create_demande_form", clear_on_submit=False):
                titre = st.text_input("Titre de la demande *").strip()
                motif = st.text_area("Motif / description *", height=120).strip()
                date_evenement = st.date_input("Date de l'événement", value=date.today())
                lieu = st.text_input("Lieu").strip()

                st.markdown("### Articles demandés")

                nb_lignes = st.number_input(
                    "Nombre de lignes",
                    min_value=1,
                    max_value=10,
                    value=1,
                    step=1,
                )

                lignes = []
                article_labels = [a["label"] for a in articles]

                for i in range(int(nb_lignes)):
                    st.markdown(f"**Ligne {i + 1}**")
                    col1, col2 = st.columns([4, 1])

                    with col1:
                        selected_label = st.selectbox(
                            f"Article {i + 1}",
                            article_labels,
                            key=f"demande_article_{i}",
                        )

                    with col2:
                        qty = st.number_input(
                            f"Qté {i + 1}",
                            min_value=1,
                            value=1,
                            step=1,
                            key=f"demande_qty_{i}",
                        )

                    selected_article = next(a for a in articles if a["label"] == selected_label)

                    if int(qty) > int(selected_article["stock"]):
                        st.warning(
                            f"La quantité demandée pour « {selected_article['nom']} » dépasse le stock actuel "
                            f"({selected_article['stock']})."
                        )

                    st.caption(
                        f"Prix unitaire : {selected_article['prix_unitaire']:.2f} € | "
                        f"Stock actuel : {selected_article['stock']}"
                    )

                    lignes.append(
                        {
                            "article_id": int(selected_article["id"]),
                            "article_nom": selected_article["nom"],
                            "quantite_demandee": int(qty),
                            "prix_unitaire": float(selected_article["prix_unitaire"]),
                        }
                    )

                estimated_total = sum(
                    int(l["quantite_demandee"]) * float(l["prix_unitaire"]) for l in lignes
                )
                st.info(f"Montant estimé : {estimated_total:.2f} €")

                submitted = st.form_submit_button(
                    "Créer la demande",
                    type="primary",
                    use_container_width=True,
                )

                if submitted:
                    if not titre or not motif:
                        st.error("Le titre et le motif sont obligatoires.")
                    else:
                        try:
                            demande_id = db.create_demande(
                                user_id=user_id,
                                titre=titre,
                                motif=motif,
                                date_evenement=str(date_evenement),
                                lieu=lieu,
                                lignes=lignes,
                            )
                            st.success(f"✅ Demande #{demande_id} créée avec succès.")
                            st.info("Votre demande est maintenant en attente de validation.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur lors de la création de la demande : {e}")

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
