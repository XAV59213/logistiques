import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate
from pathlib import Path
import sqlite3

BASE_DIR = Path("/opt/logistique-pro")
SETTINGS_DB = BASE_DIR / "data" / "settings.db"


def get_settings():
    SETTINGS_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SETTINGS_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    defaults = {
        "smtp_enabled": "0",
        "smtp_host": "",
        "smtp_port": "587",
        "smtp_user": "",
        "smtp_password": "",
        "smtp_from": "",
        "smtp_tls": "1",
    }

    for k, v in defaults.items():
        cur.execute("INSERT OR IGNORE INTO email_settings (key, value) VALUES (?, ?)", (k, v))

    conn.commit()

    cur.execute("SELECT key, value FROM email_settings")
    data = {r["key"]: r["value"] for r in cur.fetchall()}

    conn.close()
    return data


def save_settings(data):
    conn = sqlite3.connect(SETTINGS_DB)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    for k, v in data.items():
        cur.execute(
            "INSERT OR REPLACE INTO email_settings (key, value) VALUES (?, ?)",
            (k, str(v)),
        )

    conn.commit()
    conn.close()


def send_email(to_email, subject, body):
    settings = get_settings()

    if settings.get("smtp_enabled") != "1":
        return False, "SMTP désactivé."

    if not to_email:
        return False, "Aucun destinataire."

    host = settings.get("smtp_host", "")
    port = int(settings.get("smtp_port", "587") or 587)
    user = settings.get("smtp_user", "")
    password = settings.get("smtp_password", "")
    from_email = settings.get("smtp_from") or user
    use_tls = settings.get("smtp_tls", "1") == "1"

    if not host or not from_email:
        return False, "Configuration SMTP incomplète."

    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg.set_content(body)

    try:
        if use_tls:
            context = ssl.create_default_context()
            with smtplib.SMTP(host, port, timeout=20) as server:
                server.starttls(context=context)
                if user and password:
                    server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP_SSL(host, port, timeout=20) as server:
                if user and password:
                    server.login(user, password)
                server.send_message(msg)

        print("EMAIL OK:", to_email, subject)
        return True, "Email envoyé avec succès."

    except Exception as e:
        print("EMAIL ERREUR:", str(e))
        return False, str(e)
