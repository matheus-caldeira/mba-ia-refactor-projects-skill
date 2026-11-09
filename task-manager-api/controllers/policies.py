from errors import ForbiddenError, UnauthorizedError

ADMIN = 'admin'
MANAGER = 'manager'
SUPERVISOR_ROLES = (ADMIN, MANAGER)


def require_actor(actor):
    if actor is None:
        raise UnauthorizedError('Token ausente')
    return actor


def is_supervisor(actor):
    return actor is not None and actor.role in SUPERVISOR_ROLES


def ensure_self_or_admin(actor, user_id):
    require_actor(actor)
    if actor.id != user_id and not actor.is_admin():
        raise ForbiddenError('Acesso negado')


def ensure_self_or_supervisor(actor, user_id):
    require_actor(actor)
    if actor.id != user_id and not is_supervisor(actor):
        raise ForbiddenError('Acesso negado')


def ensure_task_access(actor, task):
    require_actor(actor)
    if task.user_id != actor.id and not is_supervisor(actor):
        raise ForbiddenError('Acesso negado')


def ensure_can_assign(actor, user_id):
    require_actor(actor)
    if user_id and user_id != actor.id and not is_supervisor(actor):
        raise ForbiddenError('Apenas admin ou manager podem atribuir tasks a outro usuário')


def read_scope(actor):
    require_actor(actor)
    return None if is_supervisor(actor) else actor.id
