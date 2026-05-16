# pages/Recherche_Globale.py

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


BASE_DIR = Path("/opt/logistique-pro")
DEMANDES_DB = BASE_DIR / "data" / "demandes.db"
CATALOGUE_DB = BASE_DIR / "data" / "catalogue_articles.db"


def connect(path):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def search_demandes(query):
    if not DEMANDES_DB.exists():
        return pd.DataFrame()

    conn = connect(DEMANDES_DB)
    q = f"%{query}%"

    df = pd.read_sql_query("""
        SELECT 
            id,
            demandeur,
            email,
            telephone,
            motif,
            date_debut,
            date_fin,
            date_evenement,
            lieu,
            adresse_livraison,
            articles,
            statut,
            montant_estime,
            created_at
        FROM demandes
        WHERE 
            CAST(id AS TEXT) LIKE ?
            OR COALESCE(demandeur, '') LIKE ?
            OR COALESCE(email, '') LIKE ?
            OR COALESCE(telephone, '') LIKE ?
            OR COALESCE(motif, '') LIKE ?
            OR COALESCE(lieu, '') LIKE ?
            OR COALESCE(adresse_livraison, '') LIKE ?
            OR COALESCE(articles, '') LIKE ?
            OR COALESCE(statut, '') LIKE ?
        ORDER BY created_at DESC
        LIMIT 100
    """, conn, params=[q, q, q, q, q, q, q, q, q])

    conn.close()
    return df


def search_catalogue(query, role):
    if not CATALOGUE_DB.exists():
        return pd.DataFrame()

    conn = connect(CATALOGUE_DB)
    q = f"%{query}%"

    sql = """
        SELECT 
            id,
            nom,
            categorie,
            sous_categorie,
            stock,
            stock_min,
            prix,
            prix_achat,
            prix_location,
            unite,
            emplacement,
            etat,
            notes
        FROM catalogue_articles
        WHERE (
            CAST(id AS TEXT) LIKE ?
            OR COALESCE(nom, '') LIKE ?
            OR COALESCE(categorie, '') LIKE ?
            OR COALESCE(sous_categorie, '') LIKE ?
            OR COALESCE(emplacement, '') LIKE ?
            OR COALESCE(etat, '') LIKE ?
            OR COALESCE(notes, '') LIKE ?
        )
    """

    params = [q, q, q, q, q, q, q]

    if role in ["association", "particulier", "societe", "prestataire"]:
        sql += " AND TRIM(COALESCE(sous_categorie, '')) = 'Événement'"

    sql += " ORDER BY categorie, nom LIMIT 100"

    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df


def show():
    st.title("🔎 Recherche Globale")
    st.caption("Recherche rapide dans les demandes, articles, lieux, factures et contacts")

    user = st.session_state.get("user")

    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    role = str(user.get("role", "")).lower()
    preview_role = st.session_state.get("preview_role")

    if role == "admin" and preview_role:
        role = str(preview_role).lower()

    query = st.text_input(
        "Rechercher",
        placeholder="Exemple : barnum, Dupont, facture, Marly, #10, transport...",
        key="global_search_query",
    )

    if not query or len(query.strip()) < 2:
        st.info("Saisissez au moins 2 caractères pour lancer une recherche.")
        return

    query = query.strip()

    tab1, tab2 = st.tabs(["📋 Demandes / Factures", "📦 Catalogue"])

    with tab1:
        df_dem = search_demandes(query)

        if df_dem.empty:
            st.info("Aucune demande trouvée.")
        else:
            st.success(f"{len(df_dem)} résultat(s) dans les demandes.")

            display = df_dem.rename(columns={
                "id": "N°",
                "demandeur": "Demandeur",
                "email": "Email",
                "telephone": "Téléphone",
                "motif": "Motif",
                "date_debut": "Début",
                "date_fin": "Fin",
                "date_evenement": "Date",
                "lieu": "Lieu",
                "adresse_livraison": "Livraison",
                "articles": "Articles",
                "statut": "Statut",
                "montant_estime": "Montant",
                "created_at": "Créée le",
            })

            st.dataframe(display, width="stretch", hide_index=True)

    with tab2:
        df_cat = search_catalogue(query, role)

        if df_cat.empty:
            st.info("Aucun article trouvé.")
        else:
            st.success(f"{len(df_cat)} résultat(s) dans le catalogue.")

            display = df_cat.rename(columns={
                "id": "ID",
                "nom": "Article",
                "categorie": "Catégorie",
                "sous_categorie": "Sous-catégorie",
                "stock": "Stock",
                "stock_min": "Stock min",
                "prix": "Prix facturation",
                "prix_achat": "Prix achat",
                "prix_location": "Prix location",
                "unite": "Unité",
                "emplacement": "Emplacement",
                "etat": "État",
                "notes": "Description",
            })

            st.dataframe(display, width="stretch", hide_index=True)
