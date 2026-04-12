# Logistique Pro - Ville de Marly

Application Streamlit de gestion logistique municipale pour la Ville de Marly.

Ce dépôt fournit une base exécutable et structurée pour piloter les besoins logistiques d’une collectivité : authentification, base SQLite, pages métiers, utilitaires, sauvegardes, notifications, inventaire et administration.

## Fonctionnalités disponibles

- Authentification avec création automatique du premier compte administrateur
- Initialisation automatique de la base SQLite
- Navigation multi-pages avec Streamlit
- Structure modulaire avec dossier `utils/` et dossier `pages/`
- Gestion de base des utilisateurs
- Gestion d’inventaire avec QR Code
- Gestion des bâtiments et du patrimoine
- Centre de notifications
- Exports CSV et sauvegardes SQLite
- Profil utilisateur
- Thème CSS personnalisé

## Structure du projet

```text
Logistique_Pro/
├── main.py
├── config.py
├── requirements.txt
├── install.sh
├── .env.example
├── README.md
├── LICENSE
├── assets/
│   ├── css/
│   │   └── theme.css
│   ├── icons/
│   └── photos/
├── data/
│   ├── backups/
│   ├── inventaires/
│   ├── reservations/
│   └── stock/
├── docs/
├── pages/
└── utils/
