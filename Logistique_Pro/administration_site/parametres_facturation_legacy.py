import streamlit as st
from utils.facturation_settings import get_settings, save_settings


def show():
    st.title("🧾 Paramètres facturation")
    st.caption("Configuration des factures, TVA, transport et coordonnées mairie")

    user = st.session_state.get("user")

    if not user or str(user.get("role", "")).lower() != "admin":
        st.error("Accès réservé aux administrateurs.")
        st.stop()

    settings = get_settings()

    with st.form("facturation_settings_form"):
        st.subheader("🏛️ Informations mairie")

        c1, c2 = st.columns(2)

        with c1:
            mairie_nom = st.text_input("Nom mairie", value=settings["mairie_nom"])
            mairie_service = st.text_input("Service", value=settings["mairie_service"])
            mairie_adresse = st.text_input("Adresse", value=settings["mairie_adresse"])
            mairie_cp_ville = st.text_input("Code postal / Ville", value=settings["mairie_cp_ville"])

        with c2:
            mairie_email = st.text_input("Email", value=settings["mairie_email"])
            mairie_telephone = st.text_input("Téléphone", value=settings["mairie_telephone"])
            mairie_site = st.text_input("Site internet", value=settings["mairie_site"])

        st.subheader("💶 Facturation")

        c3, c4, c5 = st.columns(3)

        with c3:
            tva_rate = st.number_input(
                "TVA (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(settings["tva_rate"]),
                step=1.0,
            )

        with c4:
            transport_default_ht = st.number_input(
                "Prix transport par défaut HT",
                min_value=0.0,
                value=float(settings["transport_default_ht"]),
                step=5.0,
            )

        with c5:
            facture_prefix = st.text_input("Préfixe facture", value=settings["facture_prefix"])

        facture_footer = st.text_area("Texte pied de facture", value=settings["facture_footer"])

        submitted = st.form_submit_button("💾 Enregistrer les paramètres", width="stretch")

        if submitted:
            save_settings({
                "mairie_nom": mairie_nom.strip(),
                "mairie_service": mairie_service.strip(),
                "mairie_adresse": mairie_adresse.strip(),
                "mairie_cp_ville": mairie_cp_ville.strip(),
                "mairie_email": mairie_email.strip(),
                "mairie_telephone": mairie_telephone.strip(),
                "mairie_site": mairie_site.strip(),
                "tva_rate": str(tva_rate),
                "transport_default_ht": str(transport_default_ht),
                "facture_prefix": facture_prefix.strip(),
                "facture_footer": facture_footer.strip(),
            })

            st.success("Paramètres de facturation enregistrés.")
            st.rerun()

    st.info("Ces paramètres seront utilisés dans les prochaines factures PDF et validations de transport.")
