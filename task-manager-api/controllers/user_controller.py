import logging

from sqlalchemy.exc import IntegrityError

from controllers.access import ensure_admin, ensure_owner_or_supervisor
from database import commit, db
from errors import ConflictError, ForbiddenError, NotFoundError
from models.task import Task
from models.user import ROLE_USER, User
from validators import user_validator

logger = logging.getLogger(__name__)

EMAIL_TAKEN = "Email já cadastrado"


def _get_or_404(user_id):
    user = User.find(user_id)
    if user is None:
        raise NotFoundError("Usuário não encontrado")
    return user


def _commit_unique_email():
    try:
        commit()
    except IntegrityError:
        raise ConflictError(EMAIL_TAKEN) from None


def list_users(actor):
    only_id = None if actor.is_supervisor() else actor.id
    totals = Task.totals_by_user()
    result = []
    for user in User.list_all(only_id=only_id):
        data = user.to_dict()
        data["task_count"] = totals.get(user.id, (0, 0))[0]
        result.append(data)
    return result


def get_user(user_id, actor):
    user = _get_or_404(user_id)
    ensure_owner_or_supervisor(actor, user.id)
    data = user.to_dict()
    data["tasks"] = [task.to_dict() for task in Task.list_for_user(user.id)]
    return data


def create_user(payload, actor=None):
    """Cadastro público cria sempre `user`; outro papel exige admin autenticado."""
    clean = user_validator.validate_create(payload)
    if clean["role"] != ROLE_USER and (actor is None or not actor.is_admin()):
        raise ForbiddenError("Apenas administradores definem o papel do usuário")
    if User.find_by_email(clean["email"]) is not None:
        raise ConflictError(EMAIL_TAKEN)
    user = User(name=clean["name"], email=clean["email"], role=clean["role"])
    user.set_password(clean["password"])
    db.session.add(user)
    _commit_unique_email()
    logger.info("Usuário criado: %s", user.id)
    return user.to_dict()


def update_user(user_id, payload, actor):
    user = _get_or_404(user_id)
    is_self = actor.id == user.id
    if not is_self:
        ensure_admin(actor)
    clean = user_validator.validate_update(payload)

    if ("role" in clean or "active" in clean) and not actor.is_admin():
        raise ForbiddenError("Apenas administradores alteram role ou active")
    if "password" in clean and is_self:
        if not user.check_password(clean.get("current_password") or ""):
            raise ForbiddenError("Senha atual incorreta")
    if "email" in clean:
        existing = User.find_by_email(clean["email"])
        if existing is not None and existing.id != user.id:
            raise ConflictError(EMAIL_TAKEN)

    for field in ("name", "email", "role", "active"):
        if field in clean:
            setattr(user, field, clean[field])
    if "password" in clean:
        user.set_password(clean["password"])
    _commit_unique_email()
    logger.info("Usuário atualizado: %s por usuário %s", user.id, actor.id)
    return user.to_dict()


def delete_user(user_id, actor):
    ensure_admin(actor)
    user = _get_or_404(user_id)
    db.session.delete(user)  # as tasks do usuário saem junto (cascade no model)
    commit()
    logger.info("Usuário deletado: %s por usuário %s", user_id, actor.id)
    return {"message": "Usuário deletado com sucesso"}


def list_user_tasks(user_id, actor):
    user = _get_or_404(user_id)
    ensure_owner_or_supervisor(actor, user.id)
    return [task.to_summary_dict() for task in Task.list_for_user(user.id)]
