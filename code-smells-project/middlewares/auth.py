"""Autenticação por token Bearer e autorização por papel."""
from functools import wraps

from flask import current_app, g, request

from errors import ForbiddenError, UnauthorizedError
from models.usuario_model import TIPO_ADMIN


def _carregar_ator():
    cabecalho = request.headers.get("Authorization", "")
    esquema, _, token = cabecalho.partition(" ")
    if esquema.lower() != "bearer" or not token.strip():
        raise UnauthorizedError("Token de acesso ausente")
    deps = current_app.extensions["loja"]
    usuario_id = deps.auth.usuario_do_token(token.strip())
    # Recarrega do banco a cada requisição: papel atualizado e usuário removido perde acesso.
    usuario = deps.usuarios.buscar_por_id(usuario_id)
    if usuario is None:
        raise UnauthorizedError("Token inválido")
    return usuario


def require_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        g.ator = _carregar_ator()
        return view(*args, **kwargs)
    return wrapper


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        g.ator = _carregar_ator()
        if g.ator["tipo"] != TIPO_ADMIN:
            raise ForbiddenError("Apenas administradores")
        return view(*args, **kwargs)
    return wrapper
