"""Regras de acesso dos casos de uso: quem pode agir sobre qual recurso.

- admin: tudo, inclusive gestão de usuários;
- manager: vê e gerencia as tasks e categorias de toda a equipe;
- user: só as próprias tasks e o próprio cadastro.
"""
from errors import ForbiddenError


def read_scope(actor):
    """None = sem restrição; senão, o id do único dono visível."""
    return None if actor.is_supervisor() else actor.id


def ensure_owner_or_supervisor(actor, owner_id):
    if not actor.is_supervisor() and owner_id != actor.id:
        raise ForbiddenError()


def ensure_supervisor(actor):
    if not actor.is_supervisor():
        raise ForbiddenError()


def ensure_admin(actor, message=None):
    if not actor.is_admin():
        raise ForbiddenError(message)
