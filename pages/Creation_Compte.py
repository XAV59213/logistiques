# pages/01_Creation_Compte.py

import re
import streamlit as st
import utils.database as db
from utils.messages import send_message


def is_valid_email(email: str) -> bool:
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email or "") is not None


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
    }

    for col, col_type in columns.items():
        if col not in existing:
            cur.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")

    conn.commit()
    conn.close()


def update_user_details(email, data):
    conn = db.get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET first_name = ?,
            last_name = ?,
            phone = ?,
            address = ?,
            postal_code = ?,
            city = ?,
            service = ?,
            organisation = ?,
            account_type = ?,
            role = ?,
            categorie = ?
        WHERE email = ?
    """, (
        data["first_name"],
        data["last_name"],
        data["phone"],
        data["address"],
        data["postal_code"],
        data["city"],
        data["service"],
        data["organisation"],
        data["account_type"],
        data["role"],
        data["categorie"],
        email,
    ))

    conn.commit()
    conn.close()


def show() -> None:
    ensure_user_columns()

    st.title("📝 Créer un compte")
    st.caption("Inscription à Logistique Pro - Ville de Marly")

    with st.form("create_account_form"):
        st.subheader("👤 Identité")

        c1, c2 = st.columns(2)

        with c1:
            first_name = st.text_input("Prénom *")
            username = st.text_input("Nom d'utilisateur *")
            email = st.text_input("Adresse mail *")
            phone = st.text_input("Téléphone")

        with c2:
            last_name = st.text_input("Nom *")
            account_type = st.selectbox(
                "Type de compte *",
                ["Interne", "Particulier", "Association", "Société", "Prestataire", "Équipe interne"]
            )
            service = st.text_input("Service / Fonction")
            organisation = st.text_input("Association / Société / Organisme")

        st.subheader("📍 Adresse")

        c3, c4, c5 = st.columns([2, 1, 1])

        with c3:
            address = st.text_input("Adresse rue")

        with c4:
            postal_code = st.text_input("Code postal")

        with c5:
            city = st.text_input("Ville", value="Marly")

        st.subheader("🔐 Sécurité")

        c6, c7 = st.columns(2)

        with c6:
            password = st.text_input("Mot de passe *", type="password")

        with c7:
            confirm_password = st.text_input("Confirmer le mot de passe *", type="password")

        submitted = st.form_submit_button("Créer mon compte", type="primary", width="stretch")

        if submitted:
            if not first_name or not last_name or not username or not email or not password or not confirm_password:
                st.error("Tous les champs avec * sont obligatoires.")
                return

            if not is_valid_email(email):
                st.error("Adresse mail invalide.")
                return

            if password != confirm_password:
                st.error("Les mots de passe ne correspondent pas.")
                return

            if len(password) < 8:
                st.error("Le mot de passe doit contenir au moins 8 caractères.")
                return

            role_map = {
                "Interne": "interne",
                "Particulier": "particulier",
                "Association": "association",
                "Société": "societe",
                "Prestataire": "particulier",
                "Équipe interne": "equipe_interne",
            }

            categorie = None
            if account_type == "Équipe interne":
                categorie = "Logistique"
            elif account_type == "Interne":
                categorie = service or "Administration"

            role = role_map.get(account_type, "particulier")

            try:
                is_admin = db.create_user(username, email, password, role=role)

                update_user_details(email, {
                    "first_name": first_name.strip(),
                    "last_name": last_name.strip(),
                    "phone": phone.strip(),
                    "address": address.strip(),
                    "postal_code": postal_code.strip(),
                    "city": city.strip(),
                    "service": service.strip(),
                    "organisation": organisation.strip(),
                    "account_type": account_type,
                    "role": role,
                    "categorie": categorie,
                })

                if is_admin:
                    st.success("✅ Premier compte créé. Vous êtes administrateur.")
                    st.session_state.user = db.authenticate_user(email, password)
                    st.rerun()
                else:
                    st.success("✅ Compte créé avec succès.")
                    st.info("Votre compte est en attente de validation par un administrateur.")

            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Erreur lors de la création du compte : {e}")

    st.markdown("---")
    st.caption("Retournez au menu latéral pour vous connecter.")
