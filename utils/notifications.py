from utils.database import get_connection


def create_notification(title: str, message: str, level: str = "info"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO notifications (title, message, level)
        VALUES (?, ?, ?)
        """,
        (title.strip(), message.strip(), level)
    )
    conn.commit()
    conn.close()


def list_notifications(limit: int | None = None):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT id, title, message, level, is_read, created_at
        FROM notifications
        ORDER BY created_at DESC
    """

    if limit is not None:
        query += f" LIMIT {int(limit)}"

    cur.execute(query)
    rows = cur.fetchall()
    conn.close()
    return rows


def mark_notification_read(notification_id: int, is_read: int = 1):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE notifications SET is_read = ? WHERE id = ?",
        (int(is_read), int(notification_id))
    )
    conn.commit()
    conn.close()
