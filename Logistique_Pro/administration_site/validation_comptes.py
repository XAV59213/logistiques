import streamlit as st

from administration_site.common import USERS_DB, connect_db, ensure_users_table


def load_pending_users():
    ensure_users_table()
    conn = connect_db(USERS_DB)

    rows = conn.execute("""
        SELECT id, username, email, role, categorie, created_at
        FROM users
        WHERE COALESCE(status, '') = 'pending'
        ORDER BY created_at DESC
    """).fetchall()

    conn.close()
    return [dict(r) for r in rows]


def validate_user(user_id, role, categorie):
    conn = connect_db(USERS_DB)
    conn.execute("""
        UPDATE users
        SET status='validated',
            role=?,
            categorie=?,
            validated_at=CURRENT_TIMESTAMP
        WHERE id=?
    """, (role, categorie, int(user_id)))
    conn.commit()
    conn.close()


def refuse_user(user_id):
    conn = connect_db(USERS_DB)
    conn.execute("DELETE FROM users WHERE id=?", (int(user_id),))
    conn.commit()
    conn.close()


def render():
    # PATCH76_DISABLED_ADMIN_MODULE_TITLE: st.subheader("✅ Validation des comptes")
    st.caption("Valider ou refuser les comptes en attente.")

    users = load_pending_users()

    if not users:
        st.success("Aucun compte en attente.")
        return

    roles = [
        "interne",
        "equipe_interne",
        "equipe_batiment",
        "garage",
        "association",
        "particulier",
        "societe",
        "prestataire",
        "admin",
    ]

    for u in users:
        with st.container(border=True):
            st.markdown(f"### {u.get('username')}")
            st.write(f"Email : **{u.get('email')}**")
            st.write(f"Rôle demandé : **{u.get('role')}**")
            st.write(f"Créé le : {u.get('created_at')}")

            c1, c2, c3 = st.columns([2, 2, 1])

            with c1:
                role = st.selectbox(
                    "Rôle à attribuer",
                    roles,
                    index=roles.index(u.get("role")) if u.get("role") in roles else 0,
                    key=f"validation_role_{u.get('id')}"
                )

            with c2:
                categorie = st.text_input(
                    "Catégorie",
                    value=u.get("categorie") or "",
                    key=f"validation_categorie_{u.get('id')}"
                )

            with c3:
                if st.button("✅ Valider", key=f"validate_{u.get('id')}", width="stretch"):
                    validate_user(u.get("id"), role, categorie)
                    st.success("Compte validé.")
                    st.rerun()

                if st.button("❌ Refuser", key=f"refuse_{u.get('id')}", width="stretch"):
                    refuse_user(u.get("id"))
                    st.warning("Compte refusé et supprimé.")
                    st.rerun()


# ============================================================
# PATCH 33 - Alias show()
# ============================================================
def show():
    render()
