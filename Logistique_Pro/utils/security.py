import re


def is_strong_password(password: str):
    if len(password) < 8:
        return False, "Minimum 8 caractères"

    if not re.search(r"[A-Z]", password):
        return False, "Au moins une majuscule"

    if not re.search(r"[0-9]", password):
        return False, "Au moins un chiffre"

    return True, "OK"


def sanitize_input(value: str):
    if not value:
        return ""
    return value.strip()
