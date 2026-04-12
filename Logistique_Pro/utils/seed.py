from utils.database import get_connection


def seed_demo_data():
    conn = get_connection()
    cur = conn.cursor()

    # Exemple bâtiments
    cur.execute("SELECT COUNT(*) FROM buildings")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO buildings (name, category, address, capacity)
            VALUES ('Mairie', 'Administratif', 'Centre ville', 50)
        """)

    # Exemple fournisseur
    cur.execute("SELECT COUNT(*) FROM suppliers")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO suppliers (name, contact_name)
            VALUES ('Fournisseur Test', 'Jean Dupont')
        """)

    conn.commit()
    conn.close()
