import streamlit as st


def render():
    st.subheader("❓ Aide administration")
    st.caption("Guide rapide des modules d'administration.")

    st.markdown("""
### Modules disponibles

**🎨 Thème et identité**  
Gestion du logo, du nom du site, des couleurs et des informations de contact.

**👥 Gestion Utilisateurs**  
Ajout, modification, désactivation, suppression et réinitialisation de mot de passe.

**✅ Validation Comptes**  
Validation ou refus des comptes en attente.

**📦 Articles / Catégories**  
Gestion des catégories et sous-catégories du catalogue.

**📋 Inventaire**  
Gestion de l’inventaire réel.

**🚗 Garage / Véhicules**  
Gestion des véhicules, entretiens, contrôles techniques, carburant et attribution conducteur.

**🏛️ Patrimoine bâti**  
Gestion des bâtiments, contrôles et interventions.

**🧾 Paramètres facturation**  
Configuration des informations de facturation.
""")

    st.info("Les modules sont maintenant séparés dans le dossier `/opt/logistique-pro/administration_site/`.")
