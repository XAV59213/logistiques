import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from config import Config
from utils.helpers import page_header, empty_state
from utils.database import get_connection

page_header(
    "Exports & Backups",
    "Exports de données et sauvegarde de la base",
    "assets/icons/settings.png"
)

backup_dir = Path("data/backups")
backup_dir.mkdir(parents=True, exist_ok=True)

conn = get_connection()

st.subheader("Exports CSV")

col1, col2 = st.columns(2)

with col1:
    if st.button("Exporter les utilisateurs", width="stretch"):
        try:
            df_users = pd.read_sql_query("SELECT * FROM users ORDER BY id DESC", conn)
            if df_users.empty:
                st.warning("Aucun utilisateur à exporter.")
            else:
                csv_data = df_users.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Télécharger users.csv",
                    data=csv_data,
                    file_name="users.csv",
                    mime="text/csv",
                    width="stretch",
                )
        except Exception as e:
            st.error(f"Erreur export utilisateurs : {e}")

with col2:
    if st.button("Exporter le stock", width="stretch"):
        try:
            df_stock = pd.read_sql_query("SELECT * FROM stock_items ORDER BY id DESC", conn)
            if df_stock.empty:
                st.warning("Aucun article à exporter.")
            else:
                csv_data = df_stock.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Télécharger stock_items.csv",
                    data=csv_data,
                    file_name="stock_items.csv",
                    mime="text/csv",
                    width="stretch",
                )
        except Exception as e:
            st.error(f"Erreur export stock : {e}")

st.divider()
st.subheader("Sauvegarde base de données")

db_path = Path(Config.DB_PATH)

if st.button("Créer une sauvegarde SQLite", width="stretch"):
    if not db_path.exists():
        st.error("Aucune base de données trouvée.")
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"database_backup_{timestamp}.db"
        shutil.copy2(db_path, backup_file)
        st.success(f"Sauvegarde créée : {backup_file.name}")

st.divider()
st.subheader("Sauvegardes disponibles")

backup_files = sorted(backup_dir.glob("*.db"), reverse=True)

if not backup_files:
    empty_state("Aucune sauvegarde disponible.")
else:
    for backup_file in backup_files:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])

            with c1:
                st.write(f"**Fichier :** {backup_file.name}")
                st.write(f"**Taille :** {backup_file.stat().st_size} octets")

            with c2:
                with open(backup_file, "rb") as f:
                    st.download_button(
                        "Télécharger",
                        data=f,
                        file_name=backup_file.name,
                        mime="application/octet-stream",
                        key=f"dl_{backup_file.name}",
                        width="stretch",
                    )

conn.close()
