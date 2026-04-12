TRANSLATIONS = {
    "fr": {
        "login": "Connexion",
        "logout": "Déconnexion",
        "welcome": "Bienvenue",
    },
    "en": {
        "login": "Login",
        "logout": "Logout",
        "welcome": "Welcome",
    },
}


def t(key: str, lang: str = "fr"):
    return TRANSLATIONS.get(lang, {}).get(key, key)
