from utils.database import get_connection


def add_vehicle(immatriculation, modele, vehicle_type):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO vehicules (immatriculation, modele, type)
        VALUES (?, ?, ?)
    """, (immatriculation, modele, vehicle_type))

    conn.commit()
    conn.close()


def list_vehicles():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM vehicules ORDER BY immatriculation")
    rows = cur.fetchall()

    conn.close()
    return rows
