"""Autenticação por token assinado (Authorization: Bearer <token>)."""
from functools import wraps

from flask import current_app, g, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from errors import UnauthorizedError
from models.user import User

_TOKEN_SALT = "task-manager-auth"


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=_TOKEN_SALT)


def issue_token(user):
    return _serializer().dumps({"uid": user.id})


def _user_from_request():
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedError("Token de autenticação ausente")
    try:
        payload = _serializer().loads(token, max_age=current_app.config["TOKEN_MAX_AGE"])
    except SignatureExpired:
        raise UnauthorizedError("Token expirado") from None
    except BadSignature:
        raise UnauthorizedError("Token inválido") from None
    user = User.find(payload.get("uid"))
    if user is None or not user.active:
        raise UnauthorizedError("Token inválido")
    return user


def require_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        g.current_user = _user_from_request()
        return view(*args, **kwargs)

    return wrapper


def optional_auth(view):
    """Identifica o ator se houver token; sem header, segue anônimo."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        g.current_user = _user_from_request() if request.headers.get("Authorization") else None
        return view(*args, **kwargs)

    return wrapper


def current_user():
    return g.get("current_user")
