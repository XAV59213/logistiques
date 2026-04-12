from utils.database import get_connection


def add_vehicle(registration, brand, model):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO vehicles (registration, brand, model)
        VALUES (?, ?, ?)
    """, (registration, brand, model))

    conn.commit()
    conn.close()


def list_vehicles():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM vehicles ORDER BY registration")
    rows = cur.fetchall()

    conn.close()
    return rows
