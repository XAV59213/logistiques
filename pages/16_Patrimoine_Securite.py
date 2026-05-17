import streamlit as st
import pandas as pd
from utils.helpers import page_header, empty_state
from utils.database import get_connection

page_header(
    "Patrimoine & Sécurité",
    "Gestion des bâtiments communaux et suivi sécurité",
    "assets/icons/admin.png"
)

conn = get_connection()

st.subheader("Ajouter un bâtiment")

with st.form("add_building_form"):
    name = st.text_input("Nom du bâtiment")
    category = st.selectbox(
        "Catégorie",
        ["École", "Salle des fêtes", "Gymnase", "Bâtiment administratif", "Autre"]
    )
    address = st.text_input("Adresse")
    capacity = st.number_input("Capacité", min_value=0, step=1)
    safety_notes = st.text_area("Notes sécurité")

    submitted = st.form_submit_button("Ajouter le bâtiment")

    if submitted:
        if not name.strip():
            st.error("Le nom du bâtiment est obligatoire.")
        else:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO buildings (name, category, address, capacity, safety_notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name.strip(), category, address.strip(), int(capacity), safety_notes.strip())
            )
            conn.commit()
            st.success("Bâtiment ajouté avec succès.")
            st.rerun()

st.divider()
st.subheader("Liste des bâtiments")

df = pd.read_sql_query(
    "SELECT id, name, category, address, capacity, safety_notes, created_at FROM buildings ORDER BY name",
    conn
)

if df.empty:
    empty_state("Aucun bâtiment enregistré.")
else:
    st.dataframe(df, width="stretch", hide_index=True)

conn.close()
