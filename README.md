# Logistique Pro - Ville de Marly

Base de projet Streamlit pour une application de gestion logistique municipale.

## Contenu
- Authentification simple avec création automatique d'un compte admin
- Initialisation SQLite
- Structure modulaire `utils/` et `pages/`
- Script d'installation Linux
- Découpage prêt à être enrichi sur GitHub

## Lancement rapide

```bash
chmod +x install.sh
./install.sh
source .venv/bin/activate
streamlit run main.py
```

## Identifiants initiaux
Définis dans `.env` :
- `DEFAULT_ADMIN_EMAIL`
- `DEFAULT_ADMIN_PASSWORD`

## Remarque
Cette archive fournit une base propre pour GitHub et un socle exécutable.
Les fonctionnalités métier avancées restent à compléter progressivement.
