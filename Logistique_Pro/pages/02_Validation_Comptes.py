# pages/02_Validation_Comptes.py
"""
Page Validation des Comptes
Accessible uniquement aux administrateurs.
Permet de valider ou refuser les comptes en attente.
"""

import streamlit as st

import utils.database as db


ROLE_OPTIONS = [
    "admin",
    "interne",
    "association",
    "externe",
    "client",
    "equipe_interne",
]

CATEGORIE_OPTIONS = [
    "Administration",
    "Logistique",
    "Montage",
    "Livraison",
    "Technique",
    "Communication",
    "Association",
    "Client",
]


def _default_categorie_for_role(role: str) -> str | None:
    mapping = {
        "admin": "Administration",
        "interne": "Logistique",
        "equipe_interne": "Technique",
        "association": "Association",
        "client": "Client",
        "externe": None,
    }
    return mapping.get(role)


def show() -> None:
    st.title("🔐 Validation des Comptes")
    st.caption("Gestion des comptes utilisateurs en attente de validation")

    user = st.session_state.get("user")
    if not user or user.get("role") != "admin":
        st.error("Accès réservé aux administrateurs.")
        st.stop()

    pending_users = db.get_pending_users()

    if not pending_users:
        st.success("✅ Aucun compte en attente de validation.")
        st.stop()

    st.subheader(f"Comptes en attente ({len(pending_users)})")

    for row in pending_users:
        compte = dict(row)
        user_id = int(compte["id"])
        username = compte.get("username", "")
        email = compte.get("email", "")
        current_role = compte.get("role") or "externe"
        created_at = compte.get("created_at", "")

        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 2, 2])

            with col1:
                st.markdown(f"### {username}")
                st.write(f"**Email :** {email}")
                st.write(f"**Rôle demandé :** {current_role}")
                st.caption(f"Créé le : {created_at}")

            with col2:
                role_index = ROLE_OPTIONS.index(current_role) if current_role in ROLE_OPTIONS else ROLE_OPTIONS.index("externe")
                role_propose = st.selectbox(
                    "Rôle à attribuer",
                    ROLE_OPTIONS,
                    index=role_index,
                    key=f"role_{user_id}",
                )

                default_cat = _default_categorie_for_role(role_propose)
                if default_cat in CATEGORIE_OPTIONS:
                    cat_index = CATEGORIE_OPTIONS.index(default_cat)
                else:
                    cat_index = 0

                categorie = st.selectbox(
                    "Catégorie",
                    CATEGORIE_OPTIONS,
                    index=cat_index,
                    key=f"cat_{user_id}",
                )

            with col3:
                if st.button("✅ Valider", key=f"validate_{user_id}", use_container_width=True):
                    try:
                        db.validate_user(
                            user_id=user_id,
                            role=role_propose,
                            categorie=categorie,
                        )
                        st.success(f"Compte « {username} » validé avec succès.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de la validation : {e}")

                if st.button("❌ Refuser", key=f"delete_{user_id}", use_container_width=True):
                    try:
                        db.delete_user(user_id)
                        st.warning(f"Compte « {username} » refusé et supprimé.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur lors du refus : {e}")

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
