import streamlit as st
import pandas as pd
from pathlib import Path

from utils.helpers import page_header, empty_state
from utils.database import get_connection
from utils.qr_scanner import generate_qr

page_header(
    "Inventaire & QR Code",
    "Gestion des articles et génération des QR codes",
    "assets/icons/stock.png"
)

conn = get_connection()
cur = conn.cursor()

st.subheader("Ajouter un article")

with st.form("add_stock_item_form"):
    name = st.text_input("Nom de l'article")
    category = st.text_input("Catégorie")
    quantity = st.number_input("Quantité", min_value=0, step=1)
    unit = st.text_input("Unité", value="pcs")
    min_threshold = st.number_input("Seuil minimum", min_value=0, step=1)
    location = st.text_input("Emplacement")
    notes = st.text_area("Notes")

    submitted = st.form_submit_button("Ajouter l'article")

    if submitted:
        if not name.strip():
            st.error("Le nom de l'article est obligatoire.")
        else:
            cur.execute(
                """
                INSERT INTO stock_items (
                    name, category, quantity, unit, min_threshold, location, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name.strip(),
                    category.strip(),
                    int(quantity),
                    unit.strip(),
                    int(min_threshold),
                    location.strip(),
                    notes.strip(),
                )
            )
            item_id = cur.lastrowid

            qr_dir = Path("assets/photos/qr")
            qr_dir.mkdir(parents=True, exist_ok=True)
            qr_path = qr_dir / f"item_{item_id}.png"

            generate_qr(f"stock_item:{item_id}:{name.strip()}", str(qr_path))

            cur.execute(
                "UPDATE stock_items SET qr_code = ? WHERE id = ?",
                (str(qr_path), item_id)
            )

            conn.commit()
            st.success("Article ajouté avec succès.")
            st.rerun()

st.divider()
st.subheader("Inventaire")

df = pd.read_sql_query("""
    SELECT id, name, category, quantity, unit, min_threshold, location, qr_code, notes, created_at
    FROM stock_items
    ORDER BY name
""", conn)

if df.empty:
    empty_state("Aucun article enregistré.")
else:
    for _, row in df.iterrows():
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"### {row['name']}")
                st.write(f"**Catégorie :** {row['category'] or '-'}")
                st.write(f"**Quantité :** {row['quantity']} {row['unit']}")
                st.write(f"**Seuil minimum :** {row['min_threshold']}")
                st.write(f"**Emplacement :** {row['location'] or '-'}")
                st.write(f"**Notes :** {row['notes'] or '-'}")

                if int(row["quantity"]) <= int(row["min_threshold"]):
                    st.warning("Stock bas")

            with col2:
                qr_path = row["qr_code"]
                if qr_path and Path(qr_path).exists():
                    st.image(qr_path, width=120)

conn.close()
