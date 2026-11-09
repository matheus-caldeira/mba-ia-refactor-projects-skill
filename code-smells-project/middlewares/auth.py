from functools import wraps

from flask import g, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from config.runtime import config_atual
from models import usuario_model

from .errors import ForbiddenError, UnauthorizedError

TOKEN_SALT = "loja-auth"
TIPO_ADMIN = "admin"


def _serializer():
    return URLSafeTimedSerializer(config_atual().SECRET_KEY, salt=TOKEN_SALT)


def emitir_token(usuario):
    return _serializer().dumps({"usuario_id": usuario["id"]})


def _usuario_do_token():
    cabecalho = request.headers.get("Authorization", "")
    if not cabecalho.startswith("Bearer "):
        raise UnauthorizedError("Token ausente")
    token = cabecalho[len("Bearer "):].strip()
    try:
        dados = _serializer().loads(token, max_age=config_atual().TOKEN_TTL_SECONDS)
    except SignatureExpired:
        raise UnauthorizedError("Token expirado")
    except BadSignature:
        raise UnauthorizedError("Token inválido")

    usuario = usuario_model.buscar_por_id(dados.get("usuario_id"))
    if usuario is None:
        raise UnauthorizedError("Token inválido")
    return usuario


def usuario_atual():
    return g.get("usuario")


def eh_admin(usuario):
    return usuario is not None and usuario["tipo"] == TIPO_ADMIN


def exigir_proprio_ou_admin(usuario_id):
    usuario = usuario_atual()
    if eh_admin(usuario):
        return
    if str(usuario["id"]) != str(usuario_id):
        raise ForbiddenError("Acesso negado")


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        g.usuario = _usuario_do_token()
        return fn(*args, **kwargs)

    return wrapper


def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        g.usuario = _usuario_do_token()
        if not eh_admin(g.usuario):
            raise ForbiddenError("Acesso negado")
        return fn(*args, **kwargs)

    return wrapper
