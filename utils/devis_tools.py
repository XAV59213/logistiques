from pathlib import Path
import sqlite3
import uuid
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

BASE_DIR = Path("/opt/logistique-pro")
DB_PATH = BASE_DIR / "data" / "demandes.db"
SIGNED_DIR = BASE_DIR / "assets/devis_signes"

SIGNED_DIR.mkdir(parents=True, exist_ok=True)


def connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_devis_columns():
    conn = connect()
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(demandes)")
    cols = [r["name"] for r in cur.fetchall()]

    needed = {
        "numero_devis": "TEXT",
        "devis_valide": "INTEGER DEFAULT 0",
        "devis_valide_at": "TEXT",
        "devis_signe_path": "TEXT",
        "devis_signe_uploaded_at": "TEXT",
        "devis_signe_valide": "INTEGER DEFAULT 0",
        "devis_signe_valide_at": "TEXT",
    }

    for col, typ in needed.items():
        if col not in cols:
            cur.execute(f"ALTER TABLE demandes ADD COLUMN {col} {typ}")

    conn.commit()
    conn.close()


def ensure_devis_number(demande_id):
    ensure_devis_columns()

    numero = f"DEV-{datetime.now().year}-{int(demande_id):06d}"

    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "UPDATE demandes SET numero_devis = COALESCE(numero_devis, ?) WHERE id = ?",
        (numero, int(demande_id)),
    )
    conn.commit()
    conn.close()

    return numero


def save_signed_devis(file, demande_id):
    ensure_devis_columns()

    ext = Path(file.name).suffix.lower()
    filename = f"devis_signe_{demande_id}_{uuid.uuid4().hex}{ext}"
    path = SIGNED_DIR / filename

    with open(path, "wb") as f:
        f.write(file.getbuffer())

    rel = str(path.relative_to(BASE_DIR))

    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        UPDATE demandes
        SET devis_signe_path = ?,
            devis_signe_uploaded_at = ?,
            statut = 'Devis signé reçu'
        WHERE id = ?
    """, (
        rel,
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        int(demande_id),
    ))

    conn.commit()
    conn.close()

    return rel


def generate_devis_pdf(demande, lignes=None):
    numero = ensure_devis_number(demande["id"])

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4

    y = h - 50

    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, y, "DEVIS")
    y -= 30

    c.setFont("Helvetica", 11)
    c.drawString(40, y, f"Numéro : {numero}")
    y -= 20

    c.drawString(40, y, f"Demande : #{demande['id']}")
    y -= 20

    c.drawString(40, y, f"Demandeur : {demande.get('demandeur','-')}")
    y -= 20

    c.drawString(40, y, f"Email : {demande.get('email','-')}")
    y -= 20

    c.drawString(40, y, f"Motif : {demande.get('motif','-')}")
    y -= 20

    c.drawString(40, y, f"Lieu : {demande.get('lieu','-')}")
    y -= 20

    c.drawString(40, y, f"Date début : {demande.get('date_debut','-')}")
    y -= 20

    c.drawString(40, y, f"Date fin : {demande.get('date_fin','-')}")
    y -= 40

    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Articles / prestations :")
    y -= 25

    c.setFont("Helvetica", 10)
    c.drawString(40, y, demande.get("articles", "-"))
    y -= 50

    c.drawString(40, y, "Merci de signer ce devis et le transmettre sous 5 jours.")
    y -= 70

    c.drawString(40, y, "Signature précédée de la mention Bon pour accord :")

    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer.getvalue()
