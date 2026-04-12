from config import Config

def send_sms_stub(phone: str, message: str):
    if not Config.SMS_ENABLED:
        return False, "SMS désactivé"
    return True, f"SMS simulé vers {phone}"
