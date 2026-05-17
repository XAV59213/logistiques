# -*- coding: utf-8 -*-
from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from .db import DB_PATH, connect, init_db
from .photos import save_photo


def safe_date(value: Any) -> date | None:
    if not value:
        return None

    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def date_to_text(value: date | None) -> str:
    if value is None:
        return ""

    return value.isoformat()


def load_vehicules(include_inactive: bool = False) -> list[dict[str, Any]]:
    init_db()

    where = "" if include_inactive else "WHERE COALESCE(actif, 1)=1"

    conn = connect()
    try:
        rows = conn.execute(
            f"""
            SELECT *
            FROM vehicules
            {where}
            ORDER BY
                COALESCE(service, ''),
                COALESCE(categorie, ''),
                COALESCE(immatriculation, ''),
                id DESC
            """
        ).fetchall()

        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_vehicule_by_id(vehicule_id: int) -> dict[str, Any] | None:
    init_db()

    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM vehicules WHERE id=?",
            (int(vehicule_id),),
        ).fetchone()

        return dict(row) if row else None
    finally:
        conn.close()


def add_vehicule(data: dict[str, Any]) -> None:
    init_db()

    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO vehicules (
                nom,
                immatriculation,
                marque,
                modele,
                categorie,
                service,
                energie,
                kilometrage_actuel,
                date_mise_en_service,
                date_ct,
                assurance,
                statut,
                actif,
                photo_path,
                notes,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("nom"),
                data.get("immatriculation"),
                data.get("marque"),
                data.get("modele"),
                data.get("categorie"),
                data.get("service"),
                data.get("energie"),
                int(data.get("kilometrage_actuel") or 0),
                data.get("date_mise_en_service"),
                data.get("date_ct"),
                data.get("assurance"),
                data.get("statut") or "Actif",
                1 if data.get("actif", True) else 0,
                data.get("photo_path"),
                data.get("notes"),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def update_vehicule(vehicule_id: int, data: dict[str, Any]) -> None:
    init_db()

    conn = connect()
    try:
        conn.execute(
            """
            UPDATE vehicules
            SET
                nom=?,
                immatriculation=?,
                marque=?,
                modele=?,
                categorie=?,
                service=?,
                energie=?,
                kilometrage_actuel=?,
                date_mise_en_service=?,
                date_ct=?,
                assurance=?,
                statut=?,
                actif=?,
                photo_path=?,
                notes=?,
                updated_at=?
            WHERE id=?
            """,
            (
                data.get("nom"),
                data.get("immatriculation"),
                data.get("marque"),
                data.get("modele"),
                data.get("categorie"),
                data.get("service"),
                data.get("energie"),
                int(data.get("kilometrage_actuel") or 0),
                data.get("date_mise_en_service"),
                data.get("date_ct"),
                data.get("assurance"),
                data.get("statut"),
                1 if data.get("actif") else 0,
                data.get("photo_path"),
                data.get("notes"),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                int(vehicule_id),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def delete_vehicule(vehicule_id: int, hard_delete: bool = False) -> None:
    init_db()

    conn = connect()
    try:
        if hard_delete:
            conn.execute("DELETE FROM vehicule_attributions WHERE vehicule_id=?", (int(vehicule_id),))
            conn.execute("DELETE FROM vehicule_carburants WHERE vehicule_id=?", (int(vehicule_id),))
            conn.execute("DELETE FROM vehicule_entretiens WHERE vehicule_id=?", (int(vehicule_id),))
            conn.execute("DELETE FROM vehicule_kilometrages WHERE vehicule_id=?", (int(vehicule_id),))
            conn.execute("DELETE FROM vehicules WHERE id=?", (int(vehicule_id),))
        else:
            conn.execute(
                """
                UPDATE vehicules
                SET actif=0, statut='Supprimé', updated_at=?
                WHERE id=?
                """,
                (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    int(vehicule_id),
                ),
            )

        conn.commit()
    finally:
        conn.close()


def render_liste() -> None:
    # PATCH80_DISABLED_GARAGE_LIST_TITLE: st.markdown("### 📋 Liste des véhicules")

    vehicules = load_vehicules(include_inactive=True)

    if not vehicules:
        st.warning("Aucun véhicule enregistré dans garage_vehicules.db.")
        return

    df = pd.DataFrame(vehicules)

    c1, c2, c3 = st.columns(3)

    services = []
    categories = []

    if "service" in df:
        services = sorted([x for x in df["service"].dropna().unique().tolist() if str(x).strip()])

    if "categorie" in df:
        categories = sorted([x for x in df["categorie"].dropna().unique().tolist() if str(x).strip()])

    with c1:
        search = st.text_input("🔍 Recherche", key="garage_search")

    with c2:
        service_filter = st.selectbox("Service", ["Tous"] + services, key="garage_service_filter")

    with c3:
        categorie_filter = st.selectbox("Catégorie", ["Toutes"] + categories, key="garage_categorie_filter")

    filtered = df.copy()

    if search:
        query = search.lower()
        mask = pd.Series(False, index=filtered.index)

        for col in ["nom", "immatriculation", "marque", "modele", "service", "categorie", "energie"]:
            if col in filtered.columns:
                mask = mask | filtered[col].astype(str).str.lower().str.contains(query, na=False)

        filtered = filtered[mask]

    if service_filter != "Tous" and "service" in filtered.columns:
        filtered = filtered[filtered["service"] == service_filter]

    if categorie_filter != "Toutes" and "categorie" in filtered.columns:
        filtered = filtered[filtered["categorie"] == categorie_filter]

    total_km = 0
    if not filtered.empty and "kilometrage_actuel" in filtered.columns:
        total_km = int(filtered["kilometrage_actuel"].fillna(0).sum())

    actifs = 0
    if not filtered.empty and "actif" in filtered.columns:
        actifs = int(filtered["actif"].fillna(1).sum())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Véhicules", len(filtered))
    m2.metric("Actifs", actifs)
    m3.metric("Kilométrage total", total_km)
    m4.metric("Base", DB_PATH.name)

    display_cols = [
        "id",
        "immatriculation",
        "nom",
        "marque",
        "modele",
        "categorie",
        "service",
        "energie",
        "kilometrage_actuel",
        "date_ct",
        "statut",
        "actif",
    ]
    display_cols = [col for col in display_cols if col in filtered.columns]

    st.dataframe(filtered[display_cols], width="stretch", hide_index=True)

    st.markdown("### 🔎 Détail véhicules")

    for _, row in filtered.iterrows():
        titre = f"{row.get('immatriculation', '')} — {row.get('marque', '')} {row.get('modele', '')}".strip()

        with st.expander(titre or f"Véhicule #{row.get('id')}"):
            col_photo, col_info = st.columns([1, 2])

            with col_photo:
                photo = str(row.get("photo_path") or "")

                if photo and Path(photo).exists():
                    st.image(photo, width="stretch")
                else:
                    st.info("Aucune photo.")

            with col_info:
                st.write(f"**Nom :** {row.get('nom') or ''}")
                st.write(f"**Immatriculation :** {row.get('immatriculation') or ''}")
                st.write(f"**Marque / modèle :** {row.get('marque') or ''} {row.get('modele') or ''}")
                st.write(f"**Catégorie :** {row.get('categorie') or ''}")
                st.write(f"**Service :** {row.get('service') or ''}")
                st.write(f"**Énergie :** {row.get('energie') or ''}")
                st.write(f"**Kilométrage :** {row.get('kilometrage_actuel') or 0}")
                st.write(f"**Contrôle technique :** {row.get('date_ct') or ''}")
                st.write(f"**Statut :** {row.get('statut') or ''}")

                notes = row.get("notes") or ""
                if notes:
                    st.write(f"**Notes :** {notes}")


def render_ajouter() -> None:
    st.markdown("### ➕ Ajouter un véhicule")

    with st.form("garage_add_vehicle_form"):
        c1, c2 = st.columns(2)

        with c1:
            nom = st.text_input("Nom")
            immatriculation = st.text_input("Immatriculation *")
            marque = st.text_input("Marque")
            modele = st.text_input("Modèle")
            categorie = st.text_input("Catégorie")
            service = st.text_input("Service")

        with c2:
            energie = st.selectbox(
                "Énergie",
                ["", "Essence", "Diesel", "Hybride", "Électrique", "GPL", "Autre"],
            )
            kilometrage_actuel = st.number_input("Kilométrage actuel", min_value=0, step=100)
            date_mise_en_service = st.date_input("Date mise en service", value=None)
            date_ct = st.date_input("Date contrôle technique", value=None)
            assurance = st.text_input("Assurance")
            statut = st.selectbox("Statut", ["Actif", "En réparation", "Hors service", "Vendu"])

        photo = st.file_uploader("Photo véhicule", type=["png", "jpg", "jpeg", "webp"])
        notes = st.text_area("Notes")

        submitted = st.form_submit_button("💾 Enregistrer", width="stretch")

    if not submitted:
        return

    if not immatriculation.strip():
        st.error("L'immatriculation est obligatoire.")
        return

    photo_path = save_photo(photo, immatriculation)

    try:
        add_vehicule(
            {
                "nom": nom,
                "immatriculation": immatriculation.strip().upper(),
                "marque": marque,
                "modele": modele,
                "categorie": categorie,
                "service": service,
                "energie": energie,
                "kilometrage_actuel": int(kilometrage_actuel),
                "date_mise_en_service": date_to_text(date_mise_en_service),
                "date_ct": date_to_text(date_ct),
                "assurance": assurance,
                "statut": statut,
                "actif": True,
                "photo_path": photo_path,
                "notes": notes,
            }
        )
        st.success("Véhicule ajouté dans garage_vehicules.db.")
        st.rerun()
    except sqlite3.IntegrityError:
        st.error("Cette immatriculation existe déjà.")
    except Exception as exc:
        st.error("Erreur pendant l'ajout du véhicule.")
        st.exception(exc)


def render_modifier_supprimer() -> None:
    st.markdown("### ✏️ Modifier / supprimer un véhicule")

    vehicules = load_vehicules(include_inactive=True)

    if not vehicules:
        st.info("Aucun véhicule disponible.")
        return

    options = {}

    for vehicule in vehicules:
        label = (
            f"#{vehicule.get('id')} — "
            f"{vehicule.get('immatriculation') or 'Sans immat'} — "
            f"{vehicule.get('marque') or ''} {vehicule.get('modele') or ''}"
        )

        if not vehicule.get("actif", 1):
            label += " — INACTIF"

        options[label] = vehicule["id"]

    selected_label = st.selectbox("Sélectionner un véhicule", list(options.keys()))
    vehicule_id = options[selected_label]
    vehicule = get_vehicule_by_id(vehicule_id)

    if not vehicule:
        st.error("Véhicule introuvable.")
        return

    with st.form(f"garage_edit_form_{vehicule_id}"):
        c1, c2 = st.columns(2)

        with c1:
            nom = st.text_input("Nom", value=vehicule.get("nom") or "")
            immatriculation = st.text_input("Immatriculation *", value=vehicule.get("immatriculation") or "")
            marque = st.text_input("Marque", value=vehicule.get("marque") or "")
            modele = st.text_input("Modèle", value=vehicule.get("modele") or "")
            categorie = st.text_input("Catégorie", value=vehicule.get("categorie") or "")
            service = st.text_input("Service", value=vehicule.get("service") or "")

        with c2:
            energies = ["", "Essence", "Diesel", "Hybride", "Électrique", "GPL", "Autre"]
            current_energie = vehicule.get("energie") or ""
            energie_index = energies.index(current_energie) if current_energie in energies else 0
            energie = st.selectbox("Énergie", energies, index=energie_index)

            kilometrage_actuel = st.number_input(
                "Kilométrage actuel",
                min_value=0,
                step=100,
                value=int(vehicule.get("kilometrage_actuel") or 0),
            )

            date_mise_en_service = st.date_input(
                "Date mise en service",
                value=safe_date(vehicule.get("date_mise_en_service")),
            )

            date_ct = st.date_input(
                "Date contrôle technique",
                value=safe_date(vehicule.get("date_ct")),
            )

            assurance = st.text_input("Assurance", value=vehicule.get("assurance") or "")

            statuts = ["Actif", "En réparation", "Hors service", "Vendu", "Supprimé"]
            current_statut = vehicule.get("statut") or "Actif"
            statut_index = statuts.index(current_statut) if current_statut in statuts else 0
            statut = st.selectbox("Statut", statuts, index=statut_index)

            actif = st.checkbox("Actif", value=bool(vehicule.get("actif", 1)))

        current_photo = vehicule.get("photo_path") or ""

        if current_photo and Path(current_photo).exists():
            st.image(current_photo, caption="Photo actuelle", width=250)

        new_photo = st.file_uploader(
            "Remplacer la photo",
            type=["png", "jpg", "jpeg", "webp"],
            key=f"garage_edit_photo_{vehicule_id}",
        )

        notes = st.text_area("Notes", value=vehicule.get("notes") or "")

        save_btn = st.form_submit_button("💾 Enregistrer les modifications", width="stretch")

    if save_btn:
        if not immatriculation.strip():
            st.error("L'immatriculation est obligatoire.")
            return

        photo_path = current_photo

        if new_photo is not None:
            photo_path = save_photo(new_photo, immatriculation)

        try:
            update_vehicule(
                vehicule_id,
                {
                    "nom": nom,
                    "immatriculation": immatriculation.strip().upper(),
                    "marque": marque,
                    "modele": modele,
                    "categorie": categorie,
                    "service": service,
                    "energie": energie,
                    "kilometrage_actuel": int(kilometrage_actuel),
                    "date_mise_en_service": date_to_text(date_mise_en_service),
                    "date_ct": date_to_text(date_ct),
                    "assurance": assurance,
                    "statut": statut,
                    "actif": actif,
                    "photo_path": photo_path,
                    "notes": notes,
                },
            )
            st.success("Véhicule modifié avec succès.")
            st.rerun()
        except sqlite3.IntegrityError:
            st.error("Cette immatriculation existe déjà sur un autre véhicule.")
        except Exception as exc:
            st.error("Erreur pendant la modification.")
            st.exception(exc)

    st.divider()
    st.markdown("### 🗑️ Suppression")

    c_soft, c_hard = st.columns(2)

    with c_soft:
        st.warning("Suppression douce : le véhicule passe en inactif et reste dans l'historique.")
        confirm_soft = st.checkbox(
            "Je confirme la désactivation de ce véhicule",
            key=f"garage_confirm_soft_{vehicule_id}",
        )

        if st.button("Désactiver le véhicule", disabled=not confirm_soft, width="stretch"):
            delete_vehicule(vehicule_id, hard_delete=False)
            st.success("Véhicule désactivé.")
            st.rerun()

    with c_hard:
        st.error("Suppression définitive : supprime le véhicule et ses historiques liés.")
        confirm_hard = st.checkbox(
            "Je confirme la suppression définitive",
            key=f"garage_confirm_hard_{vehicule_id}",
        )

        if st.button("Supprimer définitivement", disabled=not confirm_hard, width="stretch"):
            delete_vehicule(vehicule_id, hard_delete=True)
            st.success("Véhicule supprimé définitivement.")
            st.rerun()

# ============================================================
# Compatibilité navigation Streamlit
# Patch 102
# Ce module peut maintenant être appelé par :
# - render()
# - show()
# - render_modifier()
# - render_modifier_supprimer()
# ============================================================

def render():
    """
    Point d'entrée standard attendu par le routeur principal.
    """
    if "render_modifier_supprimer" in globals():
        return render_modifier_supprimer()
    if "render_liste" in globals():
        return render_liste()
    if "main" in globals():
        return main()
    import streamlit as st
    st.error("Aucune fonction d'affichage véhicule disponible.")


def show():
    """
    Alias de compatibilité pour les modules appelés avec show().
    """
    return render()


def render_modifier():
    """
    Alias de compatibilité pour l'écran modification / suppression.
    """
    if "render_modifier_supprimer" in globals():
        return render_modifier_supprimer()
    return render()


