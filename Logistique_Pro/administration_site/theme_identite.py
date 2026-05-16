from pathlib import Path
import sqlite3
import streamlit as st

DB = Path("/opt/logistique-pro/data/settings.db")


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_settings():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    defaults = {
        "site_theme": "Municipal Bleu",
        "site_nom": "Logistique Pro - Ville de Marly",
        "site_couleur_principale": "#003366",
        "site_couleur_secondaire": "#0f766e",
        "site_logo": "",
    }

    for k, v in defaults.items():
        cur.execute("""
            INSERT OR IGNORE INTO settings (key, value)
            VALUES (?, ?)
        """, (k, v))

    conn.commit()
    conn.close()


def get_setting(key, default=""):
    ensure_settings()
    conn = connect()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    ensure_settings()
    conn = connect()
    conn.execute("""
        INSERT INTO settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (key, value))
    conn.commit()
    conn.close()


def save_logo(uploaded_file):
    if not uploaded_file:
        return ""

    logo_dir = Path("/opt/logistique-pro/assets/logos")
    logo_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(uploaded_file.name or "logo.png").suffix.lower()
    if suffix not in [".png", ".jpg", ".jpeg", ".webp"]:
        suffix = ".png"

    dest = logo_dir / f"site_logo{suffix}"
    dest.write_bytes(uploaded_file.getbuffer())

    return str(dest)


def render():
    # PATCH76_DISABLED_ADMIN_MODULE_TITLE: st.subheader("🎨 Thème & identité")
    st.caption("Paramètres visuels globaux du site.")

    ensure_settings()

    current_theme = get_setting("site_theme", "Municipal Bleu")
    site_nom = get_setting("site_nom", "Logistique Pro - Ville de Marly")
    couleur_principale = get_setting("site_couleur_principale", "#003366")
    couleur_secondaire = get_setting("site_couleur_secondaire", "#0f766e")
    site_logo = get_setting("site_logo", "")

    with st.form("admin_site_theme_form"):
        theme = st.selectbox(
            "Thème global",
            ["Municipal Bleu", "Mode Sombre", "Vert Technique", "Gris Administratif"],
            index=["Municipal Bleu", "Mode Sombre", "Vert Technique", "Gris Administratif"].index(current_theme)
            if current_theme in ["Municipal Bleu", "Mode Sombre", "Vert Technique", "Gris Administratif"] else 0,
            key="admin_site_theme_select"
        )

        nom = st.text_input(
            "Nom du site",
            value=site_nom,
            key="admin_site_nom"
        )

        col1, col2 = st.columns(2)

        with col1:
            couleur1 = st.color_picker(
                "Couleur principale",
                value=couleur_principale or "#003366",
                key="admin_site_couleur_1"
            )

        with col2:
            couleur2 = st.color_picker(
                "Couleur secondaire",
                value=couleur_secondaire or "#0f766e",
                key="admin_site_couleur_2"
            )

        uploaded_logo = st.file_uploader(
            "Logo du site",
            type=["png", "jpg", "jpeg", "webp"],
            key="admin_site_logo_upload"
        )

        if site_logo:
            st.info(f"Logo actuel : {site_logo}")
            if Path(site_logo).exists():
                st.image(site_logo, width=180)

        submit = st.form_submit_button("💾 Enregistrer le thème", width="stretch")

        if submit:
            logo_path = save_logo(uploaded_logo) or site_logo

            set_setting("site_theme", theme)
            set_setting("site_nom", nom.strip())
            set_setting("site_couleur_principale", couleur1)
            set_setting("site_couleur_secondaire", couleur2)
            set_setting("site_logo", logo_path)

            st.success("Thème Administration du Site enregistré.")
            st.rerun()

    st.divider()
    st.markdown("### Aperçu")

    if current_theme == "Mode Sombre":
        st.markdown("""
        <div style="background:#0f172a;color:#e5e7eb;padding:18px;border-radius:14px;">
            <h3 style="color:#e5e7eb;">Mode Sombre</h3>
            <p>Le thème sombre est enregistré. Il faut maintenant que main.py lise ce paramètre global.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:{couleur_principale};color:white;padding:18px;border-radius:14px;">
            <h3 style="color:white;">{current_theme}</h3>
            <p>{site_nom}</p>
        </div>
        """, unsafe_allow_html=True)


# ============================================================
# PATCH 33 - Alias show()
# ============================================================
def show():
    render()
