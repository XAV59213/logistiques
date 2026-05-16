# pages/02_Validation_Comptes.py
"""
Page Validation des Comptes
Validation ou refus des comptes utilisateurs en attente.
"""

import streamlit as st
import utils.database as db
from utils.messages import send_message
from utils.emailer import send_email


def format_date(value):
    """Formate proprement une date venant de SQLite ou Python."""
    if value is None:
        return "-"

    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y")

    value = str(value)

    if len(value) >= 10:
        return value[:10]

    return value


def show() -> None:
    st.title("🔐 Validation des Comptes")
    st.caption("Gestion des comptes en attente de validation")

    user = st.session_state.get("user")

    if not user or user.get("role") != "admin":
        st.error("Accès réservé aux administrateurs.")
        st.stop()

    conn = db.get_connection()

    comptes_en_attente = conn.execute("""
        SELECT id, username, email, role, categorie, created_at
        FROM users
        WHERE status = 'pending'
        ORDER BY created_at DESC
    """).fetchall()

    conn.close()

    if not comptes_en_attente:
        st.success("✅ Aucun compte en attente de validation.")
        return

    st.subheader(f"Comptes en attente ({len(comptes_en_attente)})")

    for compte in comptes_en_attente:
        compte_id = compte["id"]
        username = compte["username"] or "-"
        email = compte["email"] or "-"
        created_at = format_date(compte["created_at"])

        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 2, 2])

            with col1:
                st.write(f"**{username}**")
                st.write(f"Email : {email}")
                st.caption(f"Créé le {created_at}")

            with col2:
                role_propose = st.selectbox(
                    "Rôle proposé",
                    ["admin", "interne", "association", "particulier", "societe", "equipe_interne"],
                    key=f"role_{compte_id}",
                )

                if role_propose in ["interne", "equipe_interne"]:
                    categorie = st.selectbox(
                        "Catégorie",
                        ["Logistique", "Montage", "Livraison", "Technique", "Administration"],
                        key=f"cat_{compte_id}",
                    )
                else:
                    categorie = None

            with col3:
                if st.button("✅ Valider", key=f"valider_{compte_id}", width="stretch"):
                    conn = db.get_connection()
                    conn.execute("""
                        UPDATE users
                        SET status = 'validated',
                            role = ?,
                            categorie = ?,
                            validated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (role_propose, categorie, compte_id))
                    conn.commit()
                    conn.close()

                    st.success(f"Compte {username} validé avec succès !")
                    st.rerun()

                if st.button("❌ Refuser", key=f"refuser_{compte_id}", width="stretch"):
                    conn = db.get_connection()
                    conn.execute("DELETE FROM users WHERE id = ?", (compte_id,))
                    conn.commit()
                    conn.close()

                    st.warning(f"Compte {username} refusé et supprimé.")
                    st.rerun()

