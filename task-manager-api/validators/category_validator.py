from errors import ValidationError
from models.category import DEFAULT_COLOR
from validators.common import is_valid_color, require_object


def _name(value):
    if not value or not isinstance(value, str):
        raise ValidationError("Nome é obrigatório")
    return value


def _description(value):
    if value is not None and not isinstance(value, str):
        raise ValidationError("Descrição inválida")
    return value


def _color(value):
    if not is_valid_color(value):
        raise ValidationError("Cor inválida. Use o formato #RRGGBB")
    return value


_FIELDS = {"name": _name, "description": _description, "color": _color}


def validate_create(data):
    data = require_object(data)
    return {
        "name": _name(data.get("name")),
        "description": _description(data.get("description", "")),
        "color": _color(data.get("color", DEFAULT_COLOR)),
    }


def validate_update(data):
    data = require_object(data)
    return {field: parse(data[field]) for field, parse in _FIELDS.items() if field in data}
