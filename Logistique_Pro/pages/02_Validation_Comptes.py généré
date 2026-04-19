# pages/02_Validation_Comptes.py
"""
Page Validation des Comptes
Accessible uniquement aux administrateurs.
Permet de valider ou refuser les comptes en attente.
"""

import streamlit as st
import pandas as pd
import utils.database as db

def show() -> None:
    """Affiche la page de validation des comptes."""
    st.title("🔐 Validation des Comptes")
    st.caption("Gestion des comptes en attente de validation")

    user = st.session_state.user
    if not user or user["role"] != "admin":
        st.error("Accès réservé aux administrateurs.")
        st.stop()

    # Récupération des comptes en attente
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
        st.stop()

    st.subheader(f"Comptes en attente ({len(comptes_en_attente)})")

    for compte in comptes_en_attente:
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 2, 2])
            with col1:
                st.write(f"**{compte['username']}**")
                st.write(f"Email : {compte['email']}")
                st.caption(f"Créé le {compte['created_at'][:10]}")
            with col2:
                role_propose = st.selectbox(
                    "Rôle proposé",
                    ["admin", "interne", "association", "externe", "client", "equipe_interne"],
                    key=f"role_{compte['id']}"
                )
                if role_propose in ["interne", "equipe_interne"]:
                    categorie = st.selectbox(
                        "Catégorie",
                        ["Logistique", "Montage", "Livraison", "Technique", "Administration"],
                        key=f"cat_{compte['id']}"
                    )
                else:
                    categorie = None
            with col3:
                if st.button("✅ Valider", key=f"valider_{compte['id']}"):
                    conn = db.get_connection()
                    conn.execute("""
                        UPDATE users 
                        SET status = 'validated', 
                            role = ?, 
                            categorie = ?,
                            validated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (role_propose, categorie, compte['id']))
                    conn.commit()
                    conn.close()
                    st.success(f"Compte {compte['username']} validé avec succès !")
                    st.rerun()

                if st.button("❌ Refuser", key=f"refuser_{compte['id']}"):
                    conn = db.get_connection()
                    conn.execute("DELETE FROM users WHERE id = ?", (compte['id'],))
                    conn.commit()
                    conn.close()
                    st.warning(f"Compte {compte['username']} refusé et supprimé.")
                    st.rerun()

    st.caption("© 2026 Ville de Marly - Développé par xavier59213")
