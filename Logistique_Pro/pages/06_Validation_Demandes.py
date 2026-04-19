# pages/06_Validation_Demandes.py
"""
Page Validation des Demandes
Accessible uniquement aux administrateurs.

Fonctionnalités :
- consultation des vraies demandes
- filtrage / recherche
- détail des lignes
- commentaire admin
- validation / refus
- décrémentation de stock sécurisée avec stock_applied
"""

import pandas as pd
import streamlit as st

import utils.database as db


def _load_demandes_dataframe() -> pd.DataFrame:
    rows = db.get_all_demandes()
    if not rows:
        return pd.DataFrame(
            columns=[
                "id",
                "user_id",
                "username",
                "email",
                "titre",
                "motif",
                "date_evenement",
                "lieu",
                "statut",
                "montant_estime",
                "commentaire_admin",
                "stock_applied",
                "created_at",
                "updated_at",
            ]
        )
    return pd.DataFrame([dict(r) for r in rows])


def _load_demande_lignes_dataframe(demande_id: int) -> pd.DataFrame:
    rows = db.get_demande_lignes(int(demande_id))
    if not rows:
        return pd.DataFrame(columns=["article_nom", "quantite_demandee", "prix_unitaire"])
    return pd.DataFrame([dict(r) for r in rows])


def show() -> None:
    st.title("✅ Validation des Demandes")
    st.caption("Traitement administratif des demandes")

    user = st.session_state.get("user")
    if not user or user.get("role") != "admin":
        st.error("Accès réservé aux administrateurs.")
        st.stop()

    df = _load_demandes_dataframe()

    if df.empty:
        st.success("✅ Aucune demande enregistrée pour le moment.")
        st.stop()

    df["titre"] = df["titre"].fillna("")
    df["motif"] = df["motif"].fillna("")
    df["lieu"] = df["lieu"].fillna("")
    df["statut"] = df["statut"].fillna("En attente")
    df["commentaire_admin"] = df["commentaire_admin"].fillna("")
    df["montant_estime"] = pd.to_numeric(df["montant_estime"], errors="coerce").fillna(0.0)
    df["stock_applied"] = pd.to_numeric(df["stock_applied"], errors="coerce").fillna(0).astype(int)

    st.subheader("Filtres")
    col1, col2, col3 = st.columns(3)

    with col1:
        statut_filter = st.selectbox(
            "Statut",
            ["Toutes", "En attente", "Validée", "Refusée", "Terminée"],
        )

    with col2:
        search = st.text_input("Recherche").strip()

    with col3:
        sort_order = st.selectbox(
            "Tri",
            ["Plus récentes d'abord", "Plus anciennes d'abord"],
        )

    filtered_df = df.copy()

    if statut_filter != "Toutes":
        filtered_df = filtered_df[filtered_df["statut"] == statut_filter]

    if search:
        mask = (
            filtered_df["titre"].str.contains(search, case=False, na=False)
            | filtered_df["motif"].str.contains(search, case=False, na=False)
            | filtered_df["username"].str.contains(search, case=False, na=False)
            | filtered_df["email"].str.contains(search, case=False, na=False)
            | filtered_df["lieu"].str.contains(search, case=False, na=False)
        )
        filtered_df = filtered_df[mask]

    filtered_df = filtered_df.sort_values(
        by="created_at",
        ascending=(sort_order == "Plus anciennes d'abord"),
    )

    st.subheader("Liste des demandes")

    display_df = filtered_df[
        [
            "id",
            "username",
            "email",
            "titre",
            "date_evenement",
            "lieu",
            "statut",
            "montant_estime",
            "stock_applied",
            "created_at",
        ]
    ].copy()

    display_df["stock_applied"] = display_df["stock_applied"].apply(
        lambda x: "Oui" if int(x) == 1 else "Non"
    )

    display_df = display_df.rename(
        columns={
            "id": "N°",
            "username": "Demandeur",
            "email": "Email",
            "titre": "Titre",
            "date_evenement": "Date événement",
            "lieu": "Lieu",
            "statut": "Statut",
            "montant_estime": "Montant estimé (€)",
            "stock_applied": "Stock décrémenté",
            "created_at": "Créée le",
        }
    )

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    if filtered_df.empty:
        st.warning("Aucune demande ne correspond aux filtres.")
        st.stop()

    st.subheader("Traitement d'une demande")
    demande_ids = filtered_df["id"].tolist()
    selected_id = st.selectbox("Sélectionner une demande", demande_ids)

    selected_row = filtered_df[filtered_df["id"] == selected_id].iloc[0].to_dict()
    lignes_df = _load_demande_lignes_dataframe(int(selected_id))

    with st.container(border=True):
        st.markdown(f"### Demande #{selected_row['id']} — {selected_row['titre']}")
        st.write(f"**Demandeur :** {selected_row['username']} ({selected_row['email']})")
        st.write(f"**Motif :** {selected_row['motif'] or '-'}")
        st.write(f"**Date événement :** {selected_row['date_evenement'] or '-'}")
        st.write(f"**Lieu :** {selected_row['lieu'] or '-'}")
        st.write(f"**Statut actuel :** {selected_row['statut']}")
        st.write(f"**Montant estimé :** {float(selected_row['montant_estime']):.2f} €")
        st.write(f"**Commentaire admin actuel :** {selected_row['commentaire_admin'] or '-'}")
        st.write(
            f"**Stock déjà décrémenté :** {'Oui' if int(selected_row['stock_applied']) == 1 else 'Non'}"
        )
        st.caption(f"Créée le : {selected_row['created_at']}")

    st.subheader("Lignes de la demande")
    if lignes_df.empty:
        st.info("Aucune ligne enregistrée pour cette demande.")
    else:
        lignes_df["prix_unitaire"] = pd.to_numeric(lignes_df["prix_unitaire"], errors="coerce").fillna(0.0)
        lignes_df["quantite_demandee"] = pd.to_numeric(lignes_df["quantite_demandee"], errors="coerce").fillna(0).astype(int)
        lignes_df["total"] = lignes_df["quantite_demandee"] * lignes_df["prix_unitaire"]

        display_lignes = lignes_df[
            ["article_nom", "quantite_demandee", "prix_unitaire", "total"]
        ].rename(
            columns={
                "article_nom": "Article",
                "quantite_demandee": "Quantité",
                "prix_unitaire": "Prix unitaire (€)",
                "total": "Total (€)",
            }
        )

        st.dataframe(display_lignes, use_container_width=True, hide_index=True)

    st.subheader("Actions administratives")

    commentaire_admin = st.text_area(
        "Commentaire administrateur",
        value=selected_row.get("commentaire_admin", "") or "",
        height=140,
        key=f"comment_admin_{selected_id}",
    )

    stock_already_applied = int(selected_row["stock_applied"]) == 1
    demande_can_apply_stock = db.can_apply_demande_stock(int(selected_id))

    decrement_stock = st.checkbox(
        "Décrémenter le stock réel des articles lors de la validation",
        value=False,
        disabled=stock_already_applied or not demande_can_apply_stock,
        help="Désactivé si le stock a déjà été appliqué.",
    )

    if stock_already_applied:
        st.info("Le stock a déjà été décrémenté pour cette demande.")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("✅ Valider la demande", type="primary", use_container_width=True):
            try:
                apply_stock_now = decrement_stock and db.can_apply_demande_stock(int(selected_id))

                db.update_demande_status(
                    demande_id=int(selected_id),
                    statut="Validée",
                    commentaire_admin=commentaire_admin,
                )

                if apply_stock_now:
                    db.apply_demande_stock(int(selected_id))
                    st.success(f"Demande #{selected_id} validée avec décrémentation du stock.")
                else:
                    if decrement_stock:
                        st.info("Le stock n'a pas été décrémenté, car il l'était déjà.")
                    st.success(f"Demande #{selected_id} validée avec succès.")

                st.rerun()
            except Exception as e:
                st.error(f"Erreur lors de la validation : {e}")

    with col2:
        if st.button("❌ Refuser la demande", use_container_width=True):
            try:
                db.update_demande_status(
                    demande_id=int(selected_id),
                    statut="Refusée",
                    commentaire_admin=commentaire_admin,
                )
                st.warning(f"Demande #{selected_id} refusée.")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur lors du refus : {e}")

    with col3:
        if st.button("💾 Enregistrer commentaire", use_container_width=True):
            try:
                db.update_demande_status(
                    demande_id=int(selected_id),
                    statut=selected_row["statut"],
                    commentaire_admin=commentaire_admin,
                )
                st.success("Commentaire administrateur enregistré.")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur lors de l'enregistrement du commentaire : {e}")

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
