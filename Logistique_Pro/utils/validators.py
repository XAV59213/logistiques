def required(value: str):
    return value is not None and value.strip() != ""


def is_positive_number(value):
    try:
        return float(value) >= 0
    except:
        return False


def validate_email(email: str):
    return "@" in email and "." in email
