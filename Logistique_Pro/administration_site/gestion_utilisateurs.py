import sqlite3
import streamlit as st

from administration_site.common import USERS_DB, connect_db, ensure_users_table, hash_password


ROLES = [
    "admin",
    "interne",
    "equipe_interne",
    "equipe_batiment",
    "garage",
    "association",
    "particulier",
    "societe",
    "prestataire",
]

STATUSES = [
    "validated",
    "pending",
    "disabled",
]

THEMES = [
    "Municipal Bleu",
    "Mode Sombre",
    "Classique",
]

OPTION_LABELS = {
    "role": "Rôle",
    "equipe": "Équipe",
    "service": "Service",
    "categorie": "Catégorie",
    "status": "Statut",
    "organisation": "Organisation",
    "account_type": "Type de compte",
}

DEFAULT_GLOBAL_OPTIONS = {
    "role": ROLES,
    "status": STATUSES,
    "categorie": ["interne", "externe", "association", "prestataire", "particulier", "société"],
    "equipe": ["Administration", "Bâtiment", "Garage", "Magasin", "Espaces verts", "Voirie"],
    "service": ["Administration", "Garage", "Bâtiments", "Logistique", "Technique", "Associations"],
    "organisation": ["Ville de Marly", "Association", "Entreprise", "Particulier"],
    "account_type": ["Interne", "Externe", "Invité", "Prestataire"],
}


def _get_columns(cur, table):
    return [r["name"] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]


def _add_column_if_missing(cur, table, column, sql_type):
    if column not in _get_columns(cur, table):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}")


def ensure_user_global_tables():
    ensure_users_table()

    conn = connect_db(USERS_DB)
    cur = conn.cursor()

    _add_column_if_missing(cur, "users", "equipe", "TEXT")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_global_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            value TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            position INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(kind, value)
        )
    """)

    for kind, values in DEFAULT_GLOBAL_OPTIONS.items():
        for pos, value in enumerate(values, start=1):
            clean = str(value or "").strip()
            if not clean:
                continue
            cur.execute("""
                INSERT OR IGNORE INTO user_global_options (kind, value, active, position)
                VALUES (?, ?, 1, ?)
            """, (kind, clean, pos))

    conn.commit()
    conn.close()


def get_user_options(kind, fallback=None, include_inactive=False):
    ensure_user_global_tables()

    fallback = fallback or []
    conn = connect_db(USERS_DB)

    query = """
        SELECT value
        FROM user_global_options
        WHERE kind=?
    """
    params = [kind]

    if not include_inactive:
        query += " AND active=1"

    query += " ORDER BY position ASC, value COLLATE NOCASE ASC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    values = []
    for row in rows:
        value = str(row["value"] or "").strip()
        if value and value not in values:
            values.append(value)

    for value in fallback:
        clean = str(value or "").strip()
        if clean and clean not in values:
            values.append(clean)

    return values


def option_select(label, kind, current="", fallback=None, key=None):
    options = get_user_options(kind, fallback=fallback)
    current = str(current or "").strip()

    if current and current not in options:
        options = [current] + options

    choices = options + ["➕ Autre..."]
    index = choices.index(current) if current in choices else 0
    selected = st.selectbox(label, choices, index=index, key=key)

    if selected == "➕ Autre...":
        return st.text_input(
            f"Nouvelle valeur - {label}",
            value=current,
            key=f"{key}_custom" if key else None,
        ).strip()

    return selected


def load_global_options():
    ensure_user_global_tables()

    conn = connect_db(USERS_DB)
    rows = conn.execute("""
        SELECT id, kind, value, active, position, created_at
        FROM user_global_options
        ORDER BY kind COLLATE NOCASE, position ASC, value COLLATE NOCASE
    """).fetchall()
    conn.close()

    return [dict(r) for r in rows]


def add_global_option(kind, value, active=1, position=0):
    ensure_user_global_tables()

    kind = str(kind or "").strip()
    value = str(value or "").strip()

    if kind not in OPTION_LABELS:
        return False, "Type de liste invalide."

    if not value:
        return False, "La valeur est obligatoire."

    conn = connect_db(USERS_DB)

    try:
        conn.execute("""
            INSERT INTO user_global_options (kind, value, active, position)
            VALUES (?, ?, ?, ?)
        """, (kind, value, 1 if active else 0, int(position or 0)))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Cette valeur existe déjà dans cette liste."

    conn.close()
    return True, "Valeur ajoutée."


def update_global_option(option_id, kind, value, active=1, position=0):
    ensure_user_global_tables()

    kind = str(kind or "").strip()
    value = str(value or "").strip()

    if kind not in OPTION_LABELS:
        return False, "Type de liste invalide."

    if not value:
        return False, "La valeur est obligatoire."

    conn = connect_db(USERS_DB)

    try:
        conn.execute("""
            UPDATE user_global_options
            SET kind=?, value=?, active=?, position=?
            WHERE id=?
        """, (kind, value, 1 if active else 0, int(position or 0), int(option_id)))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Cette valeur existe déjà dans cette liste."

    conn.close()
    return True, "Valeur modifiée."


def delete_global_option(option_id):
    ensure_user_global_tables()

    conn = connect_db(USERS_DB)
    conn.execute("DELETE FROM user_global_options WHERE id=?", (int(option_id),))
    conn.commit()
    conn.close()

    return True, "Valeur supprimée."


def load_users():
    ensure_user_global_tables()

    conn = connect_db(USERS_DB)
    rows = conn.execute("""
        SELECT
            id,
            username,
            first_name,
            last_name,
            email,
            role,
            categorie,
            status,
            telephone,
            phone,
            service,
            equipe,
            organisation,
            account_type,
            city,
            created_at,
            validated_at
        FROM users
        ORDER BY username COLLATE NOCASE
    """).fetchall()
    conn.close()

    return [dict(r) for r in rows]


def create_user(data):
    ensure_user_global_tables()

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not username:
        return False, "Le nom d'utilisateur est obligatoire."

    if not email or "@" not in email:
        return False, "Email invalide."

    if len(password) < 8:
        return False, "Le mot de passe doit contenir au moins 8 caractères."

    conn = connect_db(USERS_DB)
    cur = conn.cursor()

    existing = cur.execute(
        "SELECT id FROM users WHERE LOWER(email)=LOWER(?)",
        (email,),
    ).fetchone()

    if existing:
        conn.close()
        return False, "Un utilisateur existe déjà avec cet email."

    cur.execute("""
        INSERT INTO users (
            username,
            first_name,
            last_name,
            email,
            password_hash,
            role,
            categorie,
            status,
            telephone,
            phone,
            service,
            equipe,
            organisation,
            account_type,
            address,
            postal_code,
            city,
            theme_prefere,
            created_at,
            validated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP,
            CASE WHEN ?='validated' THEN CURRENT_TIMESTAMP ELSE NULL END
        )
    """, (
        username,
        data.get("first_name", "").strip(),
        data.get("last_name", "").strip(),
        email,
        hash_password(password),
        data.get("role", "particulier"),
        data.get("categorie", ""),
        data.get("status", "validated"),
        data.get("telephone", "").strip(),
        data.get("telephone", "").strip(),
        data.get("service", "").strip(),
        data.get("equipe", "").strip(),
        data.get("organisation", "").strip(),
        data.get("account_type", "").strip(),
        data.get("address", "").strip(),
        data.get("postal_code", "").strip(),
        data.get("city", "").strip(),
        data.get("theme_prefere", "Municipal Bleu"),
        data.get("status", "validated"),
    ))

    conn.commit()
    conn.close()

    return True, "Utilisateur ajouté avec succès."


def update_user(user_id, data):
    ensure_user_global_tables()

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()

    if not username:
        return False, "Le nom d'utilisateur est obligatoire."

    if not email or "@" not in email:
        return False, "Email invalide."

    conn = connect_db(USERS_DB)
    cur = conn.cursor()

    existing = cur.execute(
        "SELECT id FROM users WHERE LOWER(email)=LOWER(?) AND id<>?",
        (email, int(user_id)),
    ).fetchone()

    if existing:
        conn.close()
        return False, "Un autre utilisateur utilise déjà cet email."

    cur.execute("""
        UPDATE users
        SET
            username=?,
            first_name=?,
            last_name=?,
            email=?,
            role=?,
            categorie=?,
            status=?,
            telephone=?,
            phone=?,
            service=?,
            equipe=?,
            organisation=?,
            account_type=?,
            address=?,
            postal_code=?,
            city=?,
            theme_prefere=?,
            validated_at=CASE
                WHEN ?='validated' AND validated_at IS NULL THEN CURRENT_TIMESTAMP
                ELSE validated_at
            END
        WHERE id=?
    """, (
        username,
        data.get("first_name", "").strip(),
        data.get("last_name", "").strip(),
        email,
        data.get("role", "particulier"),
        data.get("categorie", ""),
        data.get("status", "validated"),
        data.get("telephone", "").strip(),
        data.get("telephone", "").strip(),
        data.get("service", "").strip(),
        data.get("equipe", "").strip(),
        data.get("organisation", "").strip(),
        data.get("account_type", "").strip(),
        data.get("address", "").strip(),
        data.get("postal_code", "").strip(),
        data.get("city", "").strip(),
        data.get("theme_prefere", "Municipal Bleu"),
        data.get("status", "validated"),
        int(user_id),
    ))

    conn.commit()
    conn.close()

    return True, "Utilisateur modifié avec succès."


def reset_password(user_id, password):
    if not password or len(password) < 8:
        return False, "Le mot de passe doit contenir au moins 8 caractères."

    conn = connect_db(USERS_DB)
    conn.execute(
        "UPDATE users SET password_hash=? WHERE id=?",
        (hash_password(password), int(user_id)),
    )
    conn.commit()
    conn.close()

    return True, "Mot de passe réinitialisé."


def set_status(user_id, status):
    conn = connect_db(USERS_DB)
    conn.execute("""
        UPDATE users
        SET status=?,
            validated_at=CASE
                WHEN ?='validated' AND validated_at IS NULL THEN CURRENT_TIMESTAMP
                ELSE validated_at
            END
        WHERE id=?
    """, (status, status, int(user_id)))
    conn.commit()
    conn.close()


def delete_user(user_id):
    conn = connect_db(USERS_DB)
    cur = conn.cursor()

    user = cur.execute(
        "SELECT email FROM users WHERE id=?",
        (int(user_id),),
    ).fetchone()

    if not user:
        conn.close()
        return False, "Utilisateur introuvable."

    if str(user["email"]).lower() == "admin@marly.fr":
        conn.close()
        return False, "Impossible de supprimer le compte administrateur principal."

    cur.execute("DELETE FROM users WHERE id=?", (int(user_id),))
    conn.commit()
    conn.close()

    return True, "Utilisateur supprimé définitivement."


def render_list():
    users = load_users()

    if not users:
        st.info("Aucun utilisateur trouvé.")
        return

    search = st.text_input("🔍 Recherche", key="users_search")

    filtered = users

    if search:
        q = search.lower().strip()
        filtered = [
            u for u in users
            if q in str(u.get("username", "")).lower()
            or q in str(u.get("first_name", "")).lower()
            or q in str(u.get("last_name", "")).lower()
            or q in str(u.get("email", "")).lower()
            or q in str(u.get("role", "")).lower()
            or q in str(u.get("service", "")).lower()
            or q in str(u.get("equipe", "")).lower()
            or q in str(u.get("organisation", "")).lower()
        ]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", len(users))
    c2.metric("Validés", len([u for u in users if u.get("status") == "validated"]))
    c3.metric("En attente", len([u for u in users if u.get("status") == "pending"]))
    c4.metric("Désactivés", len([u for u in users if u.get("status") == "disabled"]))

    rows = []

    for u in filtered:
        nom = " ".join([
            str(u.get("first_name") or "").strip(),
            str(u.get("last_name") or "").strip(),
        ]).strip()

        rows.append({
            "ID": u.get("id"),
            "Utilisateur": u.get("username"),
            "Nom": nom,
            "Email": u.get("email"),
            "Rôle": u.get("role"),
            "Équipe": u.get("equipe"),
            "Catégorie": u.get("categorie"),
            "Statut": u.get("status"),
            "Téléphone": u.get("telephone") or u.get("phone"),
            "Service": u.get("service"),
            "Organisation": u.get("organisation"),
            "Type compte": u.get("account_type"),
            "Créé le": u.get("created_at"),
        })

    st.dataframe(rows, width="stretch", hide_index=True)


def render_add():
    with st.form("users_add_form", clear_on_submit=True):
        c1, c2 = st.columns(2)

        with c1:
            username = st.text_input("Nom d'utilisateur *")
            first_name = st.text_input("Prénom")
            last_name = st.text_input("Nom")
            email = st.text_input("Email *")
            password = st.text_input("Mot de passe *", type="password")

        with c2:
            role = option_select("Rôle", "role", current="interne", fallback=ROLES, key="users_add_role")
            equipe = option_select("Équipe", "equipe", fallback=DEFAULT_GLOBAL_OPTIONS["equipe"], key="users_add_equipe")
            categorie = option_select("Catégorie", "categorie", fallback=DEFAULT_GLOBAL_OPTIONS["categorie"], key="users_add_categorie")
            status = option_select("Statut", "status", current="validated", fallback=STATUSES, key="users_add_status")
            telephone = st.text_input("Téléphone")
            theme_prefere = st.selectbox("Thème préféré", THEMES, index=0)

        service = option_select("Service", "service", fallback=DEFAULT_GLOBAL_OPTIONS["service"], key="users_add_service")
        organisation = option_select("Organisation", "organisation", fallback=DEFAULT_GLOBAL_OPTIONS["organisation"], key="users_add_organisation")
        account_type = option_select("Type de compte", "account_type", fallback=DEFAULT_GLOBAL_OPTIONS["account_type"], key="users_add_account_type")
        address = st.text_input("Adresse")
        postal_code = st.text_input("Code postal")
        city = st.text_input("Ville")

        submit = st.form_submit_button("✅ Ajouter l'utilisateur", width="stretch")

        if submit:
            ok, msg = create_user({
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": password,
                "role": role,
                "equipe": equipe,
                "categorie": categorie,
                "status": status,
                "telephone": telephone,
                "theme_prefere": theme_prefere,
                "service": service,
                "organisation": organisation,
                "account_type": account_type,
                "address": address,
                "postal_code": postal_code,
                "city": city,
            })

            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)


def render_edit():
    users = load_users()

    if not users:
        st.info("Aucun utilisateur à modifier.")
        return

    choices = {
        f"{u.get('username')} - {u.get('email')} [{u.get('role')}]": u
        for u in users
    }

    selected = st.selectbox("Utilisateur", list(choices.keys()), key="users_edit_select")
    u = choices[selected]

    with st.form("users_edit_form"):
        c1, c2 = st.columns(2)

        with c1:
            username = st.text_input("Nom d'utilisateur *", value=u.get("username") or "")
            first_name = st.text_input("Prénom", value=u.get("first_name") or "")
            last_name = st.text_input("Nom", value=u.get("last_name") or "")
            email = st.text_input("Email *", value=u.get("email") or "")

        with c2:
            role = option_select("Rôle", "role", current=u.get("role") or "", fallback=ROLES, key="users_edit_role")
            equipe = option_select("Équipe", "equipe", current=u.get("equipe") or "", fallback=DEFAULT_GLOBAL_OPTIONS["equipe"], key="users_edit_equipe")
            categorie = option_select("Catégorie", "categorie", current=u.get("categorie") or "", fallback=DEFAULT_GLOBAL_OPTIONS["categorie"], key="users_edit_categorie")
            status = option_select("Statut", "status", current=u.get("status") or "", fallback=STATUSES, key="users_edit_status")
            telephone = st.text_input("Téléphone", value=u.get("telephone") or u.get("phone") or "")
            theme_prefere = st.selectbox("Thème préféré", THEMES, index=0)

        service = option_select("Service", "service", current=u.get("service") or "", fallback=DEFAULT_GLOBAL_OPTIONS["service"], key="users_edit_service")
        organisation = option_select("Organisation", "organisation", current=u.get("organisation") or "", fallback=DEFAULT_GLOBAL_OPTIONS["organisation"], key="users_edit_organisation")
        account_type = option_select("Type de compte", "account_type", current=u.get("account_type") or "", fallback=DEFAULT_GLOBAL_OPTIONS["account_type"], key="users_edit_account_type")
        address = st.text_input("Adresse")
        postal_code = st.text_input("Code postal")
        city = st.text_input("Ville", value=u.get("city") or "")

        submit = st.form_submit_button("💾 Enregistrer", width="stretch")

        if submit:
            ok, msg = update_user(u.get("id"), {
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "role": role,
                "equipe": equipe,
                "categorie": categorie,
                "status": status,
                "telephone": telephone,
                "theme_prefere": theme_prefere,
                "service": service,
                "organisation": organisation,
                "account_type": account_type,
                "address": address,
                "postal_code": postal_code,
                "city": city,
            })

            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    st.markdown("### 🔐 Réinitialiser le mot de passe")

    with st.form("users_reset_password_form"):
        p1 = st.text_input("Nouveau mot de passe", type="password")
        p2 = st.text_input("Confirmer", type="password")
        submit = st.form_submit_button("🔐 Réinitialiser", width="stretch")

        if submit:
            if p1 != p2:
                st.error("Les deux mots de passe ne correspondent pas.")
            else:
                ok, msg = reset_password(u.get("id"), p1)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)


def render_status():
    users = load_users()

    if not users:
        st.info("Aucun utilisateur.")
        return

    choices = {
        f"{u.get('username')} - {u.get('email')} [{u.get('status')}]": u
        for u in users
    }

    selected = st.selectbox("Utilisateur", list(choices.keys()), key="users_status_select")
    u = choices[selected]

    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("✅ Valider", width="stretch"):
            set_status(u.get("id"), "validated")
            st.success("Utilisateur validé.")
            st.rerun()

    with c2:
        if st.button("⏳ Mettre en attente", width="stretch"):
            set_status(u.get("id"), "pending")
            st.success("Utilisateur mis en attente.")
            st.rerun()

    with c3:
        if st.button("🚫 Désactiver", width="stretch"):
            set_status(u.get("id"), "disabled")
            st.warning("Utilisateur désactivé.")
            st.rerun()


def render_delete():
    users = load_users()

    if not users:
        st.info("Aucun utilisateur.")
        return

    choices = {
        f"{u.get('username')} - {u.get('email')} [{u.get('role')}]": u
        for u in users
    }

    selected = st.selectbox("Utilisateur à supprimer", list(choices.keys()), key="users_delete_select")
    u = choices[selected]

    st.warning("La suppression définitive retire le compte de la base. Il est souvent préférable de désactiver le compte.")

    confirm = st.checkbox("Je confirme la suppression définitive")

    if st.button("🗑️ Supprimer définitivement", disabled=not confirm, width="stretch"):
        ok, msg = delete_user(u.get("id"))

        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)


def render_global_management():
    st.markdown("### ⚙️ Gestion globale")
    st.caption("Gestion des rôles, équipes, services, catégories, statuts, organisations et types de compte utilisés par les utilisateurs.")

    options = load_global_options()

    rows = []
    for item in options:
        rows.append({
            "ID": item.get("id"),
            "Liste": OPTION_LABELS.get(item.get("kind"), item.get("kind")),
            "Valeur": item.get("value"),
            "Actif": "Oui" if item.get("active") else "Non",
            "Ordre": item.get("position"),
            "Créé le": item.get("created_at"),
        })

    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.info("Aucune valeur globale enregistrée.")

    tab_add_option, tab_edit_option, tab_delete_option = st.tabs([
        "➕ Ajouter",
        "✏️ Modifier",
        "🗑️ Supprimer",
    ])

    with tab_add_option:
        with st.form("global_option_add_form", clear_on_submit=True):
            kind = st.selectbox(
                "Liste",
                list(OPTION_LABELS.keys()),
                format_func=lambda k: OPTION_LABELS.get(k, k),
                key="global_option_add_kind",
            )
            value = st.text_input("Nouvelle valeur")
            c1, c2 = st.columns(2)
            with c1:
                active = st.checkbox("Actif", value=True, key="global_option_add_active")
            with c2:
                position = st.number_input("Ordre", min_value=0, value=0, step=1, key="global_option_add_position")

            submit = st.form_submit_button("✅ Ajouter", width="stretch")

            if submit:
                ok, msg = add_global_option(kind, value, active, position)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    with tab_edit_option:
        if not options:
            st.info("Aucune valeur à modifier.")
        else:
            choices = {
                f"{item.get('id')} - {OPTION_LABELS.get(item.get('kind'), item.get('kind'))} : {item.get('value')}": item
                for item in options
            }
            selected = st.selectbox("Valeur à modifier", list(choices.keys()), key="global_option_edit_select")
            item = choices[selected]

            with st.form("global_option_edit_form"):
                kinds = list(OPTION_LABELS.keys())
                kind = st.selectbox(
                    "Liste",
                    kinds,
                    index=kinds.index(item.get("kind")) if item.get("kind") in kinds else 0,
                    format_func=lambda k: OPTION_LABELS.get(k, k),
                    key="global_option_edit_kind",
                )
                value = st.text_input("Valeur", value=item.get("value") or "")
                c1, c2 = st.columns(2)
                with c1:
                    active = st.checkbox("Actif", value=bool(item.get("active")), key="global_option_edit_active")
                with c2:
                    position = st.number_input("Ordre", min_value=0, value=int(item.get("position") or 0), step=1, key="global_option_edit_position")

                submit = st.form_submit_button("💾 Enregistrer", width="stretch")

                if submit:
                    ok, msg = update_global_option(item.get("id"), kind, value, active, position)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    with tab_delete_option:
        if not options:
            st.info("Aucune valeur à supprimer.")
        else:
            choices = {
                f"{item.get('id')} - {OPTION_LABELS.get(item.get('kind'), item.get('kind'))} : {item.get('value')}": item
                for item in options
            }
            selected = st.selectbox("Valeur à supprimer", list(choices.keys()), key="global_option_delete_select")
            item = choices[selected]

            st.warning("La suppression retire la valeur de la liste globale. Les utilisateurs déjà enregistrés gardent leur ancienne valeur texte.")
            confirm = st.checkbox("Je confirme la suppression", key="global_option_delete_confirm")

            if st.button("🗑️ Supprimer la valeur", disabled=not confirm, width="stretch"):
                ok, msg = delete_global_option(item.get("id"))
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)


def render():
    # PATCH77_DISABLED_DUPLICATE_USER_TITLE: st.subheader("👥 Gestion des Utilisateurs")
    st.caption("Ajouter, modifier, désactiver ou supprimer les comptes utilisateurs.")

    ensure_user_global_tables()

    tab_list, tab_add, tab_edit, tab_status, tab_delete, tab_global = st.tabs([
        "📋 Liste",
        "➕ Ajouter",
        "✏️ Modifier",
        "🚫 Activer / désactiver",
        "🗑️ Supprimer",
        "⚙️ Gestion globale",
    ])

    with tab_list:
        render_list()

    with tab_add:
        render_add()

    with tab_edit:
        render_edit()

    with tab_status:
        render_status()

    with tab_delete:
        render_delete()

    with tab_global:
        render_global_management()


# ============================================================
# Alias show()
# ============================================================
def show():
    render()
