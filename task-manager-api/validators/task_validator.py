from errors import ValidationError
from models.task import (
    DEFAULT_PRIORITY,
    MAX_PRIORITY,
    MAX_TITLE_LENGTH,
    MIN_PRIORITY,
    MIN_TITLE_LENGTH,
    STATUS_PENDING,
    VALID_STATUSES,
)
from validators.common import parse_date, parse_int, parse_optional_id, require_object

DATE_ERROR = "Formato de data inválido. Use YYYY-MM-DD"


def _title(value):
    if not value:
        raise ValidationError("Título é obrigatório")
    if not isinstance(value, str):
        raise ValidationError("Título inválido")
    if len(value) < MIN_TITLE_LENGTH:
        raise ValidationError("Título muito curto")
    if len(value) > MAX_TITLE_LENGTH:
        raise ValidationError("Título muito longo")
    return value


def _status(value):
    if value not in VALID_STATUSES:
        raise ValidationError("Status inválido")
    return value


def _priority(value):
    priority = parse_int(value, "Prioridade inválida")
    if not MIN_PRIORITY <= priority <= MAX_PRIORITY:
        raise ValidationError(f"Prioridade deve ser entre {MIN_PRIORITY} e {MAX_PRIORITY}")
    return priority


def _description(value):
    if value is not None and not isinstance(value, str):
        raise ValidationError("Descrição inválida")
    return value


def _tags(value):
    if value in (None, "", []):
        return None
    if isinstance(value, list) and all(isinstance(tag, str) for tag in value):
        return ",".join(value)
    if isinstance(value, str):
        return value
    raise ValidationError("Tags inválidas")


def _due_date(value):
    return parse_date(value, DATE_ERROR) if value else None


_FIELDS = {
    "title": _title,
    "description": _description,
    "status": _status,
    "priority": _priority,
    "user_id": lambda v: parse_optional_id(v, "user_id inválido"),
    "category_id": lambda v: parse_optional_id(v, "category_id inválido"),
    "due_date": _due_date,
    "tags": _tags,
}


def validate_create(data):
    data = require_object(data)
    clean = {
        "title": _title(data.get("title")),
        "description": _description(data.get("description", "")),
        "status": _status(data.get("status", STATUS_PENDING)),
        "priority": _priority(data.get("priority", DEFAULT_PRIORITY)),
    }
    for field in ("user_id", "category_id", "due_date", "tags"):
        if field in data:
            clean[field] = _FIELDS[field](data[field])
    return clean


def validate_update(data):
    data = require_object(data)
    return {field: parse(data[field]) for field, parse in _FIELDS.items() if field in data}


def validate_search(args):
    filters = {"text": args.get("q") or None, "status": args.get("status") or None}
    priority = args.get("priority")
    filters["priority"] = parse_int(priority, "Prioridade inválida") if priority else None
    user_id = args.get("user_id")
    filters["user_id"] = parse_int(user_id, "user_id inválido") if user_id else None
    return filters
