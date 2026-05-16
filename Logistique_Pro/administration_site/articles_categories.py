import sqlite3
import streamlit as st

from administration_site.common import CATALOGUE_DB, connect_db


def ensure_tables():
    conn = connect_db(CATALOGUE_DB)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS article_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT UNIQUE NOT NULL,
            actif INTEGER DEFAULT 1,
            ordre INTEGER DEFAULT 100,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS article_sous_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT UNIQUE NOT NULL,
            actif INTEGER DEFAULT 1,
            ordre INTEGER DEFAULT 100,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def render_table(table, label):
    conn = connect_db(CATALOGUE_DB)
    cur = conn.cursor()

    rows = cur.execute(f"""
        SELECT id, nom, actif, ordre
        FROM {table}
        ORDER BY ordre, nom
    """).fetchall()

    rows = [dict(r) for r in rows]

    st.dataframe(rows, width="stretch", hide_index=True)

    # PATCH66B_DISABLED_DUPLICATE_TITLE: st.markdown(f"### ➕ Ajouter {label}")

    with st.form(f"add_{table}", clear_on_submit=True):
        nom = st.text_input("Nom", key=f"add_{table}_nom")
        ordre = st.number_input("Ordre", min_value=0, value=100, step=10, key=f"add_{table}_ordre")
        submit = st.form_submit_button("Ajouter", width="stretch")

        if submit:
            if not nom.strip():
                st.error("Nom obligatoire.")
            else:
                try:
                    cur.execute(f"""
                        INSERT INTO {table} (nom, actif, ordre, created_at)
                        VALUES (?, 1, ?, CURRENT_TIMESTAMP)
                    """, (nom.strip(), int(ordre)))
                    conn.commit()
                    st.success("Ajout effectué.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")

    if rows:
        # PATCH66B_DISABLED_DUPLICATE_TITLE: st.markdown(f"### ✏️ Modifier / supprimer {label}")

        choices = {f"{r['nom']} [id:{r['id']}]": r for r in rows}
        selected = st.selectbox("Élément", list(choices.keys()), key=f"edit_{table}_select")
        r = choices[selected]

        with st.form(f"edit_{table}"):
            new_nom = st.text_input("Nom", value=r["nom"], key=f"edit_{table}_nom")
            new_ordre = st.number_input("Ordre", min_value=0, value=int(r["ordre"] or 100), step=10, key=f"edit_{table}_ordre")
            actif = st.checkbox("Actif", value=bool(r["actif"]), key=f"edit_{table}_actif")

            save = st.form_submit_button("Modifier", width="stretch")

            if save:
                try:
                    cur.execute(f"""
                        UPDATE {table}
                        SET nom=?, ordre=?, actif=?, updated_at=CURRENT_TIMESTAMP
                        WHERE id=?
                    """, (new_nom.strip(), int(new_ordre), 1 if actif else 0, int(r["id"])))
                    conn.commit()
                    st.success("Modification enregistrée.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")

        confirm = st.checkbox("Je confirme la suppression", key=f"delete_{table}_confirm")

        if st.button("🗑️ Supprimer", disabled=not confirm, width="stretch", key=f"delete_{table}_btn"):
            try:
                cur.execute(f"DELETE FROM {table} WHERE id=?", (int(r["id"]),))
                conn.commit()
                st.success("Suppression effectuée.")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")

    conn.close()


def render():
    # PATCH76_DISABLED_ADMIN_MODULE_TITLE: st.subheader("📦 Articles / Catégories")
    st.caption("Gestion des catégories et sous-catégories du catalogue.")

    ensure_tables()

    tab_cat, tab_sub = st.tabs([
        "📁 Catégories",
        "📂 Sous-catégories",
    ])

    with tab_cat:
        render_table("article_categories", "une catégorie")

    with tab_sub:
        render_table("article_sous_categories", "une sous-catégorie")


# ============================================================
# PATCH 33 - Alias show()
# ============================================================
def show():
    render()
