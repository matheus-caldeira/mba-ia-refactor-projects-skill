"""Proteção das rotas administrativas por token vindo do ambiente (AP-05)."""

import hmac
from functools import wraps

from flask import request

from config import settings

from .errors import ForbiddenError, UnauthorizedError


def _token_da_requisicao():
    cabecalho = request.headers.get("Authorization", "")
    if cabecalho.startswith("Bearer "):
        return cabecalho[len("Bearer "):].strip()
    return request.headers.get("X-Admin-Token", "").strip()


def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if settings.IS_PRODUCTION or not settings.ADMIN_TOKEN:
            # Sem token configurado (ou em produção) a rota fica desabilitada.
            raise ForbiddenError("Operação administrativa desabilitada neste ambiente")
        fornecido = _token_da_requisicao()
        if not fornecido or not hmac.compare_digest(fornecido, settings.ADMIN_TOKEN):
            raise UnauthorizedError("Não autorizado")
        return fn(*args, **kwargs)

    return wrapper
