from utils.footer import show_footer
# main.py
import importlib
import sqlite3
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
from streamlit_option_menu import option_menu

import utils.database as db
import utils.style as style
from config import DEFAULT_CONFIG

# Base utilisateurs connectés
ONLINE_DB = Path("/opt/logistique-pro/data/online_users.db")



# ============================================================
# THEME GLOBAL ADMINISTRATION SITE
# ============================================================


# PATCH84 - rendu pages catalogue personnalisées

# PATCH87 - Helper rendu pages catalogues personnalisées

# PATCH91 - rendu pages Catalogue Véhicules / Catalogue Bâtiments

# PATCH92 - rendu pages Catalogue Véhicules / Catalogue Bâtiments
def _patch92_render_catalogue_page(page_stem: str) -> None:
    import importlib.util
    from pathlib import Path
    import streamlit as st

    page_path = Path("/opt/logistique-pro/pages") / f"{page_stem}.py"

    if not page_path.exists():
        st.error(f"Page introuvable : {page_path}")
        return

    spec = importlib.util.spec_from_file_location(page_stem, page_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if hasattr(module, "render"):
        module.render()
    elif hasattr(module, "show"):
        module.show()
    else:
        st.error(f"La page {page_stem} ne contient pas render() ou show().")

def _patch91_render_catalogue_page(page_stem: str) -> None:
    import importlib.util
    from pathlib import Path
    import streamlit as st

    page_path = Path("/opt/logistique-pro/pages") / f"{page_stem}.py"

    if not page_path.exists():
        st.error(f"Page introuvable : {page_path}")
        return

    spec = importlib.util.spec_from_file_location(page_stem, page_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if hasattr(module, "render"):
        module.render()
    elif hasattr(module, "show"):
        module.show()
    else:
        st.error(f"La page {page_stem} ne contient pas render() ou show().")

def _patch87_render_page(page_stem: str) -> None:
    import importlib.util
    from pathlib import Path
    import streamlit as st

    project_dir = Path("/opt/logistique-pro")
    page_path = project_dir / "pages" / f"{page_stem}.py"

    if not page_path.exists():
        st.error(f"Page introuvable : {page_path}")
        return

    spec = importlib.util.spec_from_file_location(page_stem, page_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if hasattr(module, "render"):
        module.render()
    elif hasattr(module, "show"):
        module.show()
    else:
        st.error(f"La page {page_stem} ne contient pas render() ou show().")

def _patch84_render_page(page_stem: str) -> None:
    import importlib.util
    from pathlib import Path
    import streamlit as st

    project_dir = Path("/opt/logistique-pro")
    page_path = project_dir / "pages" / f"{page_stem}.py"

    if not page_path.exists():
        st.error(f"Page introuvable : {page_path}")
        return

    try:
        spec = importlib.util.spec_from_file_location(page_stem, page_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if hasattr(module, "render"):
            module.render()
        elif hasattr(module, "show"):
            module.show()
        else:
            st.error(f"La page {page_stem} ne contient pas render() ou show().")
    except Exception as exc:
        st.error(f"Erreur chargement {page_stem} : {exc}")

def get_global_site_setting(key, default=""):
    try:
        db_path = Path("/opt/logistique-pro/data/settings.db")

        if not db_path.exists():
            return default

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        row = conn.execute(
            "SELECT value FROM settings WHERE key=?",
            (key,)
        ).fetchone()

        conn.close()

        return row["value"] if row else default

    except Exception as e:
        print("get_global_site_setting error:", e)
        return default


def apply_global_site_theme():
    try:
        theme = str(get_global_site_setting("site_theme", "Municipal Bleu")).strip().lower()
        couleur1 = get_global_site_setting("site_couleur_principale", "#003366")
        couleur2 = get_global_site_setting("site_couleur_secondaire", "#0f766e")

        if theme == "mode sombre":
            st.markdown("""
            <style>
            .stApp {
                background-color: #0f172a !important;
                color: #e5e7eb !important;
            }

            [data-testid="stSidebar"] {
                background-color: #020617 !important;
                color: #e5e7eb !important;
            }

            [data-testid="stHeader"] {
                background-color: #0f172a !important;
            }

            section[data-testid="stSidebar"] * {
                color: #e5e7eb !important;
            }

            h1, h2, h3, h4, h5, h6,
            p, label, span, div {
                color: #e5e7eb;
            }

            div[data-testid="stMetric"],
            div[data-testid="stExpander"] {
                background-color: #111827 !important;
                border: 1px solid #334155 !important;
                border-radius: 12px !important;
            }

            div[data-testid="stDataFrame"] {
                background-color: #111827 !important;
            }

            input, textarea {
                background-color: #111827 !important;
                color: #e5e7eb !important;
            }

            button {
                border-radius: 10px !important;
            }

            .stButton > button {
                background-color: #1e293b !important;
                color: #e5e7eb !important;
                border: 1px solid #334155 !important;
            }

            .stButton > button:hover {
                background-color: #334155 !important;
                color: white !important;
            }
            </style>
            """, unsafe_allow_html=True)

        else:
            st.markdown(f"""
            <style>
            :root {{
                --site-primary: {couleur1};
                --site-secondary: {couleur2};
            }}

            .stApp {{
                background-color: #f8fafc;
            }}
            </style>
            """, unsafe_allow_html=True)

    except Exception as e:
        print("apply_global_site_theme error:", e)



# ============================================================
# ============================================================

st.set_page_config(
    page_title=DEFAULT_CONFIG["site_title"],
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

db.init_database()

if "user" not in st.session_state:
    st.session_state.user = None


# ============================================================
# FIX - Fonction restauration connexion persistante
# ============================================================

def restore_persistent_login():
    try:
        if st.session_state.get("user"):
            return

        token = st.query_params.get("login_token")

        if isinstance(token, list):
            token = token[0] if token else ""

        if not token:
            return

        user = db.get_user_from_login_token(token)

        if user:
            st.session_state["user"] = user

    except Exception as e:
        print("restore_persistent_login error:", e)


restore_persistent_login()
apply_global_site_theme()



if "theme" not in st.session_state:
    st.session_state.theme = DEFAULT_CONFIG["default_theme"]

if "preview_role" not in st.session_state:
    st.session_state.preview_role = None

style.apply_global_style()








# ============================================================
# PATCH - Restaurer connexion après actualisation
# ============================================================

def restore_persistent_login():
    try:
        if st.session_state.get("user"):
            return

        token = st.query_params.get("login_token")

        if isinstance(token, list):
            token = token[0] if token else ""

        if not token:
            return

        user = db.get_user_from_login_token(token)

        if user:
            st.session_state["user"] = user

    except Exception as e:
        print("restore_persistent_login error:", e)


def count_livraisons_retours_pending():
    try:
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*)
            FROM demandes
            WHERE statut IN ('Validée', 'Devis signé reçu')
              AND (
                    COALESCE(livraison_statut,'À livrer') <> 'Livrée'
                 OR COALESCE(retour_statut,'En attente retour') <> 'Retournée'
              )
        """)
        n = cur.fetchone()[0]
        conn.close()
        return int(n or 0)
    except Exception:
        return 0


def count_clotures_pending():
    try:
        conn = db.get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT COUNT(*)
            FROM demandes
            WHERE COALESCE(livraison_statut,'')='Livrée'
              AND COALESCE(retour_statut,'')='Retournée'
              AND COALESCE(cloture_statut,'Ouverte') <> 'Clôturée'
        """)

        n = cur.fetchone()[0]
        conn.close()
        return int(n or 0)
    except Exception:
        return 0

def update_user_activity(user):
    if not user:
        return

    try:
        ONLINE_DB.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(ONLINE_DB)
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS online_users (
                email TEXT PRIMARY KEY,
                user_id INTEGER,
                username TEXT,
                role TEXT,
                last_seen TEXT
            )
        """)

        email = user.get("email") or user.get("username") or "inconnu"

        cur.execute("""
            INSERT OR REPLACE INTO online_users (
                email, user_id, username, role, last_seen
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            email,
            user.get("id"),
            user.get("username", email),
            user.get("role", ""),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))

        conn.commit()
        conn.close()
    except Exception as e:
        print("ONLINE USERS ERROR:", e)


def render_admin_connected_users(user):
    if not user or str(user.get("role", "")).lower() != "admin":
        return

    update_user_activity(user)

    try:
        ONLINE_DB.parent.mkdir(parents=True, exist_ok=True)

        conn_online = sqlite3.connect(ONLINE_DB)
        conn_online.row_factory = sqlite3.Row
        cur_online = conn_online.cursor()

        cur_online.execute("""
            CREATE TABLE IF NOT EXISTS online_users (
                email TEXT PRIMARY KEY,
                user_id INTEGER,
                username TEXT,
                role TEXT,
                last_seen TEXT
            )
        """)

        online_rows_db = cur_online.execute("""
            SELECT email, username, role, last_seen
            FROM online_users
        """).fetchall()

        conn_online.close()

        activity = {
            str(r["email"]).lower(): dict(r)
            for r in online_rows_db
            if r["email"]
        }

        conn_users = db.get_connection()
        users_df = pd.read_sql_query("""
            SELECT id, username, email, role, status
            FROM users
            WHERE COALESCE(status, '') = 'validated'
            ORDER BY username
        """, conn_users)
        conn_users.close()

    except Exception as e:
        st.warning(f"Impossible d'afficher les utilisateurs : {e}")
        return

    colors = {
        "admin": "#dc2626",
        "equipe_interne": "#f97316",
        "interne": "#f59e0b",
        "particulier": "#111827",
        "societe": "#06b6d4",
        "association": "#16a34a",
        "externe": "#475569",
        "client": "#06b6d4",
        "prestataire": "#8b5cf6",
    }

    st.markdown("---")
    col_users_title, col_users_refresh = st.columns([3, 1])

    with col_users_title:
        st.subheader("👥 Utilisateurs du site")

    with col_users_refresh:
        if st.button("🔄 Actualiser", key="refresh_connected_users", width="stretch"):
            update_user_activity(user)
            st.rerun()

    now = datetime.now()
    online_rows = []
    offline_rows = []

    for _, u in users_df.iterrows():
        email = str(u["email"] or "").lower()
        act = activity.get(email)

        last_seen_value = act.get("last_seen") if act else None
        last_txt = "Jamais connecté"
        online = False

        if last_seen_value:
            try:
                last_seen = datetime.strptime(str(last_seen_value), "%Y-%m-%d %H:%M:%S")
                online = (now - last_seen) <= timedelta(minutes=60)
                last_txt = last_seen.strftime("%d/%m/%Y %H:%M")
            except Exception:
                pass

        row = {
            "username": u["username"],
            "email": u["email"],
            "role": u["role"],
            "last_txt": last_txt,
        }

        if online:
            online_rows.append(row)
        else:
            offline_rows.append(row)

    c1, c2 = st.columns(2)
    c1.metric("En ligne", len(online_rows))
    c2.metric("Hors ligne", len(offline_rows))

    def render_row(row, online):
        role = str(row["role"] or "").lower()
        color = colors.get(role, "#64748b")
        dot = "🟢" if online else "⚪"
        status_txt = "EN LIGNE" if online else "HORS LIGNE"

        st.markdown(
            f"""
            <div style="
                display:flex;
                align-items:center;
                justify-content:space-between;
                padding:8px 12px;
                margin:5px 0;
                border-radius:10px;
                border-left:7px solid {color};
                background:#f8fafc;
            ">
                <div>
                    <b>{dot} {row['username'] or row['email']}</b><br>
                    <span style="font-size:12px;color:#475569;">
                        {row['email'] or '-'} · dernier passage : {row['last_txt']}
                    </span>
                </div>
                <div style="text-align:right;">
                    <div style="color:{color};font-weight:800;font-size:13px;">{role}</div>
                    <div style="font-size:11px;color:#64748b;">{status_txt}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if online_rows:
        st.markdown("#### 🟢 En ligne")
        for row in online_rows:
            render_row(row, True)

    if offline_rows:
        with st.expander("⚪ Hors ligne", expanded=False):
            for row in offline_rows:
                render_row(row, False)


def load_page(module_name: str) -> None:
    try:
        module = importlib.import_module(module_name)
        if hasattr(module, "show"):
            module.show()
        else:
            st.error(f"La page '{module_name}' ne contient pas de fonction show().")
    except ModuleNotFoundError:
        st.error(f"Module introuvable : {module_name}")
    except Exception as e:
        st.error(f"Erreur lors du chargement de la page '{module_name}' : {e}")


def logout() -> None:
    try:
        token = st.query_params.get("login_token")
        if isinstance(token, list):
            token = token[0] if token else ""
        if token:
            db.delete_login_session(token)
        if "login_token" in st.query_params:
            del st.query_params["login_token"]
    except Exception as e:
        print("logout token cleanup error:", e)

    st.session_state.user = None
    st.rerun()



def get_unread_factures_count(user):
    if not user:
        return 0

    db_path = Path("/opt/logistique-pro/data/demandes.db")

    if not db_path.exists():
        return 0

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        cur.execute("PRAGMA table_info(demandes)")
        cols = [r[1] for r in cur.fetchall()]

        if "facture_lue" not in cols:
            cur.execute("ALTER TABLE demandes ADD COLUMN facture_lue INTEGER DEFAULT 0")
            conn.commit()

        email = user.get("email", "")

        cur.execute("""
            SELECT COUNT(*)
            FROM demandes
            WHERE email = ?
              AND (
                    statut = 'Devis à signer'
                    OR (
                        statut = 'Validée'
                        AND COALESCE(facture_lue, 0) = 0
                    )
              )
        """, (email,))

        count = cur.fetchone()[0]
        conn.close()
        return int(count or 0)

    except Exception:
        return 0


def get_unread_messages_count(user):
    if not user:
        return 0

    db_path = Path("/opt/logistique-pro/data/demandes.db")

    if not db_path.exists():
        return 0

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                destinataire TEXT,
                expediteur TEXT,
                sujet TEXT,
                message TEXT,
                lu INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        email = user.get("email", "")

        cur.execute("""
            SELECT COUNT(*)
            FROM messages
            WHERE COALESCE(lu, 0) = 0
              AND (destinataire = ? OR destinataire = 'Tous')
        """, (email,))

        count = cur.fetchone()[0]
        conn.close()
        return int(count or 0)

    except Exception:
        return 0



def get_pending_accounts_count(user):
    if not user or str(user.get("role", "")).lower() != "admin":
        return 0

    try:
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE status = 'pending'")
        count = cur.fetchone()[0]
        conn.close()
        return int(count or 0)
    except Exception:
        return 0


def get_pending_demandes_count(user):
    if not user or str(user.get("role", "")).lower() != "admin":
        return 0

    try:
        db_path = Path("/opt/logistique-pro/data/demandes.db")
        if not db_path.exists():
            return 0

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        cur.execute("""
            SELECT COUNT(*)
            FROM demandes
            WHERE statut IN ('En attente', 'Devis signé reçu')
        """)
        count = cur.fetchone()[0]

        conn.close()
        return int(count or 0)

    except Exception:
        return 0




def clean_menu_name(item):
    item = str(item)
    for sep in [" 🔴 ", " 🟠 ", " 🟢 ", " 🔵 "]:
        if sep in item:
            return item.split(sep)[0]
    return item.strip()


def _demandes_db():
    return Path("/opt/logistique-pro/data/demandes.db")


def _sql_count(query, params=()):
    try:
        conn = sqlite3.connect(_demandes_db())
        cur = conn.cursor()
        cur.execute(query, params)
        n = cur.fetchone()[0]
        conn.close()
        return int(n or 0)
    except Exception:
        return 0


def count_messages(user):
    if not user:
        return 0

    role = str(user.get("role", "")).lower()
    email = user.get("email", "")

    if role == "admin":
        return _sql_count("SELECT COUNT(*) FROM messages WHERE COALESCE(lu,0)=0")

    return _sql_count("""
        SELECT COUNT(*)
        FROM messages
        WHERE COALESCE(lu,0)=0
          AND (destinataire=? OR destinataire='Tous')
    """, (email,))


def count_pending_accounts(user):
    if not user or str(user.get("role", "")).lower() != "admin":
        return 0
    try:
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE status='pending'")
        n = cur.fetchone()[0]
        conn.close()
        return int(n or 0)
    except Exception:
        return 0


def count_admin_demandes(user):
    if not user or str(user.get("role", "")).lower() != "admin":
        return 0

    return _sql_count("""
        SELECT COUNT(*)
        FROM demandes
        WHERE statut IN ('En attente','Devis signé reçu')
    """)


def count_admin_clotures(user):
    if not user or str(user.get("role", "")).lower() != "admin":
        return 0

    return _sql_count("""
        SELECT COUNT(*)
        FROM demandes
        WHERE COALESCE(livraison_statut,'')='Livrée'
          AND COALESCE(retour_statut,'')='Retournée'
          AND COALESCE(cloture_statut,'Ouverte') <> 'Clôturée'
    """)


def count_interne_ops(user):
    if not user:
        return 0

    role = str(user.get("role", "")).lower()
    if role not in ["interne", "equipe_interne"]:
        return 0

    return _sql_count("""
        SELECT COUNT(*)
        FROM demandes
        WHERE statut IN ('Validée','Devis signé reçu')
          AND (
               COALESCE(livraison_statut,'À livrer') <> 'Livrée'
            OR COALESCE(retour_statut,'En attente retour') <> 'Retournée'
          )
    """)


def count_user_mes_demandes(user):
    if not user:
        return 0

    role = str(user.get("role", "")).lower()
    if role in ["admin", "interne", "equipe_interne"]:
        return 0

    email = user.get("email", "")

    return _sql_count("""
        SELECT COUNT(*)
        FROM demandes
        WHERE email=?
          AND (
                statut='Devis à signer'
             OR statut='Devis signé reçu'
             OR (
                    COALESCE(cloture_statut,'Ouverte')='Clôturée'
                AND COALESCE(facture_lue,0)=0
                )
          )
    """, (email,))


def apply_menu_badges(menu_options, user):
    role = str((user or {}).get("role", "")).lower()

    result = []

    counts = {
        "Messages": count_messages(user),
        "Validation Comptes": count_pending_accounts(user),
        "Validation Demandes": count_admin_demandes(user),
        "Mes Demandes": count_user_mes_demandes(user),
    }

    eq_count = 0
    eq_color = ""

    if role == "admin":
        eq_count = count_admin_clotures(user)
        eq_color = "🔴"
    elif role in ["interne", "equipe_interne"]:
        eq_count = count_interne_ops(user)
        eq_color = "🟠"

    for item in menu_options:
        clean = clean_menu_name(item)

        if clean in ["Équipe Logistique",
            "Équipe Bâtiment", "Equipe Logistique"]:
            if eq_count > 0:
                result.append(f"Équipe Logistique {eq_color} {eq_count}")
            else:
                result.append("Équipe Logistique")
            continue

        n = counts.get(clean, 0)

        if n > 0:
            result.append(f"{clean} 🔴 {n}")
        else:
            result.append(clean)

    return result

def get_menu_options(user: Optional[Dict]) -> List[str]:
    if not user:
        return ["Connexion", "Créer un compte"]

    role = user.get("role")
    status = user.get("status", "pending")

    if status == "pending":
        return ["Compte en attente", "Mon Profil", "Se déconnecter"]

    if role == "admin":
        return [
            "Tableau de Bord",
            "Recherche Globale",
            "Nouvelle Demande",
            "Validation Demandes",
            "Catalogue Articles",
            "Catalogue Véhicules",
            "Catalogue Bâtiments",
            "Fournisseurs",
            "Inventaire",
            "Planning Équipes",
            "Équipe Logistique",
            "Calendrier Logistique",
            "Calendrier Événements",
            "Centre Alertes",
            "Messages",
            "Mon Profil",
            "Administration Site",
            "Administration Système",
            "Se déconnecter",
        ]

    if role == "equipe_interne":
        return [
            "Mon Tableau de Bord",
            "Catalogue Articles",
            "Catalogue Véhicules",
            "Catalogue Bâtiments",
            "Équipe Logistique",
            "Calendrier Logistique",
            "Centre Alertes",
            "Messages",
            "Mon Profil",
            "Se déconnecter",
        ]

    if role in ["interne", "association", "particulier", "societe"]:
        return [
            "Tableau de Bord",
            "Nouvelle Demande",
            "Mes Demandes",
            "Catalogue Articles",
            "Catalogue Véhicules",
            "Catalogue Bâtiments",
            "Messages",
            "Mon Profil",
            "Se déconnecter",
        ]

    return [
        "Tableau de Bord",
        "Catalogue Articles",
        "Catalogue Véhicules",
        "Catalogue Bâtiments",
        "Mon Profil",
        "Se déconnecter",
        ]


def get_icon_map() -> Dict[str, str]:
    return {
        "Connexion": "box-arrow-in-right",
        "Créer un compte": "person-plus",
        "Compte en attente": "hourglass-split",
        "Tableau de Bord": "house",
        "Recherche Globale": "search",
        "Mon Tableau de Bord": "house",
        "Validation Demandes": "clipboard-check",
        "Catalogue Articles": "box-seam",
        "Catalogue Véhicules": "truck",
        "Catalogue Bâtiments": "building",
        "Fournisseurs": "building",
        "Inventaire": "boxes",
        "Planning Équipes": "calendar-week",
        "Équipe Logistique": "truck",
        "Équipe Bâtiment": "hammer",
        "Calendrier Logistique": "calendar-event",
        "Calendrier Événements": "calendar-event",
        "Centre Alertes": "exclamation-triangle",
        "Messages": "envelope",
        "Mon Profil": "person-circle",
        "Administration Site": "palette",
        "Administration Système": "gear",
        "Nouvelle Demande": "plus-circle",
        "Mes Demandes": "file-earmark-text",
        "Se déconnecter": "box-arrow-right",
    }


def render_pending_account_page() -> None:
    st.title("⏳ Compte en attente de validation")
    st.info(
        """
Votre compte est actuellement en attente de validation par un administrateur.

Vous recevrez une notification dès que votre compte sera activé.
Merci de votre patience.
        """
    )

    if st.button("Se déconnecter", type="primary"):
        logout()



def get_effective_user():
    user = st.session_state.get("user")

    if not user:
        return None

    preview_role = st.session_state.get("preview_role")

    if user.get("role") == "admin" and preview_role:
        fake_user = dict(user)
        fake_user["role"] = preview_role
        fake_user["username"] = f"{user.get('username', 'Admin')} (aperçu {preview_role})"
        return fake_user

    return user



with st.sidebar:
    logo_path = Path("assets/logo/logo.png")

    if logo_path.exists():
        st.image(str(logo_path), width=220)
    else:
        st.markdown(
            f"""
            <h2 style="color:{DEFAULT_CONFIG['primary_color']}; text-align:center; margin-bottom:0;">
                🚛 Logistique Pro
            </h2>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("**Ville de Marly**")
    st.caption("Service Logistique & Événements")

    if st.session_state.user:
        username = st.session_state.user.get("username", "Utilisateur")
        role = st.session_state.user.get("role", "N/A")
        status = st.session_state.user.get("status", "pending")

        st.markdown("---")

        avatar_path = None

        try:
            conn_avatar = db.get_connection()
            cur_avatar = conn_avatar.cursor()
            cur_avatar.execute("PRAGMA table_info(users)")
            avatar_cols = [r[1] for r in cur_avatar.fetchall()]

            if "photo_profil" in avatar_cols:
                cur_avatar.execute(
                    "SELECT photo_profil FROM users WHERE id = ?",
                    (st.session_state.user.get("id"),),
                )
                avatar_row = cur_avatar.fetchone()

                if avatar_row and avatar_row["photo_profil"]:
                    candidate = Path("/opt/logistique-pro") / avatar_row["photo_profil"]
                    if candidate.exists():
                        avatar_path = candidate

            conn_avatar.close()
        except Exception:
            avatar_path = None

        if avatar_path is None:
            avatar_candidates = [
                Path("assets/photos/default/mairie.png"),
                Path("assets/logo/logo.png"),
                Path("assets/logo_mairie.png"),
            ]

            for avatar in avatar_candidates:
                if avatar.exists():
                    avatar_path = avatar
                    break

        if avatar_path:
            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                    <img src="data:image/png;base64,{avatar_path.read_bytes().hex()}" style="display:none;">
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.image(str(avatar_path), width=56)

        st.markdown(f"**Connecté :** {username}")
        st.caption(f"Rôle : {role} | Statut : {status}")

        if role == "admin" and status != "pending":
            preview = st.selectbox(
                "👁️ Aperçu utilisateur",
                [
                    "Admin",
                    "Interne",
                    "Équipe interne",
                    "Association",
                    "Particulier",
                    "Société",
        ],
                key="admin_preview_selector",
            )

            role_map_preview = {
                "Admin": None,
                "Interne": "interne",
                "Équipe interne": "equipe_interne",
                "Association": "association",
                "Particulier": "particulier",
                "Société": "societe",
            }

            st.session_state.preview_role = role_map_preview.get(preview)

    menu_options = get_menu_options(get_effective_user())
    menu_options = apply_menu_badges(menu_options, get_effective_user())
    icon_map = get_icon_map()
    icons = [icon_map.get(item, "circle") for item in menu_options]

    st.markdown("---")

    selected = option_menu(
        menu_title=None,
        options=menu_options,
        icons=icons,
        menu_icon="truck",
        default_index=0,
        styles={
            "container": {"padding": "6px"},
            "icon": {"font-size": "16px"},
            "nav-link": {
                "font-size": "15px",
                "padding": "10px 12px",
                "margin": "2px 0",
                "border-radius": "8px",
            },
            "nav-link-selected": {
                "background-color": DEFAULT_CONFIG["primary_color"],
                "color": "white",
            },
        },
    )

    selected_raw = selected

    if isinstance(selected, str):
        selected = clean_menu_name(selected)

    if isinstance(selected, str) and selected.startswith("Mes Demandes"):
        selected = "Mes Demandes"

    if isinstance(selected, str) and selected.startswith("Messages"):
        selected = "Messages"

    if isinstance(selected, str) and selected.startswith("Validation Comptes"):
        selected = "Validation Comptes"

    if isinstance(selected, str) and selected.startswith("Équipe Logistique"):
        selected = "Équipe Logistique"

    if isinstance(selected, str) and selected.startswith("Validation Demandes"):
        selected = "Validation Demandes"

    st.markdown("---")

    theme_options = ["Municipal Bleu", "Mode Clair", "Mode Sombre"]
    current_theme = st.session_state.get("theme", DEFAULT_CONFIG["default_theme"])
    if current_theme not in theme_options:
        current_theme = DEFAULT_CONFIG["default_theme"]

    theme_choice = st.selectbox(
        "🎨 Thème",
        options=theme_options,
        index=theme_options.index(current_theme),
        key="theme_selector",
    )

    if theme_choice != st.session_state.theme:
        st.session_state.theme = theme_choice
        st.rerun()




user = get_effective_user()

if user is None:
    if selected == "Connexion":
        load_page("pages.Connexion")
    elif selected == "Créer un compte":
        load_page("pages.Creation_Compte")
    else:
        st.warning("Veuillez vous connecter ou créer un compte.")

else:
    user_status = user.get("status", "pending")
    user_role = user.get("role")

    if selected == "Se déconnecter":
        logout()

    elif user_status == "pending":
        if selected == "Mon Profil":
            load_page("pages.Mon_Profil")
        else:
            render_pending_account_page()

    else:
        if selected in ["Tableau de Bord", "Mon Tableau de Bord"]:
            load_page("pages.Tableau_de_bord")

        elif selected == "Recherche Globale" and user_role == "admin":
            load_page("pages.Recherche_Globale")

        elif selected == "Validation Demandes" and user_role == "admin":
            load_page("pages.Validation_Demandes")

        elif selected == "Catalogue Articles":
            load_page("pages.Catalogue_Articles")

        elif selected == "Catalogue Véhicules":
            load_page("pages.Catalogue_Vehicules")

        elif selected == "Catalogue Bâtiments":
            load_page("pages.Catalogue_Batiments")

        elif selected == "Fournisseurs" and user_role == "admin":
            load_page("pages.Fournisseurs")

        elif selected == "Inventaire":
            load_page("pages.Inventaire")

        elif selected == "Planning Équipes":
            load_page("pages.Planning_Equipes")

        elif str(selected).startswith("Équipe Logistique"):
            load_page("pages.Equipe_Logistique")

        elif selected == "Calendrier Logistique":
            load_page("pages.Calendrier_Logistique")


        elif selected == "Calendrier Événements":
            load_page("pages.Calendrier_Evenements")

        elif selected == "Équipe Bâtiment":
            if user_role in ["admin", "equipe_batiment", "batiment", "agent_batiment"]:
                load_page("pages.Equipe_Batiment")
            else:
                st.error("Accès réservé à l’équipe bâtiment.")
        elif selected == "Centre Alertes":
            load_page("pages.Centre_Alertes")

        elif selected == "Messages":
            load_page("pages.Messages")

        elif selected == "Nouvelle Demande":
            load_page("pages.Nouvelle_Demande")

        elif selected == "Mes Demandes":
            load_page("pages.Mes_Demandes")

        elif selected == "Mon Profil":
            load_page("pages.Mon_Profil")

        elif selected == "Administration Site" and user_role == "admin":
            load_page("pages.Administration")

        elif selected == "Administration Système" and user_role == "admin":
            load_page("pages.Administration_Systeme")

        else:
            pass  # PATCH86B_FIX_EMPTY_ELSE_LINE_1185


render_admin_connected_users(st.session_state.user)

st.markdown(
    """
    <div class="custom-footer">
        © 2026 Ville de Marly - Développé par xavier59213
    </div>
    """,
    unsafe_allow_html=True,
)

show_footer()



# ============================================================
# PATCH - Appliquer thème global Administration Site
# ============================================================

def get_global_site_setting(key, default=""):
    try:
        import sqlite3
        from pathlib import Path

        db = Path("/opt/logistique-pro/data/settings.db")
        if not db.exists():
            return default

        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        conn.close()

        return row["value"] if row else default
    except Exception:
        return default


def apply_global_site_theme():
    try:
        theme = str(get_global_site_setting("site_theme", "Municipal Bleu")).strip().lower()
        couleur1 = get_global_site_setting("site_couleur_principale", "#003366")
        couleur2 = get_global_site_setting("site_couleur_secondaire", "#0f766e")

        if theme == "mode sombre":
            st.markdown("""
            <style>
            .stApp {
                background-color: #0f172a !important;
                color: #e5e7eb !important;
            }

            [data-testid="stSidebar"] {
                background-color: #020617 !important;
            }

            [data-testid="stHeader"] {
                background-color: #0f172a !important;
            }

            h1, h2, h3, h4, h5, h6, p, label, span, div {
                color: #e5e7eb;
            }

            div[data-testid="stMetric"],
            div[data-testid="stExpander"],
            section[data-testid="stSidebar"] {
                background-color: #111827;
                border-color: #334155;
            }

            input, textarea {
                background-color: #111827 !important;
                color: #e5e7eb !important;
            }
            </style>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <style>
            :root {{
                --site-primary: {couleur1};
                --site-secondary: {couleur2};
            }}
            </style>
            """, unsafe_allow_html=True)

    except Exception as e:
        print("apply_global_site_theme error:", e)
