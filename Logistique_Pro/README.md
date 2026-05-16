# 🚛 Logistique Pro - Ville de Marly

> Application professionnelle de gestion logistique municipale développée avec **Python** et **Streamlit** pour la **Ville de Marly**.

---

## 📌 Présentation

**Logistique Pro** centralise l’ensemble des besoins d’un service logistique communal :

- 📦 Gestion des stocks  
- 📅 Organisation des événements  
- 📝 Demandes internes / externes  
- 👷 Planning des équipes  
- 📊 Tableau de bord décisionnel  
- 🔐 Gestion multi-utilisateurs  
- 💾 Sauvegardes et exports  
- 🏛️ Administration système  

---

## ✨ Fonctionnalités principales

### 👤 Gestion des utilisateurs

- Connexion sécurisée  
- Création de compte  
- Validation administrateur  
- Gestion des rôles utilisateurs  

**Rôles disponibles :**

- Administrateur  
- Interne  
- Équipe terrain  
- Association  
- Client / Externe  

---

### 📦 Gestion du matériel

- Catalogue des articles  
- Suivi des quantités  
- Alertes stock faible  
- Photos du matériel  
- Inventaire global  

---

### 📅 Gestion événementielle

- Réservations  
- Planning logistique  
- Affectation des équipes  
- Suivi des missions terrain  

---

### 📊 Pilotage & Analyse

- Tableau de bord dynamique  
- Notifications internes  
- Statistiques d’activité  
- Prévisions IA  

---

### ⚙️ Administration

- Gestion identité visuelle  
- Sauvegardes SQLite  
- Exports CSV  
- Maintenance système  

---

## 🛠️ Technologies utilisées

| Technologie | Utilisation |
|------------|------------|
| Python 3.11+ | Backend |
| Streamlit | Interface Web |
| SQLite | Base de données |
| Pandas | Analyse de données |
| bcrypt | Sécurité |
| Plotly | Graphiques |
| OpenPyXL | Export Excel |
| WeasyPrint | Génération PDF |
| Pillow | Gestion images |

---

## 📁 Structure du projet

```text
Logistique_Pro/
│
├── main.py
├── config.py
├── requirements.txt
├── install.sh
├── README.md
├── LICENSE
│
├── assets/
│   ├── css/
│   ├── icons/
│   ├── logo/
│   ├── photos/
│   ├── profiles/
│   └── vehicules/
│
├── data/
│   ├── logistique_marly.db
│   ├── backups/
│   ├── stock/
│   └── inventaires/
│
├── pages/
│   ├── 00_Connexion.py
│   ├── 01_Creation_Compte.py
│   ├── 03_Tableau_de_bord.py
│   ├── 04_Catalogue_Articles.py
│   ├── 08_Planning_Equipes.py
│   ├── 12_Mon_Profil.py
│   └── 19_Exports_Backups.py
│
├── utils/
│   ├── database.py
│   ├── auth.py
│   ├── backups.py
│   ├── exports.py
│   ├── weather.py
│   └── style.py
│
└── docs/
    └── architecture.md

## 🚀 Installation rapide

Suivez les étapes ci-dessous pour installer **Logistique Pro** sur votre machine.

---

### 1️⃣ Cloner le dépôt

```bash
git clone https://github.com/votre-repo/logistique_pro.git
cd logistique_pro
```



