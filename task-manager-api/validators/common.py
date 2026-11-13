import re
from datetime import datetime

from errors import ValidationError

EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
DATE_FORMAT = "%Y-%m-%d"


def require_object(data):
    if not isinstance(data, dict) or not data:
        raise ValidationError("Dados inválidos")
    return data


def parse_int(value, message):
    """Aceita inteiro ou string numérica; rejeita bool, float e texto."""
    if isinstance(value, bool):
        raise ValidationError(message)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    raise ValidationError(message)


def parse_optional_id(value, message):
    if value in (None, ""):
        return None
    return parse_int(value, message)


def parse_date(value, message):
    if not isinstance(value, str):
        raise ValidationError(message)
    try:
        return datetime.strptime(value, DATE_FORMAT)
    except ValueError:
        raise ValidationError(message) from None


def is_valid_email(value):
    return isinstance(value, str) and bool(EMAIL_PATTERN.match(value))


def is_valid_color(value):
    return isinstance(value, str) and bool(COLOR_PATTERN.match(value))
