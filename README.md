# Logistique Pro - Ville de Marly

Application professionnelle développée avec Streamlit pour la gestion logistique municipale de la Ville de Marly.

Cette solution centralise les besoins opérationnels d’un service logistique communal :

- gestion du stock
- organisation des événements
- demandes internes / externes
- inventaire global
- planning des équipes
- communication interne
- administration système
- sauvegardes et exports
- profils utilisateurs

---

# Aperçu du projet

Logistique Pro permet de moderniser et simplifier la gestion quotidienne :

✅ Matériel communal  
✅ Réservations événementielles  
✅ Suivi des équipes terrain  
✅ Validation des demandes  
✅ Tableau de bord décisionnel  
✅ Gestion multi-utilisateurs  
✅ Sauvegarde sécurisée  

---

# Technologies utilisées

- Python 3.11+
- Streamlit
- SQLite
- Pandas
- NumPy
- bcrypt
- Plotly
- OpenPyXL
- Requests
- Pillow
- WeasyPrint
- Docker (optionnel)

---

# Structure complète du projet

```text
Logistique_Pro/
│
├── main.py
├── config.py
├── requirements.txt
├── install.sh
├── .env.example
├── README.md
├── LICENSE
│
├── assets/
│   ├── css/
│   ├── icons/
│   ├── logo/
│   ├── photos/
│   ├── profiles/
│   ├── logos_users/
│   ├── vehicules/
│   ├── outils/
│   └── signatures/
│
├── data/
│   ├── logistique_marly.db
│   ├── backups/
│   ├── stock/
│   ├── reservations/
│   └── inventaires/
│
├── docs/
│   └── architecture.md
│
├── pages/
│   ├── 00_Connexion.py
│   ├── 01_Creation_Compte.py
│   ├── 02_Validation_Comptes.py
│   ├── 03_Tableau_de_bord.py
│   ├── 04_Catalogue_Articles.py
│   ├── 05_Mes_Demandes.py
│   ├── 06_Validation_Demandes.py
│   ├── 07_Calendrier_Evenements.py
│   ├── 08_Planning_Equipes.py
│   ├── 09_Administration.py
│   ├── 10_Administration_Systeme.py
│   ├── 11_Messages.py
│   ├── 12_Mon_Profil.py
│   ├── 13_Inventaire.py
│   ├── 16_Patrimoine_Securite.py
│   ├── 17_Inventaire_QR.py
│   ├── 18_Notifications.py
│   └── 19_Exports_Backups.py
│
└── utils/
    ├── ai_forecast.py
    ├── auth.py
    ├── backups.py
    ├── database.py
    ├── exports.py
    ├── helpers.py
    ├── logger.py
    ├── notifications.py
    ├── qr_scanner.py
    ├── security.py
    ├── sms.py
    ├── style.py
    ├── system_manager.py
    ├── validators.py
    └── vehicles.py

Installation rapide
1. Cloner le projet
git clone https://github.com/votre-repo/logistique_pro.git
cd logistique_pro

2. Lancer l'installation automatique
chmod +x install.sh
./install.sh

3. Activer l’environnement virtuel
Linux / Mac
source .venv/bin/activate
Windows
.venv\Scripts\activate

4. Lancer l’application
streamlit run main.py

Identifiants administrateur par défaut
Email : admin@marly.fr
Mot de passe : ChangeMe123!

⚠️ À modifier dès la première connexion.

Modules disponibles
Connexion & Comptes
connexion sécurisée
création de compte
validation administrateur
rôles utilisateurs
Tableau de Bord
indicateurs clés
notifications
météo
prévisions IA
suivi activité
Catalogue Articles
consultation du matériel
niveaux de stock
photos
prix
Inventaire
inventaire complet
outils
matériel communal
alertes stock
Planning Équipes
interventions
missions terrain
véhicules
export CSV
Messages
communication interne
messagerie équipes
notifications admin
Administration
logo mairie
favicon
couleurs thème
identité visuelle
Administration Système
contrôle base SQLite
sauvegardes
maintenance
statistiques techniques
Exports & Backups
exports CSV
téléchargement base
sauvegardes multiples
Sécurité
mots de passe hashés avec bcrypt
rôles utilisateurs
validation des comptes
accès restreint aux pages admin
base locale SQLite
Personnalisation

Modifier .env

APP_NAME=Logistique Pro
DEFAULT_ADMIN_EMAIL=admin@marly.fr
DEFAULT_ADMIN_PASSWORD=MonMotDePasse
SITE_MAINTENANCE_ENABLED=false
Sauvegardes

Les sauvegardes sont stockées ici :

data/backups/
Roadmap future
application mobile agents terrain
signature numérique interventions
QR code complet matériel
email automatique
SMS réel Twilio / OVH
API interne mairie
statistiques avancées
multi-sites
Auteur

Développé par xavier59213

Projet Logistique Pro pour la Ville de Marly.

Licence

MIT License



