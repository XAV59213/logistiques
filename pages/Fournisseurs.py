# pages/Fournisseurs.py

import sqlite3
import uuid
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st


BASE_DIR = Path("/opt/logistique-pro")
DB_PATH = BASE_DIR / "data" / "fournisseurs.db"
LOGO_DIR = BASE_DIR / "assets/photos/fournisseurs"
DEFAULT_LOGO = BASE_DIR / "assets/photos/default/mairie.png"

LOGO_DIR.mkdir(parents=True, exist_ok=True)


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS fournisseurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            adresse TEXT,
            code_postal TEXT,
            ville TEXT,
            email TEXT,
            telephone TEXT,
            referent TEXT,
            notes TEXT,
            logo_path TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_logo(file):
    if file is None:
        return ""

    ext = Path(file.name).suffix.lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        return ""

    filename = f"fournisseur_{uuid.uuid4().hex}{ext}"
    path = LOGO_DIR / filename

    with open(path, "wb") as f:
        f.write(file.getbuffer())

    return str(path.relative_to(BASE_DIR))


def show_logo(path_value):
    if path_value:
        p = BASE_DIR / str(path_value)
        if p.exists():
            st.image(str(p), width=90)
            return

    if DEFAULT_LOGO.exists():
        st.image(str(DEFAULT_LOGO), width=90)
    else:
        st.markdown("🏢")


def load_fournisseurs(search=""):
    conn = connect()

    if search:
        q = f"%{search}%"
        df = pd.read_sql_query("""
            SELECT *
            FROM fournisseurs
            WHERE nom LIKE ?
               OR email LIKE ?
               OR ville LIKE ?
               OR referent LIKE ?
               OR telephone LIKE ?
            ORDER BY nom
        """, conn, params=[q, q, q, q, q])
    else:
        df = pd.read_sql_query("""
            SELECT *
            FROM fournisseurs
            ORDER BY nom
        """, conn)

    conn.close()
    return df


def add_fournisseur(data):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO fournisseurs (
            nom, adresse, code_postal, ville, email, telephone,
            referent, notes, logo_path
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["nom"],
        data["adresse"],
        data["code_postal"],
        data["ville"],
        data["email"],
        data["telephone"],
        data["referent"],
        data["notes"],
        data["logo_path"],
    ))

    conn.commit()
    conn.close()


def update_fournisseur(fournisseur_id, data):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        UPDATE fournisseurs
        SET nom = ?,
            adresse = ?,
            code_postal = ?,
            ville = ?,
            email = ?,
            telephone = ?,
            referent = ?,
            notes = ?,
            logo_path = ?,
            updated_at = ?
        WHERE id = ?
    """, (
        data["nom"],
        data["adresse"],
        data["code_postal"],
        data["ville"],
        data["email"],
        data["telephone"],
        data["referent"],
        data["notes"],
        data["logo_path"],
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        int(fournisseur_id),
    ))

    conn.commit()
    conn.close()


def delete_fournisseur(fournisseur_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM fournisseurs WHERE id = ?", (int(fournisseur_id),))
    conn.commit()
    conn.close()


def show():
    init_db()

    st.title("🏢 Fournisseurs")
    st.caption("Gestion des fournisseurs et prestataires")

    user = st.session_state.get("user")

    if not user or str(user.get("role", "")).lower() != "admin":
        st.error("Accès réservé aux administrateurs.")
        st.stop()

    search = st.text_input("🔍 Rechercher un fournisseur")

    st.subheader("➕ Ajouter un fournisseur")

    with st.expander("Nouveau fournisseur", expanded=False):
        with st.form("add_fournisseur_form"):
            c1, c2, c3 = st.columns(3)

            with c1:
                nom = st.text_input("Nom du fournisseur *")
                email = st.text_input("Adresse mail")
                telephone = st.text_input("Téléphone")

            with c2:
                adresse = st.text_input("Adresse")
                code_postal = st.text_input("Code postal")
                ville = st.text_input("Ville")

            with c3:
                referent = st.text_input("Référent")
                logo_file = st.file_uploader(
                    "Logo de la société",
                    type=["png", "jpg", "jpeg", "webp"],
                    key="add_logo_fournisseur",
                )

            notes = st.text_area("Notes / informations complémentaires")

            submitted = st.form_submit_button("Ajouter le fournisseur", width="stretch")

            if submitted:
                if not nom.strip():
                    st.error("Le nom du fournisseur est obligatoire.")
                else:
                    add_fournisseur({
                        "nom": nom.strip(),
                        "adresse": adresse.strip(),
                        "code_postal": code_postal.strip(),
                        "ville": ville.strip(),
                        "email": email.strip(),
                        "telephone": telephone.strip(),
                        "referent": referent.strip(),
                        "notes": notes.strip(),
                        "logo_path": save_logo(logo_file),
                    })

                    st.success("Fournisseur ajouté.")
                    st.rerun()

    st.divider()

    df = load_fournisseurs(search.strip())

    st.subheader("📋 Liste des fournisseurs")

    if df.empty:
        st.info("Aucun fournisseur enregistré.")
        return

    st.metric("Fournisseurs", len(df))

    for _, row in df.iterrows():
        with st.container(border=True):
            c_logo, c_info, c_actions = st.columns([1, 4, 2])

            with c_logo:
                show_logo(row["logo_path"])

            with c_info:
                st.markdown(f"### {row['nom']}")
                st.write(f"**Email :** {row['email'] or '-'}")
                st.write(f"**Téléphone :** {row['telephone'] or '-'}")
                st.write(f"**Adresse :** {row['adresse'] or '-'}")
                st.write(f"**Ville :** {(row['code_postal'] or '')} {(row['ville'] or '')}")
                st.write(f"**Référent :** {row['referent'] or '-'}")

                if row["notes"]:
                    st.info(row["notes"])

            with c_actions:
                with st.expander("✏️ Modifier"):
                    with st.form(f"edit_fournisseur_{row['id']}"):
                        nom_e = st.text_input("Nom", value=row["nom"] or "", key=f"nom_{row['id']}")
                        email_e = st.text_input("Email", value=row["email"] or "", key=f"email_{row['id']}")
                        tel_e = st.text_input("Téléphone", value=row["telephone"] or "", key=f"tel_{row['id']}")
                        adresse_e = st.text_input("Adresse", value=row["adresse"] or "", key=f"adresse_{row['id']}")
                        cp_e = st.text_input("Code postal", value=row["code_postal"] or "", key=f"cp_{row['id']}")
                        ville_e = st.text_input("Ville", value=row["ville"] or "", key=f"ville_{row['id']}")
                        ref_e = st.text_input("Référent", value=row["referent"] or "", key=f"ref_{row['id']}")
                        notes_e = st.text_area("Notes", value=row["notes"] or "", key=f"notes_{row['id']}")
                        logo_e = st.file_uploader(
                            "Remplacer le logo",
                            type=["png", "jpg", "jpeg", "webp"],
                            key=f"logo_edit_{row['id']}",
                        )

                        if st.form_submit_button("Enregistrer", width="stretch"):
                            logo_path = row["logo_path"] or ""
                            if logo_e is not None:
                                logo_path = save_logo(logo_e)

                            update_fournisseur(row["id"], {
                                "nom": nom_e.strip(),
                                "adresse": adresse_e.strip(),
                                "code_postal": cp_e.strip(),
                                "ville": ville_e.strip(),
                                "email": email_e.strip(),
                                "telephone": tel_e.strip(),
                                "referent": ref_e.strip(),
                                "notes": notes_e.strip(),
                                "logo_path": logo_path,
                            })

                            st.success("Fournisseur modifié.")
                            st.rerun()

                with st.expander("🗑️ Supprimer"):
                    confirm = st.checkbox(
                        "Confirmer la suppression",
                        key=f"confirm_delete_fournisseur_{row['id']}",
                    )

                    if st.button(
                        "Supprimer",
                        disabled=not confirm,
                        key=f"delete_fournisseur_{row['id']}",
                        width="stretch",
                    ):
                        delete_fournisseur(row["id"])
                        st.warning("Fournisseur supprimé.")
                        st.rerun()

    st.divider()

    st.subheader("📤 Export CSV")
    st.download_button(
        "Télécharger fournisseurs.csv",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="fournisseurs.csv",
        mime="text/csv",
        width="stretch",
    )
