from errors import ValidationError
from models.user import ROLE_USER, VALID_ROLES
from validators.common import is_valid_email, require_object

MIN_PASSWORD_LENGTH = 4
PASSWORD_ERROR = f"Senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres"


def _name(value):
    if not value:
        raise ValidationError("Nome é obrigatório")
    if not isinstance(value, str):
        raise ValidationError("Nome inválido")
    return value


def _email(value):
    if not value:
        raise ValidationError("Email é obrigatório")
    if not is_valid_email(value):
        raise ValidationError("Email inválido")
    return value


def _password(value):
    if not value:
        raise ValidationError("Senha é obrigatória")
    if not isinstance(value, str):
        raise ValidationError("Senha inválida")
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValidationError(PASSWORD_ERROR)
    return value


def _role(value):
    if value not in VALID_ROLES:
        raise ValidationError("Role inválido")
    return value


def _active(value):
    if not isinstance(value, bool):
        raise ValidationError("Campo active deve ser booleano")
    return value


def validate_create(data):
    data = require_object(data)
    return {
        "name": _name(data.get("name")),
        "email": _email(data.get("email")),
        "password": _password(data.get("password")),
        "role": _role(data.get("role", ROLE_USER)),
    }


_UPDATE_FIELDS = {
    "name": _name,
    "email": _email,
    "password": _password,
    "role": _role,
    "active": _active,
}


def validate_update(data):
    data = require_object(data)
    clean = {field: parse(data[field]) for field, parse in _UPDATE_FIELDS.items() if field in data}
    if "current_password" in data:
        clean["current_password"] = data["current_password"]
    return clean


def validate_login(data):
    data = require_object(data)
    email, password = data.get("email"), data.get("password")
    if not email or not password or not isinstance(email, str) or not isinstance(password, str):
        raise ValidationError("Email e senha são obrigatórios")
    return email, password
