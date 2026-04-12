import pandas as pd
from utils.database import get_connection


def export_table_to_csv(table_name: str):
    conn = get_connection()

    try:
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    except Exception as e:
        conn.close()
        return False, str(e)

    conn.close()

    if df.empty:
        return False, "Aucune donnée"

    return True, df.to_csv(index=False).encode("utf-8")
