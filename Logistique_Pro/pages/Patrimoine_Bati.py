# pages/Patrimoine_Bati.py

import sqlite3
import csv
import io
from pathlib import Path
from datetime import date, datetime

import streamlit as st

BASE_DIR = Path("/opt/logistique-pro")
DB = BASE_DIR / "data" / "patrimoine_bati.db"
PHOTO_DIR = BASE_DIR / "assets" / "photos" / "patrimoine_bati"
PHOTO_DIR.mkdir(parents=True, exist_ok=True)


def connect():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def load_batiments():
    conn = connect()
    rows = conn.execute("""
        SELECT *
        FROM batiments
        WHERE COALESCE(actif, 1)=1
        ORDER BY categorie, secteur, COALESCE(numero, 9999), nom
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_types():
    conn = connect()
    rows = conn.execute("""
        SELECT *
        FROM entretien_types
        WHERE COALESCE(actif, 1)=1
        ORDER BY nom
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_entretiens(batiment_id=None):
    conn = connect()
    params = []
    where = ""

    if batiment_id:
        where = "WHERE e.batiment_id=?"
        params.append(int(batiment_id))

    rows = conn.execute(f"""
        SELECT
            e.*,
            b.nom AS batiment_nom,
            b.numero AS batiment_numero,
            b.categorie AS batiment_categorie
        FROM batiment_entretiens e
        JOIN batiments b ON b.id=e.batiment_id
        {where}
        ORDER BY COALESCE(e.date_prochain, '9999-12-31'), b.nom, e.type_entretien
    """, params).fetchall()

    conn.close()
    return [dict(r) for r in rows]


def save_photo(uploaded_file, batiment_name):
    if uploaded_file is None:
        return ""

    safe = "".join(c if c.isalnum() else "_" for c in batiment_name.lower()).strip("_")
    ext = Path(uploaded_file.name).suffix.lower() or ".jpg"
    path = PHOTO_DIR / f"{safe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"

    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return str(path)


def days_until(value):
    if not value:
        return None
    try:
        d = datetime.strptime(str(value), "%Y-%m-%d").date()
        return (d - date.today()).days
    except Exception:
        return None


def statut_entretien(date_prochain, statut):
    delta = days_until(date_prochain)

    if delta is None:
        return statut or "À planifier"
    if delta < 0:
        return "En retard"
    if delta <= 30:
        return "À prévoir"
    return statut or "Planifié"



def load_controles_for_batiment(batiment_id):
    conn = connect()
    rows = conn.execute("""
        SELECT
            c.id,
            c.identifiant_activite,
            c.reference,
            c.domaine,
            COALESCE(c.date_intervention, c.date_debut, '') AS date_intervention,
            c.date_debut,
            c.statut,
            c.nom_site,
            c.ville_site,
            c.libelle_prestation,
            c.organisme,
            c.nombre_documents,
            ca.nom AS campagne_nom,
            ca.organisme AS campagne_organisme
        FROM controle_batiments c
        LEFT JOIN controle_campagnes ca ON ca.id = c.campagne_id
        WHERE COALESCE(c.actif, 1)=1
          AND c.batiment_id=?
        ORDER BY
            CASE
                WHEN COALESCE(c.date_intervention, c.date_debut, '') = '' THEN '9999-12-31'
                WHEN instr(COALESCE(c.date_intervention, c.date_debut, ''), '/') > 0
                    THEN substr(COALESCE(c.date_intervention, c.date_debut, ''), 7, 4) || '-' ||
                         substr(COALESCE(c.date_intervention, c.date_debut, ''), 4, 2) || '-' ||
                         substr(COALESCE(c.date_intervention, c.date_debut, ''), 1, 2)
                ELSE COALESCE(c.date_intervention, c.date_debut, '')
            END,
            c.domaine,
            c.reference
    """, (int(batiment_id),)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def render_controles_for_batiment(batiment_id):
    controles = load_controles_for_batiment(batiment_id)

    st.markdown("#### 📆 Liste des interventions de contrôle du bâtiment")

    if not controles:
        st.caption("Aucune intervention de contrôle rattachée à ce bâtiment.")
        return

    rows = []

    for c in controles:
        rows.append({
            "Date intervention": c.get("date_intervention") or c.get("date_debut") or "",
            "Statut": c.get("statut") or "",
            "Domaine": c.get("domaine") or "",
            "Organisme": c.get("organisme") or c.get("campagne_organisme") or "",
            "Campagne": c.get("campagne_nom") or "",
            "Site importé": c.get("nom_site") or "",
            "Référence": c.get("reference") or "",
            "Identifiant": c.get("identifiant_activite") or "",
            "Prestation": c.get("libelle_prestation") or "",
            "Documents": c.get("nombre_documents") or 0,
        })

    st.dataframe(rows, width="stretch", hide_index=True)


def render_liste():
    st.subheader("📋 Liste des bâtiments")

    batiments = load_batiments()

    if not batiments:
        st.warning("Aucun bâtiment enregistré.")
        return

    c1, c2, c3 = st.columns(3)

    categories = sorted(set(b["categorie"] for b in batiments if b.get("categorie")))
    secteurs = sorted(set(b["secteur"] for b in batiments if b.get("secteur")))

    with c1:
        search = st.text_input("Recherche", placeholder="Nom, numéro, secteur...")

    with c2:
        cat = st.selectbox("Catégorie", ["Toutes"] + categories, key="patrimoine_liste_categorie")

    with c3:
        secteur = st.selectbox("Secteur", ["Tous"] + secteurs, key="patrimoine_liste_secteur")

    filtered = batiments

    if search:
        s = search.lower()
        filtered = [
            b for b in filtered
            if s in str(b.get("nom", "")).lower()
            or s in str(b.get("numero", "")).lower()
            or s in str(b.get("secteur", "")).lower()
            or s in str(b.get("adresse", "")).lower()
        ]

    if cat != "Toutes":
        filtered = [b for b in filtered if b.get("categorie") == cat]

    if secteur != "Tous":
        filtered = [b for b in filtered if b.get("secteur") == secteur]

    st.metric("Bâtiments affichés", len(filtered))

    rows = []
    for b in filtered:
        rows.append({
            "ID": b.get("id"),
            "N°": b.get("numero"),
            "Nom": b.get("nom"),
            "Catégorie": b.get("categorie"),
            "Secteur": b.get("secteur"),
            "Adresse": b.get("adresse"),
        })

    st.dataframe(rows, width="stretch", hide_index=True)

    for b in filtered:
        with st.expander(f"{b.get('numero') or ''} - {b.get('nom')}"):
            col_photo, col_info = st.columns([1, 2])

            with col_photo:
                photo = b.get("photo_path") or ""
                if photo and Path(photo).exists():
                    st.image(photo, width="stretch")
                else:
                    st.info("Aucune photo")

            with col_info:
                st.write(f"**Catégorie :** {b.get('categorie')}")
                st.write(f"**Secteur :** {b.get('secteur')}")
                st.write(f"**Adresse :** {b.get('adresse') or 'À compléter'}")
                st.write(f"**Responsable :** {b.get('responsable') or 'À compléter'}")
                st.write(f"**Téléphone :** {b.get('telephone') or 'À compléter'}")

            st.markdown("#### 🛠️ Liste des entretiens enregistrés")

            entretiens = load_entretiens(b.get("id"))
            if entretiens:
                rows_e = []
                for e in entretiens:
                    rows_e.append({
                        "Entretien": e.get("type_entretien"),
                        "Dernier": e.get("date_dernier"),
                        "Prochain": e.get("date_prochain"),
                        "Statut": statut_entretien(e.get("date_prochain"), e.get("statut")),
                        "Prestataire": e.get("prestataire"),
                    })
                st.dataframe(rows_e, width="stretch", hide_index=True)
            else:
                st.caption("Aucun entretien enregistré.")

            render_controles_for_batiment(b.get("id"))


def render_ajouter():
    st.subheader("➕ Ajouter un bâtiment")

    with st.form("add_batiment", clear_on_submit=True):
        c1, c2 = st.columns(2)

        with c1:
            numero = st.text_input("N°")
            nom = st.text_input("Nom *")
            categorie = st.selectbox("Catégorie", ["Groupes scolaires", "Bâtiments sportifs", "Bâtiments autres", "Salle", "École", "Autre"], key="patrimoine_add_categorie")
            secteur = st.text_input("Secteur")

        with c2:
            adresse = st.text_input("Adresse")
            responsable = st.text_input("Responsable")
            telephone = st.text_input("Téléphone")
            email = st.text_input("Email")

        photo = st.file_uploader("Photo", type=["jpg", "jpeg", "png", "webp"])
        notes = st.text_area("Notes")

        submit = st.form_submit_button("Ajouter", width="stretch")

        if submit:
            if not nom.strip():
                st.error("Le nom est obligatoire.")
                return

            photo_path = save_photo(photo, nom)

            conn = connect()
            conn.execute("""
                INSERT INTO batiments
                (numero, nom, categorie, secteur, adresse, photo_path, responsable, telephone, email, notes, actif, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                int(numero) if numero.strip() else None,
                nom.strip(),
                categorie,
                secteur.strip(),
                adresse.strip(),
                photo_path,
                responsable.strip(),
                telephone.strip(),
                email.strip(),
                notes.strip(),
            ))
            conn.commit()
            conn.close()

            st.success("Bâtiment ajouté.")
            st.rerun()


def render_modifier():
    st.subheader("✏️ Modifier un bâtiment")

    batiments = load_batiments()

    if not batiments:
        st.info("Aucun bâtiment.")
        return

    choices = {f"{b.get('numero') or ''} - {b.get('nom')}": b for b in batiments}
    label = st.selectbox("Bâtiment", list(choices.keys()), key="patrimoine_edit_batiment")
    b = choices[label]

    with st.form("edit_batiment"):
        c1, c2 = st.columns(2)

        with c1:
            numero = st.text_input("N°", value=str(b.get("numero") or ""))
            nom = st.text_input("Nom *", value=b.get("nom") or "")
            categorie = st.text_input("Catégorie", value=b.get("categorie") or "")
            secteur = st.text_input("Secteur", value=b.get("secteur") or "")

        with c2:
            adresse = st.text_input("Adresse", value=b.get("adresse") or "")
            responsable = st.text_input("Responsable", value=b.get("responsable") or "")
            telephone = st.text_input("Téléphone", value=b.get("telephone") or "")
            email = st.text_input("Email", value=b.get("email") or "")

        current_photo = b.get("photo_path") or ""
        if current_photo and Path(current_photo).exists():
            st.image(current_photo, width=250)

        photo = st.file_uploader("Remplacer photo", type=["jpg", "jpeg", "png", "webp"])
        notes = st.text_area("Notes", value=b.get("notes") or "")

        submit = st.form_submit_button("Enregistrer", width="stretch")

        if submit:
            if not nom.strip():
                st.error("Le nom est obligatoire.")
                return

            photo_path = save_photo(photo, nom) if photo else current_photo

            conn = connect()
            conn.execute("""
                UPDATE batiments
                SET numero=?, nom=?, categorie=?, secteur=?, adresse=?, photo_path=?,
                    responsable=?, telephone=?, email=?, notes=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (
                int(numero) if numero.strip() else None,
                nom.strip(),
                categorie.strip(),
                secteur.strip(),
                adresse.strip(),
                photo_path,
                responsable.strip(),
                telephone.strip(),
                email.strip(),
                notes.strip(),
                b["id"],
            ))
            conn.commit()
            conn.close()

            st.success("Bâtiment modifié.")
            st.rerun()


def render_supprimer():
    st.subheader("🗑️ Supprimer un bâtiment")

    batiments = load_batiments()

    if not batiments:
        st.info("Aucun bâtiment.")
        return

    choices = {f"{b.get('numero') or ''} - {b.get('nom')}": b for b in batiments}
    label = st.selectbox("Bâtiment", list(choices.keys()), key="patrimoine_delete_batiment")
    b = choices[label]

    hard = st.checkbox("Suppression définitive")
    confirm = st.checkbox("Je confirme")

    if st.button("Supprimer", disabled=not confirm, width="stretch"):
        conn = connect()
        if hard:
            conn.execute("DELETE FROM batiment_entretiens WHERE batiment_id=?", (b["id"],))
            conn.execute("DELETE FROM batiments WHERE id=?", (b["id"],))
        else:
            conn.execute("UPDATE batiments SET actif=0, updated_at=CURRENT_TIMESTAMP WHERE id=?", (b["id"],))
        conn.commit()
        conn.close()
        st.success("Bâtiment supprimé.")
        st.rerun()


def render_entretiens():
    st.subheader("🛠️ Entretiens")

    batiments = load_batiments()
    types = load_types()

    if not batiments:
        st.info("Aucun bâtiment.")
        return

    tab1, tab2 = st.tabs(["📋 Liste", "➕ Ajouter"])

    with tab1:
        entretiens = load_entretiens()
        rows = []
        for e in entretiens:
            rows.append({
                "Bâtiment": e.get("batiment_nom"),
                "N°": e.get("batiment_numero"),
                "Entretien": e.get("type_entretien"),
                "Dernier": e.get("date_dernier"),
                "Prochain": e.get("date_prochain"),
                "Statut": statut_entretien(e.get("date_prochain"), e.get("statut")),
                "Prestataire": e.get("prestataire"),
            })

        if rows:
            st.dataframe(rows, width="stretch", hide_index=True)
        else:
            st.info("Aucun entretien.")

    with tab2:
        choices_b = {f"{b.get('numero') or ''} - {b.get('nom')}": b for b in batiments}
        type_names = [t["nom"] for t in types]

        with st.form("add_entretien", clear_on_submit=True):
            bat_label = st.selectbox("Bâtiment", list(choices_b.keys()), key="patrimoine_entretien_batiment")
            type_entretien = st.selectbox("Type", type_names, key="patrimoine_entretien_type")

            c1, c2, c3 = st.columns(3)
            with c1:
                dernier = st.date_input("Date dernier contrôle", value=None)
            with c2:
                prochain = st.date_input("Date prochain contrôle", value=None)
            with c3:
                periodicite = st.number_input("Périodicité mois", min_value=1, value=12)

            prestataire = st.text_input("Prestataire")
            statut = st.selectbox("Statut", ["À planifier", "Planifié", "Fait", "À prévoir", "En retard"], key="patrimoine_entretien_statut")
            notes = st.text_area("Notes")

            submit = st.form_submit_button("Ajouter entretien", width="stretch")

            if submit:
                conn = connect()
                conn.execute("""
                    INSERT INTO batiment_entretiens
                    (batiment_id, type_entretien, date_dernier, date_prochain, periodicite_mois, prestataire, statut, notes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (
                    choices_b[bat_label]["id"],
                    type_entretien,
                    dernier.strftime("%Y-%m-%d") if dernier else "",
                    prochain.strftime("%Y-%m-%d") if prochain else "",
                    int(periodicite),
                    prestataire.strip(),
                    statut,
                    notes.strip(),
                ))
                conn.commit()
                conn.close()
                st.success("Entretien ajouté.")
                st.rerun()



def normalize_text(value):
    return " ".join(str(value or "").strip().split())


def normalize_site_name(value):
    text = normalize_text(value).lower()
    replacements = {
        "ecole": "école",
        "maternelle": "maternelle",
        "primaire": "primaire",
        "jules henri lengrand": "jules henri lengrand",
        "hurez st nicolas": "hurez st nicolas",
        "saint nicolas": "st nicolas",
        "salle des fetes": "salle des fêtes",
        "ccas": "c.c.a.s",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def find_batiment_id_by_site(nom_site):
    nom_site_norm = normalize_site_name(nom_site)

    if not nom_site_norm:
        return None

    batiments = load_batiments()

    best_id = None
    best_score = 0

    for b in batiments:
        nom = normalize_site_name(b.get("nom", ""))
        secteur = normalize_site_name(b.get("secteur", ""))

        score = 0

        if nom and nom in nom_site_norm:
            score += 4

        if nom_site_norm and nom_site_norm in nom:
            score += 4

        if secteur and secteur in nom_site_norm:
            score += 2

        for token in nom_site_norm.split():
            if len(token) > 3 and token in nom:
                score += 1

        if score > best_score:
            best_score = score
            best_id = b.get("id")

    return best_id if best_score >= 2 else None


def load_controle_campagnes():
    conn = connect()
    rows = conn.execute("""
        SELECT *
        FROM controle_campagnes
        WHERE COALESCE(actif, 1)=1
        ORDER BY created_at DESC, nom
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_controles():
    conn = connect()
    rows = conn.execute("""
        SELECT
            c.*,
            ca.nom AS campagne_nom,
            ca.organisme AS campagne_organisme,
            b.nom AS batiment_nom,
            b.numero AS batiment_numero,
            b.categorie AS batiment_categorie,
            b.secteur AS batiment_secteur
        FROM controle_batiments c
        LEFT JOIN controle_campagnes ca ON ca.id = c.campagne_id
        LEFT JOIN batiments b ON b.id = c.batiment_id
        WHERE COALESCE(c.actif, 1)=1
        ORDER BY COALESCE(c.date_intervention, c.date_debut, '9999-12-31'), c.nom_site
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_controle_campagne(nom, organisme, domaine, description):
    nom = normalize_text(nom)

    if not nom:
        return False, "Le nom de la campagne est obligatoire."

    conn = connect()
    cur = conn.cursor()

    exists = cur.execute("""
        SELECT id FROM controle_campagnes
        WHERE LOWER(TRIM(nom)) = LOWER(?)
    """, (nom,)).fetchone()

    if exists:
        conn.close()
        return False, "Cette campagne existe déjà."

    cur.execute("""
        INSERT INTO controle_campagnes
        (nom, organisme, domaine, description, actif, created_at, updated_at)
        VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, (
        nom,
        normalize_text(organisme),
        normalize_text(domaine),
        normalize_text(description),
    ))

    conn.commit()
    conn.close()

    return True, "Campagne de contrôle ajoutée."


def add_controle_batiment(
    campagne_id,
    batiment_id,
    identifiant_activite,
    reference,
    domaine,
    date_debut,
    date_intervention,
    statut,
    nom_site,
    ville_site,
    libelle_prestation,
    livrables,
    nombre_documents,
    organisme,
    notes,
):
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO controle_batiments
        (
            campagne_id,
            batiment_id,
            identifiant_activite,
            reference,
            domaine,
            date_debut,
            date_intervention,
            statut,
            nom_site,
            ville_site,
            libelle_prestation,
            livrables,
            nombre_documents,
            organisme,
            notes,
            actif,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, (
        int(campagne_id) if campagne_id else None,
        int(batiment_id) if batiment_id else None,
        normalize_text(identifiant_activite),
        normalize_text(reference),
        normalize_text(domaine),
        normalize_text(date_debut),
        normalize_text(date_intervention or date_debut),
        normalize_text(statut),
        normalize_text(nom_site),
        normalize_text(ville_site),
        normalize_text(libelle_prestation),
        int(livrables or 0),
        int(nombre_documents or 0),
        normalize_text(organisme),
        normalize_text(notes),
    ))

    conn.commit()
    conn.close()

    return True, "Contrôle ajouté."


def delete_controle_batiment(controle_id):
    conn = connect()
    conn.execute("""
        UPDATE controle_batiments
        SET actif=0, updated_at=CURRENT_TIMESTAMP
        WHERE id=?
    """, (int(controle_id),))
    conn.commit()
    conn.close()
    return True, "Contrôle supprimé."


def detect_csv_delimiter(sample):
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\\t,")
        return dialect.delimiter
    except Exception:
        return ";"


def parse_csv_uploaded(uploaded_file):
    raw = uploaded_file.getvalue()

    for encoding in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
        try:
            text = raw.decode(encoding)
            break
        except Exception:
            text = None

    if text is None:
        raise ValueError("Impossible de lire le fichier CSV.")

    delimiter = detect_csv_delimiter(text[:2048])
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)

    rows = []

    for row in reader:
        clean_row = {}
        for k, v in row.items():
            key = normalize_text(k)
            clean_row[key] = normalize_text(v)
        rows.append(clean_row)

    return rows


def get_csv_value(row, possible_names):
    lower_map = {str(k).lower().strip(): v for k, v in row.items()}

    for name in possible_names:
        key = name.lower().strip()
        if key in lower_map:
            return lower_map[key]

    return ""


def import_controles_from_rows(rows, campagne_id, organisme_default=""):
    added = 0
    skipped = 0

    for row in rows:
        identifiant = get_csv_value(row, ["Identifiant d'activité", "Identifiant activite", "ID", "Identifiant"])
        reference = get_csv_value(row, ["Référence", "Reference"])
        domaine = get_csv_value(row, ["Domaine"])
        date_debut = get_csv_value(row, ["Date début", "Date debut", "Date"])
        date_intervention = get_csv_value(row, ["Date d'intervention", "Date intervention", "Date début", "Date debut", "Date"])
        statut = get_csv_value(row, ["Statut"])
        nom_site = get_csv_value(row, ["Nom site", "Site", "Bâtiment", "Batiment"])
        ville_site = get_csv_value(row, ["Ville site", "Ville"])
        libelle = get_csv_value(row, ["Libellé prestation", "Libelle prestation", "Prestation"])
        livrables = get_csv_value(row, ["Livrables"])
        documents = get_csv_value(row, ["Nombre de documents", "Documents"])

        if not nom_site and not identifiant and not reference:
            skipped += 1
            continue

        batiment_id = find_batiment_id_by_site(nom_site)

        add_controle_batiment(
            campagne_id=campagne_id,
            batiment_id=batiment_id,
            identifiant_activite=identifiant,
            reference=reference,
            domaine=domaine,
            date_debut=date_debut,
            date_intervention=date_intervention,
            statut=statut,
            nom_site=nom_site,
            ville_site=ville_site,
            libelle_prestation=libelle,
            livrables=int(livrables or 0) if str(livrables or "0").isdigit() else 0,
            nombre_documents=int(documents or 0) if str(documents or "0").isdigit() else 0,
            organisme=organisme_default,
            notes="Import CSV",
        )

        added += 1

    return added, skipped


def render_controles_batiments():
    st.subheader("📅 Contrôles des bâtiments")
    st.caption("Import et suivi des contrôles : Veritas, électricité, sécurité, désenfumage, extincteurs, etc.")

    campagnes = load_controle_campagnes()
    controles = load_controles()
    batiments = load_batiments()

    tab_liste, tab_add, tab_import, tab_campagne = st.tabs([
        "📋 Liste des contrôles",
        "➕ Ajouter un contrôle",
        "📥 Import CSV",
        "⚙️ Campagnes",
    ])

    with tab_liste:
        c1, c2, c3, c4 = st.columns(4)

        domaines = sorted(set(c.get("domaine", "") for c in controles if c.get("domaine")))
        statuts = sorted(set(c.get("statut", "") for c in controles if c.get("statut")))
        organismes = sorted(set((c.get("organisme") or c.get("campagne_organisme") or "") for c in controles if (c.get("organisme") or c.get("campagne_organisme"))))

        with c1:
            search = st.text_input("Recherche", key="controles_search", placeholder="Site, référence, prestation...")

        with c2:
            domaine_filter = st.selectbox("Domaine", ["Tous"] + domaines, key="controles_domaine_filter")

        with c3:
            statut_filter = st.selectbox("Statut", ["Tous"] + statuts, key="controles_statut_filter")

        with c4:
            organisme_filter = st.selectbox("Organisme", ["Tous"] + organismes, key="controles_organisme_filter")

        filtered = controles

        if search:
            s = search.lower()
            filtered = [
                c for c in filtered
                if s in str(c.get("nom_site", "")).lower()
                or s in str(c.get("batiment_nom", "")).lower()
                or s in str(c.get("reference", "")).lower()
                or s in str(c.get("libelle_prestation", "")).lower()
                or s in str(c.get("identifiant_activite", "")).lower()
            ]

        if domaine_filter != "Tous":
            filtered = [c for c in filtered if c.get("domaine") == domaine_filter]

        if statut_filter != "Tous":
            filtered = [c for c in filtered if c.get("statut") == statut_filter]

        if organisme_filter != "Tous":
            filtered = [
                c for c in filtered
                if (c.get("organisme") or c.get("campagne_organisme") or "") == organisme_filter
            ]

        non_rapproches = len([c for c in filtered if not c.get("batiment_id")])

        m1, m2, m3 = st.columns(3)
        m1.metric("Contrôles", len(filtered))
        m2.metric("Non rapprochés bâtiment", non_rapproches)
        m3.metric("Campagnes", len(campagnes))

        rows = []

        for c in filtered:
            rows.append({
                "Date intervention": c.get("date_intervention") or c.get("date_debut", ""),
                "Statut": c.get("statut", ""),
                "Domaine": c.get("domaine", ""),
                "Site importé": c.get("nom_site", ""),
                "Bâtiment lié": c.get("batiment_nom", "") or "Non rapproché",
                "Référence": c.get("reference", ""),
                "Prestation": c.get("libelle_prestation", ""),
                "Organisme": c.get("organisme") or c.get("campagne_organisme") or "",
                "Documents": c.get("nombre_documents", 0),
            })

        if rows:
            st.dataframe(rows, width="stretch", hide_index=True)
        else:
            st.info("Aucun contrôle trouvé.")

        if filtered:
            with st.expander("🗑️ Supprimer une ligne de contrôle"):
                choices = {
                    f"{c.get('date_intervention') or c.get('date_debut')} - {c.get('nom_site')} - {c.get('reference')}": c.get("id")
                    for c in filtered
                }
                selected = st.selectbox("Contrôle à supprimer", list(choices.keys()), key="controle_delete_choice")
                confirm = st.checkbox("Je confirme la suppression", key="controle_delete_confirm")

                if st.button("Supprimer le contrôle", disabled=not confirm, key="controle_delete_btn", width="stretch"):
                    ok, msg = delete_controle_batiment(choices[selected])
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    with tab_add:
        st.markdown("### Ajouter un contrôle manuellement")

        campagne_choices = {c["nom"]: c["id"] for c in campagnes}
        batiment_choices = {
            f"{b.get('numero') or ''} - {b.get('nom')}": b.get("id")
            for b in batiments
        }

        with st.form("controle_add_form", clear_on_submit=True):
            c1, c2 = st.columns(2)

            with c1:
                campagne_label = st.selectbox("Campagne", list(campagne_choices.keys()), key="controle_add_campagne")
                batiment_label = st.selectbox("Bâtiment lié", ["Non lié"] + list(batiment_choices.keys()), key="controle_add_batiment")
                identifiant = st.text_input("Identifiant d'activité")
                reference = st.text_input("Référence")
                domaine = st.text_input("Domaine", value="Électricité")
                date_debut = st.text_input("Date début", placeholder="13/05/2026 ou 2026-05-13")
                date_intervention = st.text_input("Date d'intervention", value=date_debut, placeholder="13/05/2026")

            with c2:
                statut = st.selectbox("Statut", ["Planifiée", "Réalisée", "À reprogrammer", "Annulée"], key="controle_add_statut")
                nom_site = st.text_input("Nom site")
                ville_site = st.text_input("Ville site", value="MARLY")
                organisme = st.text_input("Organisme", value="Veritas")
                livrables = st.number_input("Livrables", min_value=0, value=0, step=1)
                documents = st.number_input("Nombre de documents", min_value=0, value=0, step=1)

            libelle = st.text_area("Libellé prestation", value="Vérification périodique annuelle des installations électriques")
            notes = st.text_area("Notes")

            submit = st.form_submit_button("➕ Ajouter le contrôle", width="stretch")

            if submit:
                batiment_id = None if batiment_label == "Non lié" else batiment_choices[batiment_label]

                ok, msg = add_controle_batiment(
                    campagne_id=campagne_choices[campagne_label],
                    batiment_id=batiment_id,
                    identifiant_activite=identifiant,
                    reference=reference,
                    domaine=domaine,
                    date_debut=date_debut,
                    date_intervention=date_intervention,
                    statut=statut,
                    nom_site=nom_site,
                    ville_site=ville_site,
                    libelle_prestation=libelle,
                    livrables=livrables,
                    nombre_documents=documents,
                    organisme=organisme,
                    notes=notes,
                )

                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    with tab_import:
        st.markdown("### Importer une liste de contrôles")

        st.info(
            "Pour le moment, l'import direct Excel .xlsx n'est pas utilisé afin d'éviter une dépendance supplémentaire. "
            "Dans Excel : Fichier → Enregistrer sous → CSV UTF-8, puis importe le CSV ici."
        )

        campagne_choices = {c["nom"]: c["id"] for c in campagnes}

        if not campagne_choices:
            st.warning("Crée d'abord une campagne.")
        else:
            campagne_label = st.selectbox("Campagne d'import", list(campagne_choices.keys()), key="controle_import_campagne")
            organisme_default = st.text_input("Organisme par défaut", value="Veritas", key="controle_import_organisme")
            uploaded = st.file_uploader("Fichier CSV des contrôles", type=["csv"], key="controle_import_csv")

            if uploaded is not None:
                try:
                    rows = parse_csv_uploaded(uploaded)
                    st.success(f"{len(rows)} ligne(s) détectée(s) dans le fichier CSV.")

                    preview = rows[:10]
                    if preview:
                        st.dataframe(preview, width="stretch")

                    confirm = st.checkbox("Je confirme l'import", key="controle_import_confirm")

                    if st.button("📥 Importer les contrôles", disabled=not confirm, key="controle_import_btn", width="stretch"):
                        added, skipped = import_controles_from_rows(
                            rows,
                            campagne_choices[campagne_label],
                            organisme_default,
                        )
                        st.success(f"Import terminé : {added} ligne(s) ajoutée(s), {skipped} ignorée(s).")
                        st.rerun()

                except Exception as e:
                    st.error(f"Erreur import CSV : {e}")

    with tab_campagne:
        st.markdown("### Campagnes de contrôle")

        rows = []
        for c in campagnes:
            rows.append({
                "Nom": c.get("nom", ""),
                "Organisme": c.get("organisme", ""),
                "Domaine": c.get("domaine", ""),
                "Description": c.get("description", ""),
            })

        st.dataframe(rows, width="stretch", hide_index=True)

        with st.form("controle_campagne_add_form", clear_on_submit=True):
            nom = st.text_input("Nom de la campagne", placeholder="Veritas - contrôle électrique 2026")
            organisme = st.text_input("Organisme", value="Veritas")
            domaine = st.text_input("Domaine", value="Électricité")
            description = st.text_area("Description", value="Vérification périodique annuelle des installations électriques")

            submit = st.form_submit_button("➕ Ajouter la campagne", width="stretch")

            if submit:
                ok, msg = add_controle_campagne(nom, organisme, domaine, description)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)



def render_liste_interventions_controle():
    st.subheader("📆 Liste des interventions de contrôle")
    st.caption("Planning global des contrôles réglementaires des bâtiments.")

    conn = connect()
    rows_db = conn.execute("""
        SELECT
            c.id,
            c.identifiant_activite,
            c.reference,
            c.domaine,
            COALESCE(c.date_intervention, c.date_debut, '') AS date_intervention,
            c.date_debut,
            c.statut,
            c.nom_site,
            c.ville_site,
            c.libelle_prestation,
            c.livrables,
            c.nombre_documents,
            c.organisme,
            c.notes,
            ca.nom AS campagne_nom,
            ca.organisme AS campagne_organisme,
            b.numero AS batiment_numero,
            b.nom AS batiment_nom,
            b.categorie AS batiment_categorie,
            b.secteur AS batiment_secteur,
            b.adresse AS batiment_adresse,
            b.photo_path AS batiment_photo
        FROM controle_batiments c
        LEFT JOIN controle_campagnes ca ON ca.id = c.campagne_id
        LEFT JOIN batiments b ON b.id = c.batiment_id
        WHERE COALESCE(c.actif, 1)=1
        ORDER BY
            CASE
                WHEN COALESCE(c.date_intervention, c.date_debut, '') = '' THEN '9999-12-31'
                WHEN instr(COALESCE(c.date_intervention, c.date_debut, ''), '/') > 0
                    THEN substr(COALESCE(c.date_intervention, c.date_debut, ''), 7, 4) || '-' ||
                         substr(COALESCE(c.date_intervention, c.date_debut, ''), 4, 2) || '-' ||
                         substr(COALESCE(c.date_intervention, c.date_debut, ''), 1, 2)
                ELSE COALESCE(c.date_intervention, c.date_debut, '')
            END,
            b.nom,
            c.nom_site
    """).fetchall()
    conn.close()

    controles = [dict(r) for r in rows_db]

    if not controles:
        st.info("Aucune intervention de contrôle enregistrée.")
        return

    domaines = sorted(set(str(c.get("domaine") or "").strip() for c in controles if str(c.get("domaine") or "").strip()))
    statuts = sorted(set(str(c.get("statut") or "").strip() for c in controles if str(c.get("statut") or "").strip()))
    categories = sorted(set(str(c.get("batiment_categorie") or "").strip() for c in controles if str(c.get("batiment_categorie") or "").strip()))
    organismes = sorted(set(str(c.get("organisme") or c.get("campagne_organisme") or "").strip() for c in controles if str(c.get("organisme") or c.get("campagne_organisme") or "").strip()))

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        search = st.text_input(
            "🔍 Recherche",
            key="interventions_controle_search",
            placeholder="Bâtiment, site, référence..."
        )

    with col2:
        domaine_filter = st.selectbox(
            "Domaine",
            ["Tous"] + domaines,
            key="interventions_controle_domaine"
        )

    with col3:
        statut_filter = st.selectbox(
            "Statut",
            ["Tous"] + statuts,
            key="interventions_controle_statut"
        )

    with col4:
        categorie_filter = st.selectbox(
            "Catégorie bâtiment",
            ["Toutes"] + categories,
            key="interventions_controle_categorie"
        )

    col5, col6 = st.columns(2)

    with col5:
        organisme_filter = st.selectbox(
            "Organisme",
            ["Tous"] + organismes,
            key="interventions_controle_organisme"
        )

    with col6:
        uniquement_non_lies = st.checkbox(
            "Afficher uniquement les contrôles non rattachés à un bâtiment",
            key="interventions_controle_non_lies"
        )

    filtered = controles

    if search:
        q = search.lower().strip()
        filtered = [
            c for c in filtered
            if q in str(c.get("batiment_nom") or "").lower()
            or q in str(c.get("nom_site") or "").lower()
            or q in str(c.get("reference") or "").lower()
            or q in str(c.get("identifiant_activite") or "").lower()
            or q in str(c.get("libelle_prestation") or "").lower()
            or q in str(c.get("batiment_adresse") or "").lower()
        ]

    if domaine_filter != "Tous":
        filtered = [c for c in filtered if str(c.get("domaine") or "") == domaine_filter]

    if statut_filter != "Tous":
        filtered = [c for c in filtered if str(c.get("statut") or "") == statut_filter]

    if categorie_filter != "Toutes":
        filtered = [c for c in filtered if str(c.get("batiment_categorie") or "") == categorie_filter]

    if organisme_filter != "Tous":
        filtered = [
            c for c in filtered
            if str(c.get("organisme") or c.get("campagne_organisme") or "") == organisme_filter
        ]

    if uniquement_non_lies:
        filtered = [c for c in filtered if not c.get("batiment_nom")]

    total = len(filtered)
    non_lies = len([c for c in filtered if not c.get("batiment_nom")])
    avec_date = len([c for c in filtered if str(c.get("date_intervention") or "").strip()])
    planifiees = len([c for c in filtered if str(c.get("statut") or "").lower() in ["planifiée", "planifiee", "planifié", "planifie"]])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Interventions", total)
    m2.metric("Avec date", avec_date)
    m3.metric("Planifiées", planifiees)
    m4.metric("Non rattachées", non_lies)

    rows = []
    for c in filtered:
        rows.append({
            "Date intervention": c.get("date_intervention") or c.get("date_debut") or "",
            "Statut": c.get("statut") or "",
            "Domaine": c.get("domaine") or "",
            "Organisme": c.get("organisme") or c.get("campagne_organisme") or "",
            "N° bâtiment": c.get("batiment_numero") or "",
            "Bâtiment patrimoine": c.get("batiment_nom") or "Non rattaché",
            "Catégorie": c.get("batiment_categorie") or "",
            "Secteur": c.get("batiment_secteur") or "",
            "Adresse": c.get("batiment_adresse") or "",
            "Site importé": c.get("nom_site") or "",
            "Référence": c.get("reference") or "",
            "Identifiant": c.get("identifiant_activite") or "",
            "Prestation": c.get("libelle_prestation") or "",
            "Documents": c.get("nombre_documents") or 0,
        })

    st.dataframe(rows, width="stretch", hide_index=True)

    st.divider()

    with st.expander("🏛️ Détail par intervention"):
        for c in filtered:
            title = (
                f"{c.get('date_intervention') or c.get('date_debut') or 'Sans date'}"
                f" — {c.get('batiment_nom') or c.get('nom_site') or 'Site inconnu'}"
                f" — {c.get('domaine') or ''}"
            )

            with st.container(border=True):
                st.markdown(f"### {title}")

                c_photo, c_info = st.columns([1, 3])

                with c_photo:
                    photo = c.get("batiment_photo") or ""
                    if photo and Path(photo).exists():
                        st.image(photo, width="stretch")
                    else:
                        st.info("Aucune photo bâtiment.")

                with c_info:
                    st.write(f"**Bâtiment patrimoine :** {c.get('batiment_nom') or 'Non rattaché'}")
                    st.write(f"**N° bâtiment :** {c.get('batiment_numero') or ''}")
                    st.write(f"**Catégorie :** {c.get('batiment_categorie') or ''}")
                    st.write(f"**Secteur :** {c.get('batiment_secteur') or ''}")
                    st.write(f"**Adresse :** {c.get('batiment_adresse') or 'À compléter'}")
                    st.write(f"**Site importé :** {c.get('nom_site') or ''}")
                    st.write(f"**Organisme :** {c.get('organisme') or c.get('campagne_organisme') or ''}")
                    st.write(f"**Référence :** {c.get('reference') or ''}")
                    st.write(f"**Identifiant activité :** {c.get('identifiant_activite') or ''}")
                    st.write(f"**Prestation :** {c.get('libelle_prestation') or ''}")
                    st.write(f"**Statut :** {c.get('statut') or ''}")

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()) if rows else ["Aucune donnée"], delimiter=";")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    st.download_button(
        "📥 Télécharger la liste des interventions CSV",
        data=output.getvalue().encode("utf-8-sig"),
        file_name="interventions_controle_batiments.csv",
        mime="text/csv",
        width="stretch",
        key="download_interventions_controle_csv"
    )



def show():
    st.title("🏛️ Patrimoine bâti")
    st.caption("Gestion des bâtiments, entretiens et contrôles réglementaires")

    user = st.session_state.get("user") or {}
    if str(user.get("role", "")).lower() != "admin":
        st.error("Accès réservé aux administrateurs.")
        st.stop()

    tabs = st.tabs([
        "📋 Liste",
        "➕ Ajouter",
        "✏️ Modifier",
        "🗑️ Supprimer",
        "🛠️ Entretiens",
        "📅 Contrôles bâtiments",
        "📆 Interventions contrôle",
    ])

    with tabs[0]:
        render_liste()

    with tabs[1]:
        render_ajouter()

    with tabs[2]:
        render_modifier()

    with tabs[3]:
        render_supprimer()

    with tabs[4]:
        render_entretiens()

    with tabs[5]:
        if "render_controles_batiments" in globals():
            render_controles_batiments()
        else:
            st.warning("Module Contrôles bâtiments non disponible.")

    with tabs[6]:
        render_liste_interventions_controle()
