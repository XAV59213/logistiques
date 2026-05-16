# pages/12_Mon_Profil.py

import re
import uuid
from pathlib import Path
import bcrypt
import streamlit as st
import utils.database as db

BASE_DIR = Path("/opt/logistique-pro")
PROFILE_PHOTOS_DIR = BASE_DIR / "assets/photos/profils"
PROFILE_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)


def ensure_user_columns():
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(users)")
    existing = [row["name"] for row in cur.fetchall()]

    columns = {
        "first_name": "TEXT",
        "last_name": "TEXT",
        "phone": "TEXT",
        "address": "TEXT",
        "postal_code": "TEXT",
        "city": "TEXT",
        "service": "TEXT",
        "organisation": "TEXT",
        "account_type": "TEXT",
        "photo_profil": "TEXT",
    }

    for col, col_type in columns.items():
        if col not in existing:
            cur.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")

    conn.commit()
    conn.close()


def safe(row, key):
    try:
        value = row[key]
        return value if value not in [None, ""] else "-"
    except Exception:
        return "-"


def save_profile_photo(file, user_id):
    if file is None:
        return ""

    ext = Path(file.name).suffix.lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        return ""

    filename = f"user_{user_id}_{uuid.uuid4().hex}{ext}"
    path = PROFILE_PHOTOS_DIR / filename

    with open(path, "wb") as f:
        f.write(file.getbuffer())

    return str(path.relative_to(BASE_DIR))


def is_valid_email(email):
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email or "") is not None


def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def show():
    ensure_user_columns()

    st.title("👤 Mon Profil")
    st.caption("Gestion de vos informations personnelles")

    user = st.session_state.get("user")

    if not user:
        st.error("Vous devez être connecté.")
        st.stop()

    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user["id"],))
    row = cur.fetchone()
    conn.close()

    if not row:
        st.error("Utilisateur introuvable.")
        st.stop()

    st.subheader("🪪 Informations complètes du compte")

    with st.container(border=True):
        c1, c2, c3 = st.columns(3)

        with c1:
            st.write(f"**ID :** {safe(row, 'id')}")
            st.write(f"**Identifiant :** {safe(row, 'username')}")
            st.write(f"**Prénom :** {safe(row, 'first_name')}")
            st.write(f"**Nom :** {safe(row, 'last_name')}")
            st.write(f"**Email :** {safe(row, 'email')}")

        with c2:
            st.write(f"**Téléphone :** {safe(row, 'phone')}")
            st.write(f"**Rôle :** {safe(row, 'role')}")
            st.write(f"**Statut :** {safe(row, 'status')}")
            st.write(f"**Catégorie :** {safe(row, 'categorie')}")
            st.write(f"**Type de compte :** {safe(row, 'account_type')}")

        with c3:
            st.write(f"**Service / Fonction :** {safe(row, 'service')}")
            st.write(f"**Organisation :** {safe(row, 'organisation')}")
            st.write(f"**Adresse :** {safe(row, 'address')}")
            st.write(f"**Code postal :** {safe(row, 'postal_code')}")
            st.write(f"**Ville :** {safe(row, 'city')}")

    st.subheader("🖼️ Photo de profil")

    current_photo = safe(row, "photo_profil")
    if current_photo != "-" and (BASE_DIR / current_photo).exists():
        st.image(str(BASE_DIR / current_photo), width=120)
    else:
        default_photo = BASE_DIR / "assets/photos/default/mairie.png"
        if default_photo.exists():
            st.image(str(default_photo), width=120)
        else:
            st.info("Aucune photo de profil.")

    uploaded_photo = st.file_uploader(
        "Uploader une photo de profil",
        type=["png", "jpg", "jpeg", "webp"],
        key="upload_photo_profil",
    )

    if uploaded_photo is not None:
        new_photo_path = save_profile_photo(uploaded_photo, row["id"])

        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET photo_profil = ? WHERE id = ?",
            (new_photo_path, row["id"]),
        )
        conn.commit()
        conn.close()

        st.success("Photo de profil mise à jour.")
        st.rerun()

    st.subheader("📋 Modifier mes informations")

    with st.form("profile_form"):
        c1, c2 = st.columns(2)

        with c1:
            first_name = st.text_input("Prénom", value=safe(row, "first_name") if safe(row, "first_name") != "-" else "")
            username = st.text_input("Nom d'affichage", value=safe(row, "username") if safe(row, "username") != "-" else "")
            email = st.text_input("Adresse mail", value=safe(row, "email") if safe(row, "email") != "-" else "")
            phone = st.text_input("Téléphone", value=safe(row, "phone") if safe(row, "phone") != "-" else "")

        with c2:
            last_name = st.text_input("Nom", value=safe(row, "last_name") if safe(row, "last_name") != "-" else "")
            service = st.text_input("Service / Fonction", value=safe(row, "service") if safe(row, "service") != "-" else "")
            organisation = st.text_input("Association / Société / Organisme", value=safe(row, "organisation") if safe(row, "organisation") != "-" else "")

            options = ["Interne", "Particulier", "Association", "Société", "Prestataire", "Équipe interne"]
            current_type = safe(row, "account_type")
            account_type = st.selectbox(
                "Type de compte",
                options,
                index=options.index(current_type) if current_type in options else 1,
            )

        st.subheader("📍 Adresse")

        c3, c4, c5 = st.columns([2, 1, 1])

        with c3:
            address = st.text_input("Adresse rue", value=safe(row, "address") if safe(row, "address") != "-" else "")

        with c4:
            postal_code = st.text_input("Code postal", value=safe(row, "postal_code") if safe(row, "postal_code") != "-" else "")

        with c5:
            city = st.text_input("Ville", value=safe(row, "city") if safe(row, "city") != "-" else "Marly")

        submitted = st.form_submit_button("💾 Enregistrer les modifications", width="stretch")

        if submitted:
            if not username.strip():
                st.error("Le nom d'affichage est obligatoire.")
                return

            if not is_valid_email(email):
                st.error("Adresse mail invalide.")
                return

            conn = db.get_connection()
            cur = conn.cursor()

            cur.execute("""
                UPDATE users
                SET username = ?,
                    email = ?,
                    first_name = ?,
                    last_name = ?,
                    phone = ?,
                    address = ?,
                    postal_code = ?,
                    city = ?,
                    service = ?,
                    organisation = ?,
                    account_type = ?
                WHERE id = ?
            """, (
                username.strip(),
                email.strip(),
                first_name.strip(),
                last_name.strip(),
                phone.strip(),
                address.strip(),
                postal_code.strip(),
                city.strip(),
                service.strip(),
                organisation.strip(),
                account_type,
                user["id"],
            ))

            conn.commit()
            conn.close()

            st.session_state["user"]["username"] = username.strip()
            st.session_state["user"]["email"] = email.strip()

            st.success("Profil mis à jour.")
            st.rerun()

    st.divider()
    st.subheader("🔐 Changer mon mot de passe")

    with st.form("password_form"):
        new_password = st.text_input("Nouveau mot de passe", type="password")
        confirm_password = st.text_input("Confirmer le nouveau mot de passe", type="password")

        submitted_pwd = st.form_submit_button("🔐 Mettre à jour le mot de passe", width="stretch")

        if submitted_pwd:
            if not new_password:
                st.error("Le mot de passe est obligatoire.")
            elif len(new_password) < 8:
                st.error("Le mot de passe doit contenir au moins 8 caractères.")
            elif new_password != confirm_password:
                st.error("Les mots de passe ne correspondent pas.")
            else:
                conn = db.get_connection()
                cur = conn.cursor()
                cur.execute(
                    "UPDATE users SET password = ? WHERE id = ?",
                    (hash_password(new_password), user["id"]),
                )
                conn.commit()
                conn.close()

                st.success("Mot de passe mis à jour avec succès.")
