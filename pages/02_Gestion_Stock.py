# -*- coding: utf-8 -*-
"""
Gestion Stock / Inventaire

Module activé par PATCH 39.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


PROJECT_DIR = Path("/opt/logistique-pro")
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "gestion_stock.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _columns(table: str) -> set[str]:
    conn = connect()
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return {row["name"] for row in rows}
    finally:
        conn.close()


def _add_column_if_missing(table: str, column: str, sql: str) -> None:
    if column in _columns(table):
        return

    conn = connect()
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {sql}")
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS articles_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference TEXT UNIQUE,
            designation TEXT,
            categorie TEXT,
            sous_categorie TEXT,
            fournisseur TEXT,
            emplacement TEXT,
            unite TEXT DEFAULT 'pcs',
            quantite REAL DEFAULT 0,
            seuil_minimum REAL DEFAULT 0,
            prix_unitaire REAL DEFAULT 0,
            actif INTEGER DEFAULT 1,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS mouvements_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER,
            type_mouvement TEXT,
            quantite REAL,
            quantite_avant REAL,
            quantite_apres REAL,
            motif TEXT,
            utilisateur TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(article_id) REFERENCES articles_stock(id)
        )
        """
    )

    conn.commit()
    conn.close()

    required = {
        "reference": "reference TEXT",
        "designation": "designation TEXT",
        "categorie": "categorie TEXT",
        "sous_categorie": "sous_categorie TEXT",
        "fournisseur": "fournisseur TEXT",
        "emplacement": "emplacement TEXT",
        "unite": "unite TEXT DEFAULT 'pcs'",
        "quantite": "quantite REAL DEFAULT 0",
        "seuil_minimum": "seuil_minimum REAL DEFAULT 0",
        "prix_unitaire": "prix_unitaire REAL DEFAULT 0",
        "actif": "actif INTEGER DEFAULT 1",
        "notes": "notes TEXT",
        "created_at": "created_at TEXT DEFAULT CURRENT_TIMESTAMP",
        "updated_at": "updated_at TEXT",
    }

    for col, sql in required.items():
        _add_column_if_missing("articles_stock", col, sql)

    conn = connect()
    try:
        conn.execute("UPDATE articles_stock SET actif=1 WHERE actif IS NULL")
        conn.execute("UPDATE articles_stock SET quantite=0 WHERE quantite IS NULL")
        conn.execute("UPDATE articles_stock SET seuil_minimum=0 WHERE seuil_minimum IS NULL")
        conn.execute("UPDATE articles_stock SET prix_unitaire=0 WHERE prix_unitaire IS NULL")
        conn.commit()
    finally:
        conn.close()


def load_articles(include_inactive: bool = False) -> pd.DataFrame:
    init_db()

    where = "" if include_inactive else "WHERE COALESCE(actif, 1)=1"

    conn = connect()
    try:
        return pd.read_sql_query(
            f"""
            SELECT *
            FROM articles_stock
            {where}
            ORDER BY categorie, designation, reference
            """,
            conn,
        )
    finally:
        conn.close()


def load_mouvements() -> pd.DataFrame:
    init_db()

    conn = connect()
    try:
        return pd.read_sql_query(
            """
            SELECT
                m.id,
                m.article_id,
                a.reference,
                a.designation,
                m.type_mouvement,
                m.quantite,
                m.quantite_avant,
                m.quantite_apres,
                m.motif,
                m.utilisateur,
                m.created_at
            FROM mouvements_stock m
            LEFT JOIN articles_stock a ON a.id = m.article_id
            ORDER BY m.id DESC
            """,
            conn,
        )
    finally:
        conn.close()


def add_article(data: dict[str, Any]) -> None:
    init_db()

    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO articles_stock (
                reference,
                designation,
                categorie,
                sous_categorie,
                fournisseur,
                emplacement,
                unite,
                quantite,
                seuil_minimum,
                prix_unitaire,
                actif,
                notes,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("reference"),
                data.get("designation"),
                data.get("categorie"),
                data.get("sous_categorie"),
                data.get("fournisseur"),
                data.get("emplacement"),
                data.get("unite") or "pcs",
                float(data.get("quantite") or 0),
                float(data.get("seuil_minimum") or 0),
                float(data.get("prix_unitaire") or 0),
                1,
                data.get("notes"),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def update_article(article_id: int, data: dict[str, Any]) -> None:
    init_db()

    conn = connect()
    try:
        conn.execute(
            """
            UPDATE articles_stock
            SET
                reference=?,
                designation=?,
                categorie=?,
                sous_categorie=?,
                fournisseur=?,
                emplacement=?,
                unite=?,
                quantite=?,
                seuil_minimum=?,
                prix_unitaire=?,
                actif=?,
                notes=?,
                updated_at=?
            WHERE id=?
            """,
            (
                data.get("reference"),
                data.get("designation"),
                data.get("categorie"),
                data.get("sous_categorie"),
                data.get("fournisseur"),
                data.get("emplacement"),
                data.get("unite") or "pcs",
                float(data.get("quantite") or 0),
                float(data.get("seuil_minimum") or 0),
                float(data.get("prix_unitaire") or 0),
                1 if data.get("actif", True) else 0,
                data.get("notes"),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                int(article_id),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def delete_article(article_id: int, hard_delete: bool = False) -> None:
    init_db()

    conn = connect()
    try:
        if hard_delete:
            conn.execute("DELETE FROM mouvements_stock WHERE article_id=?", (int(article_id),))
            conn.execute("DELETE FROM articles_stock WHERE id=?", (int(article_id),))
        else:
            conn.execute(
                """
                UPDATE articles_stock
                SET actif=0,
                    updated_at=?
                WHERE id=?
                """,
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), int(article_id)),
            )
        conn.commit()
    finally:
        conn.close()


def add_mouvement(article_id: int, type_mouvement: str, quantite: float, motif: str = "", utilisateur: str = "") -> None:
    init_db()

    conn = connect()
    try:
        row = conn.execute(
            "SELECT quantite FROM articles_stock WHERE id=?",
            (int(article_id),),
        ).fetchone()

        if not row:
            raise ValueError("Article introuvable")

        avant = float(row["quantite"] or 0)
        qte = float(quantite or 0)

        if type_mouvement == "Entrée":
            apres = avant + qte
        elif type_mouvement == "Sortie":
            apres = avant - qte
        elif type_mouvement == "Ajustement":
            apres = qte
        else:
            apres = avant

        conn.execute(
            """
            INSERT INTO mouvements_stock (
                article_id,
                type_mouvement,
                quantite,
                quantite_avant,
                quantite_apres,
                motif,
                utilisateur,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(article_id),
                type_mouvement,
                qte,
                avant,
                apres,
                motif,
                utilisateur,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )

        conn.execute(
            """
            UPDATE articles_stock
            SET quantite=?,
                updated_at=?
            WHERE id=?
            """,
            (
                apres,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                int(article_id),
            ),
        )

        conn.commit()
    finally:
        conn.close()


def _article_options(df: pd.DataFrame) -> dict[str, int]:
    options = {}

    for _, row in df.iterrows():
        label = f"#{row['id']} — {row.get('reference') or 'Sans ref'} — {row.get('designation') or ''}"
        options[label] = int(row["id"])

    return options


def render_dashboard() -> None:
    st.markdown("### 📊 Tableau de bord stock")

    df = load_articles(include_inactive=True)

    if df.empty:
        st.info("Aucun article enregistré.")
        return

    df["quantite"] = pd.to_numeric(df["quantite"], errors="coerce").fillna(0)
    df["seuil_minimum"] = pd.to_numeric(df["seuil_minimum"], errors="coerce").fillna(0)
    df["prix_unitaire"] = pd.to_numeric(df["prix_unitaire"], errors="coerce").fillna(0)
    df["valeur_stock"] = df["quantite"] * df["prix_unitaire"]

    actifs = int(pd.to_numeric(df["actif"], errors="coerce").fillna(0).sum()) if "actif" in df else len(df)
    alertes = df[(df["quantite"] <= df["seuil_minimum"]) & (df["actif"] == 1)]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Articles", len(df))
    c2.metric("Actifs", actifs)
    c3.metric("Alertes stock", len(alertes))
    c4.metric("Valeur stock", f"{df['valeur_stock'].sum():.2f} €")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### ⚠️ Articles sous seuil")
        if alertes.empty:
            st.success("Aucune alerte de stock.")
        else:
            cols = ["reference", "designation", "categorie", "quantite", "seuil_minimum", "emplacement"]
            st.dataframe(alertes[cols], width="stretch", hide_index=True)

    with col2:
        st.markdown("#### 📦 Répartition catégories")
        if "categorie" in df:
            cat_df = df["categorie"].fillna("Non renseigné").replace("", "Non renseigné").value_counts().reset_index()
            cat_df.columns = ["Catégorie", "Nombre"]
            st.bar_chart(cat_df.set_index("Catégorie"))


def render_liste() -> None:
    st.markdown("### 📋 Liste des articles")

    df = load_articles(include_inactive=True)

    if df.empty:
        st.info("Aucun article enregistré.")
        return

    c1, c2, c3 = st.columns(3)

    with c1:
        search = st.text_input("🔍 Recherche", key="stock_search")

    with c2:
        categories = sorted([x for x in df["categorie"].fillna("").unique().tolist() if str(x).strip()]) if "categorie" in df else []
        categorie = st.selectbox("Catégorie", ["Toutes"] + categories, key="stock_cat_filter")

    with c3:
        statut = st.selectbox("Statut", ["Tous", "Actifs", "Inactifs", "Sous seuil"], key="stock_status_filter")

    filtered = df.copy()

    if search:
        q = search.lower()
        mask = pd.Series(False, index=filtered.index)
        for col in filtered.columns:
            mask = mask | filtered[col].astype(str).str.lower().str.contains(q, na=False)
        filtered = filtered[mask]

    if categorie != "Toutes" and "categorie" in filtered.columns:
        filtered = filtered[filtered["categorie"] == categorie]

    if statut == "Actifs":
        filtered = filtered[pd.to_numeric(filtered["actif"], errors="coerce").fillna(0) == 1]
    elif statut == "Inactifs":
        filtered = filtered[pd.to_numeric(filtered["actif"], errors="coerce").fillna(0) == 0]
    elif statut == "Sous seuil":
        filtered["quantite"] = pd.to_numeric(filtered["quantite"], errors="coerce").fillna(0)
        filtered["seuil_minimum"] = pd.to_numeric(filtered["seuil_minimum"], errors="coerce").fillna(0)
        filtered = filtered[filtered["quantite"] <= filtered["seuil_minimum"]]

    cols = [
        "id",
        "reference",
        "designation",
        "categorie",
        "sous_categorie",
        "fournisseur",
        "emplacement",
        "unite",
        "quantite",
        "seuil_minimum",
        "prix_unitaire",
        "actif",
    ]
    cols = [c for c in cols if c in filtered.columns]

    st.dataframe(filtered[cols], width="stretch", hide_index=True)


def render_ajouter() -> None:
    st.markdown("### ➕ Ajouter un article")

    with st.form("stock_add_article"):
        c1, c2 = st.columns(2)

        with c1:
            reference = st.text_input("Référence *")
            designation = st.text_input("Désignation *")
            categorie = st.text_input("Catégorie")
            sous_categorie = st.text_input("Sous-catégorie")
            fournisseur = st.text_input("Fournisseur")
            emplacement = st.text_input("Emplacement")

        with c2:
            unite = st.text_input("Unité", value="pcs")
            quantite = st.number_input("Quantité initiale", min_value=0.0, step=1.0)
            seuil_minimum = st.number_input("Seuil minimum", min_value=0.0, step=1.0)
            prix_unitaire = st.number_input("Prix unitaire", min_value=0.0, step=1.0, format="%.2f")

        notes = st.text_area("Notes")
        submitted = st.form_submit_button("💾 Ajouter l'article", width="stretch")

    if submitted:
        if not reference.strip() or not designation.strip():
            st.error("La référence et la désignation sont obligatoires.")
            return

        try:
            add_article(
                {
                    "reference": reference.strip().upper(),
                    "designation": designation.strip(),
                    "categorie": categorie,
                    "sous_categorie": sous_categorie,
                    "fournisseur": fournisseur,
                    "emplacement": emplacement,
                    "unite": unite,
                    "quantite": quantite,
                    "seuil_minimum": seuil_minimum,
                    "prix_unitaire": prix_unitaire,
                    "notes": notes,
                }
            )
            st.success("Article ajouté.")
            st.rerun()
        except sqlite3.IntegrityError:
            st.error("Cette référence existe déjà.")
        except Exception as exc:
            st.error("Erreur pendant l'ajout.")
            st.exception(exc)


def render_modifier() -> None:
    st.markdown("### ✏️ Modifier / supprimer un article")

    df = load_articles(include_inactive=True)

    if df.empty:
        st.info("Aucun article disponible.")
        return

    options = _article_options(df)
    selected = st.selectbox("Article", list(options.keys()))
    article_id = options[selected]

    row = df[df["id"] == article_id].iloc[0].to_dict()

    with st.form(f"stock_edit_{article_id}"):
        c1, c2 = st.columns(2)

        with c1:
            reference = st.text_input("Référence *", value=str(row.get("reference") or ""))
            designation = st.text_input("Désignation *", value=str(row.get("designation") or ""))
            categorie = st.text_input("Catégorie", value=str(row.get("categorie") or ""))
            sous_categorie = st.text_input("Sous-catégorie", value=str(row.get("sous_categorie") or ""))
            fournisseur = st.text_input("Fournisseur", value=str(row.get("fournisseur") or ""))
            emplacement = st.text_input("Emplacement", value=str(row.get("emplacement") or ""))

        with c2:
            unite = st.text_input("Unité", value=str(row.get("unite") or "pcs"))
            quantite = st.number_input("Quantité", value=float(row.get("quantite") or 0), step=1.0)
            seuil_minimum = st.number_input("Seuil minimum", value=float(row.get("seuil_minimum") or 0), step=1.0)
            prix_unitaire = st.number_input("Prix unitaire", value=float(row.get("prix_unitaire") or 0), step=1.0, format="%.2f")
            actif = st.checkbox("Actif", value=bool(row.get("actif", 1)))

        notes = st.text_area("Notes", value=str(row.get("notes") or ""))
        submitted = st.form_submit_button("💾 Enregistrer", width="stretch")

    if submitted:
        try:
            update_article(
                article_id,
                {
                    "reference": reference.strip().upper(),
                    "designation": designation.strip(),
                    "categorie": categorie,
                    "sous_categorie": sous_categorie,
                    "fournisseur": fournisseur,
                    "emplacement": emplacement,
                    "unite": unite,
                    "quantite": quantite,
                    "seuil_minimum": seuil_minimum,
                    "prix_unitaire": prix_unitaire,
                    "actif": actif,
                    "notes": notes,
                },
            )
            st.success("Article modifié.")
            st.rerun()
        except sqlite3.IntegrityError:
            st.error("Cette référence existe déjà.")
        except Exception as exc:
            st.error("Erreur pendant la modification.")
            st.exception(exc)

    st.divider()
    st.markdown("### 🗑️ Suppression")

    c1, c2 = st.columns(2)

    with c1:
        confirm_soft = st.checkbox("Confirmer la désactivation", key=f"stock_soft_{article_id}")
        if st.button("Désactiver", disabled=not confirm_soft, width="stretch"):
            delete_article(article_id, hard_delete=False)
            st.success("Article désactivé.")
            st.rerun()

    with c2:
        confirm_hard = st.checkbox("Confirmer suppression définitive", key=f"stock_hard_{article_id}")
        if st.button("Supprimer définitivement", disabled=not confirm_hard, width="stretch"):
            delete_article(article_id, hard_delete=True)
            st.success("Article supprimé.")
            st.rerun()


def render_mouvements() -> None:
    st.markdown("### 🔁 Mouvements de stock")

    df = load_articles()

    if df.empty:
        st.info("Ajoute d'abord un article.")
        return

    options = _article_options(df)

    with st.form("stock_movement_form"):
        selected = st.selectbox("Article", list(options.keys()))
        type_mouvement = st.selectbox("Type", ["Entrée", "Sortie", "Ajustement"])
        quantite = st.number_input("Quantité", min_value=0.0, step=1.0)
        motif = st.text_input("Motif")
        utilisateur = st.text_input("Utilisateur")
        submitted = st.form_submit_button("💾 Enregistrer le mouvement", width="stretch")

    if submitted:
        try:
            add_mouvement(options[selected], type_mouvement, quantite, motif, utilisateur)
            st.success("Mouvement enregistré.")
            st.rerun()
        except Exception as exc:
            st.error("Erreur pendant le mouvement.")
            st.exception(exc)

    st.divider()
    st.markdown("#### Historique mouvements")

    mv = load_mouvements()

    if mv.empty:
        st.info("Aucun mouvement enregistré.")
    else:
        st.dataframe(mv, width="stretch", hide_index=True)


def render_import_export() -> None:
    st.markdown("### 📤 Import / 📥 Export")

    df = load_articles(include_inactive=True)

    if not df.empty:
        st.download_button(
            "📥 Exporter les articles CSV",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name="gestion_stock_articles.csv",
            mime="text/csv",
            width="stretch",
        )

    st.divider()

    st.markdown("#### Import CSV articles")

    example = pd.DataFrame(
        [
            {
                "reference": "ART-001",
                "designation": "Exemple article",
                "categorie": "Outillage",
                "sous_categorie": "",
                "fournisseur": "",
                "emplacement": "Magasin",
                "unite": "pcs",
                "quantite": 10,
                "seuil_minimum": 2,
                "prix_unitaire": 5.5,
                "notes": "",
            }
        ]
    )

    st.download_button(
        "📄 Télécharger modèle CSV",
        data=example.to_csv(index=False).encode("utf-8-sig"),
        file_name="modele_import_stock.csv",
        mime="text/csv",
    )

    uploaded = st.file_uploader("Importer un CSV", type=["csv"], key="stock_import_csv")

    if uploaded is None:
        return

    try:
        content = uploaded.getvalue().decode("utf-8-sig")
    except UnicodeDecodeError:
        content = uploaded.getvalue().decode("latin-1")

    try:
        import_df = pd.read_csv(StringIO(content), sep=None, engine="python").fillna("")
    except Exception as exc:
        st.error("Impossible de lire le CSV.")
        st.exception(exc)
        return

    st.dataframe(import_df.head(50), width="stretch", hide_index=True)

    confirm = st.checkbox("Confirmer l'import", key="stock_confirm_import")

    if st.button("Importer", disabled=not confirm, width="stretch"):
        inserted = 0
        errors = []

        for idx, row in import_df.iterrows():
            try:
                add_article(
                    {
                        "reference": str(row.get("reference") or row.get("Référence") or "").strip().upper(),
                        "designation": str(row.get("designation") or row.get("Désignation") or "").strip(),
                        "categorie": str(row.get("categorie") or ""),
                        "sous_categorie": str(row.get("sous_categorie") or ""),
                        "fournisseur": str(row.get("fournisseur") or ""),
                        "emplacement": str(row.get("emplacement") or ""),
                        "unite": str(row.get("unite") or "pcs"),
                        "quantite": float(row.get("quantite") or 0),
                        "seuil_minimum": float(row.get("seuil_minimum") or 0),
                        "prix_unitaire": float(row.get("prix_unitaire") or 0),
                        "notes": str(row.get("notes") or ""),
                    }
                )
                inserted += 1
            except Exception as exc:
                errors.append(f"Ligne {idx + 1}: {exc}")

        if inserted:
            st.success(f"{inserted} article(s) importé(s).")

        if errors:
            st.error(f"{len(errors)} erreur(s).")
            st.code("\n".join(errors))


def render() -> None:
    init_db()

    st.title("📦 Gestion Stock")
    st.caption("Gestion des articles, quantités, mouvements et alertes de stock.")

    tabs = st.tabs(
        [
            "📊 Tableau de bord",
            "📋 Articles",
            "➕ Ajouter",
            "✏️ Modifier / Supprimer",
            "🔁 Mouvements",
            "📤 Import / Export",
        ]
    )

    with tabs[0]:
        render_dashboard()

    with tabs[1]:
        render_liste()

    with tabs[2]:
        render_ajouter()

    with tabs[3]:
        render_modifier()

    with tabs[4]:
        render_mouvements()

    with tabs[5]:
        render_import_export()


def show() -> None:
    render()


def render_page() -> None:
    render()


if __name__ == "__main__":
    render()
