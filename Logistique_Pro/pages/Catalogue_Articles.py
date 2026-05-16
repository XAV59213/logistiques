import sqlite3
from pathlib import Path
from datetime import datetime
import uuid
import pandas as pd
import streamlit as st

from utils.catalogue_settings import (
    ensure_catalogue_settings,
    load_categories,
    load_sous_categories,
)

BASE_DIR = Path("/opt/logistique-pro")
DB_PATH = BASE_DIR / "data" / "catalogue_articles.db"
FOURNISSEURS_DB = BASE_DIR / "data" / "fournisseurs.db"
UPLOAD_DIR = BASE_DIR / "assets/photos/catalogue"
DEFAULT_IMAGE = BASE_DIR / "assets/photos/default/mairie.png"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_IMAGE.parent.mkdir(parents=True, exist_ok=True)


def get_effective_role(user):
    role = str(user.get("role", "")).lower()
    preview_role = st.session_state.get("preview_role")
    if role == "admin" and preview_role:
        return str(preview_role).lower()
    return role


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS catalogue_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            categorie TEXT DEFAULT 'Divers',
            sous_categorie TEXT DEFAULT 'Standard',
            stock INTEGER DEFAULT 0,
            stock_min INTEGER DEFAULT 0,
            prix REAL DEFAULT 0,
            unite TEXT DEFAULT 'unité',
            emplacement TEXT,
            etat TEXT DEFAULT 'OK',
            image_path TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        )
    """)

    cur.execute("PRAGMA table_info(catalogue_articles)")
    cols = [r["name"] for r in cur.fetchall()]

    needed = {
        "sous_categorie": "TEXT DEFAULT 'Standard'",
        "image_path": "TEXT",
        "emplacement": "TEXT",
        "notes": "TEXT",
        "updated_at": "TEXT",
        "prix_achat": "REAL DEFAULT 0",
        "prix_location": "REAL DEFAULT 0",
        "fournisseur_id": "INTEGER",
    }

    for col, typ in needed.items():
        if col not in cols:
            cur.execute(f"ALTER TABLE catalogue_articles ADD COLUMN {col} {typ}")

    conn.commit()
    conn.close()
    ensure_catalogue_settings()


def compute_etat(stock, stock_min):
    if int(stock) <= 0:
        return "Critique"
    if int(stock) <= int(stock_min):
        return "Bas"
    return "OK"


def save_image(file):
    if file is None:
        return ""

    ext = Path(file.name).suffix.lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        return ""

    name = f"{uuid.uuid4().hex}{ext}"
    path = UPLOAD_DIR / name

    with open(path, "wb") as f:
        f.write(file.getbuffer())

    return str(path.relative_to(BASE_DIR))


def show_image(image_path):
    if image_path:
        path = BASE_DIR / str(image_path)
        if path.exists():
            st.image(str(path), width=90)
            return

    if DEFAULT_IMAGE.exists():
        st.image(str(DEFAULT_IMAGE), width=90)
    else:
        st.markdown("🏛️")


def load_articles(search="", categorie="Toutes", sous_categorie="Toutes", stock_filter="Tous", role=""):
    if role in ["equipe_batiment", "batiment", "agent_batiment"]:
        categorie = "Bâtiment"

    conn = get_connection()

    query = """
        SELECT id, nom, categorie, sous_categorie, stock, stock_min, prix,
               prix_achat, prix_location, fournisseur_id,
               unite, emplacement, etat, image_path, notes
        FROM catalogue_articles
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND nom LIKE ?"
        params.append(f"%{search}%")

    if categorie != "Toutes":
        query += " AND categorie = ?"
        params.append(categorie)

    if sous_categorie != "Toutes":
        query += " AND TRIM(COALESCE(sous_categorie, '')) = ?"
        params.append(sous_categorie)

    if stock_filter == "Stock OK":
        query += " AND etat = 'OK'"
    elif stock_filter == "Stock bas":
        query += " AND etat = 'Bas'"
    elif stock_filter == "Stock critique":
        query += " AND etat = 'Critique'"

    # VERROU PROFILS PUBLICS
    if role in ["association", "particulier", "societe", "prestataire"]:
        query += " AND TRIM(COALESCE(sous_categorie, '')) = 'Événement'"

    query += " ORDER BY categorie, nom"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df



def load_fournisseurs():
    if not FOURNISSEURS_DB.exists():
        return []

    try:
        conn = sqlite3.connect(FOURNISSEURS_DB)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id, nom FROM fournisseurs ORDER BY nom").fetchall()
        conn.close()
        return [(0, "Aucun fournisseur")] + [(int(r["id"]), r["nom"]) for r in rows]
    except Exception:
        return [(0, "Aucun fournisseur")]


def fournisseur_name(fournisseur_id):
    if not fournisseur_id or not FOURNISSEURS_DB.exists():
        return "-"

    try:
        conn = sqlite3.connect(FOURNISSEURS_DB)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT nom FROM fournisseurs WHERE id = ?",
            (int(fournisseur_id),)
        ).fetchone()
        conn.close()
        return row["nom"] if row else "-"
    except Exception:
        return "-"



def add_article(data):
    conn = get_connection()
    cur = conn.cursor()
    etat = compute_etat(data["stock"], data["stock_min"])

    cur.execute("""
        INSERT INTO catalogue_articles
        (nom, categorie, sous_categorie, stock, stock_min, prix, prix_achat, prix_location, fournisseur_id, unite, emplacement, etat, image_path, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["nom"], data["categorie"], data["sous_categorie"],
        data["stock"], data["stock_min"], data["prix"], data["prix_achat"], data["prix_location"], data.get("fournisseur_id", 0), data["unite"],
        data["emplacement"], etat, data["image_path"], data["notes"]
    ))

    conn.commit()
    conn.close()


def update_article(article_id, data):
    conn = get_connection()
    cur = conn.cursor()
    etat = compute_etat(data["stock"], data["stock_min"])

    cur.execute("""
        UPDATE catalogue_articles
        SET nom=?, categorie=?, sous_categorie=?, stock=?, stock_min=?, prix=?, prix_achat=?, prix_location=?, fournisseur_id=?,
            unite=?, emplacement=?, etat=?, image_path=?, notes=?, updated_at=?
        WHERE id=?
    """, (
        data["nom"], data["categorie"], data["sous_categorie"],
        data["stock"], data["stock_min"], data["prix"], data["prix_achat"], data["prix_location"], data.get("fournisseur_id", 0), data["unite"],
        data["emplacement"], etat, data["image_path"], data["notes"],
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        article_id
    ))

    conn.commit()
    conn.close()


def delete_article(article_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM catalogue_articles WHERE id=?", (article_id,))
    conn.commit()
    conn.close()


def stock_badge(etat):
    color = {"OK": "#16a34a", "Bas": "#f59e0b", "Critique": "#dc2626"}.get(etat, "#6b7280")
    return f"<span style='background:{color};color:white;padding:4px 10px;border-radius:999px'>{etat}</span>"



def fournisseur_details(fournisseur_id):
    if not fournisseur_id or not FOURNISSEURS_DB.exists():
        return None

    try:
        conn = sqlite3.connect(FOURNISSEURS_DB)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT nom, adresse, code_postal, ville, email, telephone, referent, notes, logo_path
            FROM fournisseurs
            WHERE id = ?
            """,
            (int(fournisseur_id),)
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None



def show():
    ensure_db()

    st.title("📦 Catalogue Articles")
    st.caption("Stock et matériel disponible")

    user = st.session_state.get("user")
    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    role = get_effective_role(user)
    is_admin = role == "admin"

    categories_form = load_categories()
    sous_categories_form = load_sous_categories()
    categories = ["Toutes"] + categories_form
    sous_categories = ["Toutes"] + sous_categories_form
    fournisseurs = load_fournisseurs()
    fournisseurs_ids = [f[0] for f in fournisseurs]
    fournisseurs_labels = {f[0]: f[1] for f in fournisseurs}

    if role in ["association", "particulier", "societe", "prestataire"]:
        st.warning("Accès limité aux articles de sous-catégorie Événement. Ajout / modification interdits.")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        search = st.text_input("🔍 Rechercher", key="catalogue_search")

    with c2:
        categorie = st.selectbox("Catégorie", categories, key="catalogue_categorie")

    with c3:
        if role in ["association", "particulier", "societe", "prestataire"]:
            sous_categorie_filter = "Événement"
            st.selectbox(
                "Sous-catégorie",
                ["Événement"],
                key="catalogue_sous_categorie_filter_public",
                disabled=True
            )
        else:
            sous_categorie_filter = st.selectbox(
                "Sous-catégorie",
                sous_categories,
                key="catalogue_sous_categorie_filter"
            )

    with c4:
        stock_filter = st.selectbox(
            "Stock",
            ["Tous", "Stock OK", "Stock bas", "Stock critique"],
            key="catalogue_stock_filter"
        )

    df = load_articles(search, categorie, sous_categorie_filter, stock_filter, role)

    st.subheader("📊 Vue rapide")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Articles affichés", len(df))
    k2.metric("Stock OK", int((df["etat"] == "OK").sum()) if not df.empty else 0)
    k3.metric("Stock bas", int((df["etat"] == "Bas").sum()) if not df.empty else 0)
    k4.metric("Critique", int((df["etat"] == "Critique").sum()) if not df.empty else 0)

    if is_admin:
        st.divider()
        with st.expander("➕ Ajouter un article"):
            with st.form("add_article_form"):
                a1, a2, a3 = st.columns(3)

                with a1:
                    nom = st.text_input("Nom")
                    categorie_new = st.selectbox("Catégorie", categories_form)
                    sous_cat = st.selectbox("Sous-catégorie", sous_categories_form)

                with a2:
                    stock = st.number_input("Stock", min_value=0, value=0)
                    stock_min = st.number_input("Stock minimum", min_value=0, value=1)
                    unite = st.text_input("Unité", value="unité")

                with a3:
                    prix = st.number_input("Prix facturation", min_value=0.0, value=0.0)
                    prix_achat = st.number_input("Prix d'achat", min_value=0.0, value=0.0)
                    prix_location = st.number_input("Prix location", min_value=0.0, value=0.0)
                    emplacement = st.text_input("Emplacement")
                    fournisseur_id = st.selectbox(
                        "Fournisseur",
                        fournisseurs_ids,
                        format_func=lambda x: fournisseurs_labels.get(x, "Aucun fournisseur"),
                        key="add_fournisseur_article",
                    )
                    image = st.file_uploader("Image", type=["png", "jpg", "jpeg", "webp"])

                notes = st.text_area("Notes")

                if st.form_submit_button("Ajouter", width="stretch"):
                    if not nom.strip():
                        st.error("Nom obligatoire.")
                    else:
                        add_article({
                            "nom": nom.strip(),
                            "categorie": categorie_new,
                            "sous_categorie": sous_cat,
                            "stock": int(stock),
                            "stock_min": int(stock_min),
                            "prix": float(prix),
                            "prix_achat": float(prix_achat),
                            "prix_location": float(prix_location),
                            "fournisseur_id": int(fournisseur_id or 0),
                            "unite": unite.strip(),
                            "emplacement": emplacement.strip(),
                            "image_path": save_image(image),
                            "notes": notes.strip(),
                        })
                        st.success("Article ajouté.")
                        st.rerun()

    st.divider()
    st.subheader("📋 Articles disponibles")

    display_cols = st.selectbox(
        "Affichage",
        [3, 4],
        index=1,
        format_func=lambda x: f"{x} colonnes",
        key="catalogue_display_cols"
    )

    ITEMS_PER_PAGE = display_cols * 3
    if "catalogue_page" not in st.session_state:
        st.session_state.catalogue_page = 1

    total = len(df)
    total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    st.session_state.catalogue_page = min(st.session_state.catalogue_page, total_pages)

    start = (st.session_state.catalogue_page - 1) * ITEMS_PER_PAGE
    df_page = df.iloc[start:start + ITEMS_PER_PAGE]

    p1, p2, p3 = st.columns([1, 2, 1])
    if p1.button("⬅️ Précédent", disabled=st.session_state.catalogue_page <= 1, width="stretch"):
        st.session_state.catalogue_page -= 1
        st.rerun()
    p2.markdown(f"<div style='text-align:center'>Page <b>{st.session_state.catalogue_page}</b> / <b>{total_pages}</b></div>", unsafe_allow_html=True)
    if p3.button("Suivant ➡️", disabled=st.session_state.catalogue_page >= total_pages, width="stretch"):
        st.session_state.catalogue_page += 1
        st.rerun()

    if df_page.empty:
        st.info("Aucun article disponible.")
    else:
        rows = list(df_page.iterrows())

        for i in range(0, len(rows), display_cols):
            cols = st.columns(display_cols)

            for col, (_, row) in zip(cols, rows[i:i + display_cols]):
                with col:
                    with st.container(border=True):
                        show_image(row["image_path"])

                        st.markdown(f"### {row['nom']}")

                        st.markdown(
                            f"""
                            **Catégorie :** {row['categorie']}  
                            **Sous-catégorie :** {row['sous_categorie'] or 'Standard'}  
                            **Stock :** {int(row['stock'])} {row['unite']} — min {int(row['stock_min'])}  
                            **Prix facturation :** {float(row['prix']):.2f} €  
                            **Prix d'achat :** {float(row.get('prix_achat', 0) or 0):.2f} €  
                            **Prix location :** {float(row.get('prix_location', 0) or 0):.2f} €  
                            **Emplacement :** {row['emplacement'] or '-'}  
                            **État :** {stock_badge(row['etat'])}
                            """,
                            unsafe_allow_html=True
                        )

                        if row.get("notes"):
                            with st.expander("📝 Notes"):
                                st.write(row.get("notes") or "")

                        if is_admin:
                            fournisseur_id_safe = 0
                            try:
                                if not pd.isna(row.get("fournisseur_id")):
                                    fournisseur_id_safe = int(row.get("fournisseur_id") or 0)
                            except Exception:
                                fournisseur_id_safe = 0

                            fd = fournisseur_details(fournisseur_id_safe)

                            if fd:
                                with st.expander("🏢 Fournisseur"):
                                    st.write(f"**Nom :** {fd.get('nom') or '-'}")
                                    st.write(f"**Adresse :** {fd.get('adresse') or '-'}")
                                    st.write(f"**Ville :** {(fd.get('code_postal') or '')} {(fd.get('ville') or '')}")
                                    st.write(f"**Email :** {fd.get('email') or '-'}")
                                    st.write(f"**Téléphone :** {fd.get('telephone') or '-'}")
                                    st.write(f"**Référent :** {fd.get('referent') or '-'}")
                                    if fd.get("notes"):
                                        st.info(fd.get("notes"))
                            else:
                                st.caption("Fournisseur : aucun fournisseur associé.")

                            with st.expander("✏️ Modifier"):
                                with st.form(f"edit_{row['id']}"):
                                    nom_e = st.text_input("Nom", value=row["nom"])
                                    cat_e = st.selectbox(
                                        "Catégorie",
                                        categories_form,
                                        index=categories_form.index(row["categorie"]) if row["categorie"] in categories_form else 0
                                    )
                                    sous_e = st.selectbox(
                                        "Sous-catégorie",
                                        sous_categories_form,
                                        index=sous_categories_form.index(row["sous_categorie"]) if row["sous_categorie"] in sous_categories_form else 0
                                    )
                                    stock_e = st.number_input("Stock", min_value=0, value=int(row["stock"]))
                                    stock_min_e = st.number_input("Stock min", min_value=0, value=int(row["stock_min"]))
                                    prix_e = st.number_input("Prix facturation", min_value=0.0, value=float(row["prix"]))
                                    prix_achat_e = st.number_input("Prix d'achat", min_value=0.0, value=float(row.get("prix_achat", 0) or 0))
                                    prix_location_e = st.number_input("Prix location", min_value=0.0, value=float(row.get("prix_location", 0) or 0))
                                    unite_e = st.text_input("Unité", value=row["unite"] or "unité")
                                    empl_e = st.text_input("Emplacement", value=row["emplacement"] or "")

                                    try:
                                        current_fournisseur = int(row.get("fournisseur_id") or 0)
                                    except Exception:
                                        current_fournisseur = 0

                                    if current_fournisseur not in fournisseurs_ids:
                                        current_fournisseur = 0

                                    fournisseur_e = st.selectbox(
                                        "Fournisseur",
                                        fournisseurs_ids,
                                        index=fournisseurs_ids.index(current_fournisseur),
                                        format_func=lambda x: fournisseurs_labels.get(x, "Aucun fournisseur"),
                                        key=f"edit_fournisseur_{row['id']}",
                                    )

                                    img_e = st.file_uploader(
                                        "Remplacer image",
                                        type=["png", "jpg", "jpeg", "webp"],
                                        key=f"edit_img_{row['id']}"
                                    )

                                    notes_e = st.text_area("Notes", value=row["notes"] or "")

                                    if st.form_submit_button("Enregistrer"):
                                        image_path = row["image_path"] or ""

                                        if img_e is not None:
                                            image_path = save_image(img_e)

                                        update_article(row["id"], {
                                            "nom": nom_e.strip(),
                                            "categorie": cat_e,
                                            "sous_categorie": sous_e,
                                            "stock": int(stock_e),
                                            "stock_min": int(stock_min_e),
                                            "prix": float(prix_e),
                                            "prix_achat": float(prix_achat_e),
                                            "prix_location": float(prix_location_e),
                                            "fournisseur_id": int(fournisseur_e or 0),
                                            "unite": unite_e.strip(),
                                            "emplacement": empl_e.strip(),
                                            "image_path": image_path,
                                            "notes": notes_e.strip(),
                                        })

                                        st.success("Article modifié.")
                                        st.rerun()

                            with st.expander("🗑️ Supprimer"):
                                confirm = st.checkbox(
                                    "Confirmer",
                                    key=f"del_confirm_{row['id']}"
                                )

                                if st.button(
                                    "Supprimer",
                                    disabled=not confirm,
                                    key=f"del_{row['id']}"
                                ):
                                    delete_article(row["id"])
                                    st.success("Article supprimé.")
                                    st.rerun()
                        else:
                            st.caption("Lecture seule")

    st.divider()
    p1b, p2b, p3b = st.columns([1, 2, 1])
    if p1b.button("⬅️ Précédent ", disabled=st.session_state.catalogue_page <= 1, width="stretch"):
        st.session_state.catalogue_page -= 1
        st.rerun()
    p2b.markdown(f"<div style='text-align:center'>Page <b>{st.session_state.catalogue_page}</b> / <b>{total_pages}</b></div>", unsafe_allow_html=True)
    if p3b.button("Suivant ➡️ ", disabled=st.session_state.catalogue_page >= total_pages, width="stretch"):
        st.session_state.catalogue_page += 1
        st.rerun()

    st.subheader("📤 Export")
    if not df.empty:
        st.download_button(
            "Télécharger CSV",
            data=df.drop(columns=["id"]).to_csv(index=False).encode("utf-8"),
            file_name="catalogue_articles.csv",
            mime="text/csv",
            width="stretch"
        )

    if is_admin:
        st.subheader("📥 Import CSV")
        file = st.file_uploader("Importer CSV", type=["csv"])
        if file is not None:
            imp = pd.read_csv(file)
            st.dataframe(imp.head(10), width="stretch")
            if st.button("Importer les articles", width="stretch"):
                for _, r in imp.iterrows():
                    add_article({
                        "nom": str(r.get("nom", "")).strip(),
                        "categorie": str(r.get("categorie", "Divers")).strip(),
                        "sous_categorie": str(r.get("sous_categorie", "Standard")).strip(),
                        "stock": int(r.get("stock", 0) or 0),
                        "stock_min": int(r.get("stock_min", 0) or 0),
                        "prix": float(r.get("prix", 0) or 0),
                        "prix_achat": float(r.get("prix_achat", 0) or 0),
                        "prix_location": float(r.get("prix_location", 0) or 0),
                        "fournisseur_id": int(r.get("fournisseur_id", 0) or 0),
                        "unite": str(r.get("unite", "unité")).strip(),
                        "emplacement": str(r.get("emplacement", "")).strip(),
                        "image_path": "",
                        "notes": str(r.get("notes", "")).strip(),
                    })
                st.success("Import terminé.")
                st.rerun()
