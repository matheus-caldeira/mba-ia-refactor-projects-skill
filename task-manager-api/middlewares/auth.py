"""Autenticação/autorização por token Bearer.

O token é emitido pelo ``AuthService`` (assinado, com expiração). O usuário
autenticado fica em ``flask.g.current_user``.
"""

from functools import wraps

from flask import current_app, g, request

from errors import ForbiddenError, UnauthorizedError


def _auth_service():
    return current_app.extensions['auth_service']


def _extract_token():
    header = request.headers.get('Authorization', '')
    if header.startswith('Bearer '):
        return header[len('Bearer '):].strip()
    return None


def load_current_user():
    """Popula ``g.current_user`` quando houver token válido; nunca bloqueia."""
    g.current_user = None
    token = _extract_token()
    if not token:
        return
    try:
        g.current_user = _auth_service().verify_token(token)
    except UnauthorizedError:
        g.current_user = None


def current_user():
    return getattr(g, 'current_user', None)


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _extract_token()
        g.current_user = _auth_service().verify_token(token)
        return fn(*args, **kwargs)

    return wrapper


def require_role(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = _extract_token()
            user = _auth_service().verify_token(token)
            g.current_user = user
            if user.role not in roles:
                raise ForbiddenError('Acesso negado')
            return fn(*args, **kwargs)

        return wrapper

    return decorator
