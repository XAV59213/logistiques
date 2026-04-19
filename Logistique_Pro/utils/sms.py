# utils/sms.py
from config import Config


def send_sms_stub(phone: str, message: str):
    if not phone.strip():
        return False, "Numéro de téléphone manquant"

    if not message.strip():
        return False, "Message vide"

    if not Config.SMS_ENABLED:
        return False, "SMS désactivé"

    return True, f"SMS simulé vers {phone}"
