import logging

from controllers.access import ensure_owner_or_supervisor, read_scope
from database import commit, db
from errors import ForbiddenError, NotFoundError
from models.category import Category
from models.task import STATUS_DONE, Task
from models.user import User
from utils.clock import utcnow
from validators import task_validator

logger = logging.getLogger(__name__)


def _get_or_404(task_id):
    task = Task.find(task_id)
    if task is None:
        raise NotFoundError("Task não encontrada")
    return task


def _ensure_references(clean, actor):
    if clean.get("user_id") is not None:
        if not actor.is_supervisor() and clean["user_id"] != actor.id:
            raise ForbiddenError("Apenas supervisores atribuem tasks a outros usuários")
        if User.find(clean["user_id"]) is None:
            raise NotFoundError("Usuário não encontrado")
    elif "user_id" in clean and not actor.is_supervisor():
        raise ForbiddenError("Apenas supervisores deixam tasks sem responsável")
    if clean.get("category_id") is not None and Category.find(clean["category_id"]) is None:
        raise NotFoundError("Categoria não encontrada")


def list_tasks(actor):
    now = utcnow()
    result = []
    for task in Task.list_with_relations(owner_id=read_scope(actor)):
        data = task.to_dict()
        data["overdue"] = task.is_overdue(now)
        data["user_name"] = task.user.name if task.user else None
        data["category_name"] = task.category.name if task.category else None
        result.append(data)
    return result


def get_task(task_id, actor):
    task = _get_or_404(task_id)
    ensure_owner_or_supervisor(actor, task.user_id)
    data = task.to_dict()
    data["overdue"] = task.is_overdue()
    return data


def create_task(payload, actor):
    clean = task_validator.validate_create(payload)
    if not actor.is_supervisor():
        clean.setdefault("user_id", actor.id)
    _ensure_references(clean, actor)
    task = Task(**clean)
    db.session.add(task)
    commit()
    logger.info("Task criada: %s por usuário %s", task.id, actor.id)
    return task.to_dict()


def update_task(task_id, payload, actor):
    task = _get_or_404(task_id)
    ensure_owner_or_supervisor(actor, task.user_id)
    clean = task_validator.validate_update(payload)
    _ensure_references(clean, actor)
    for field, value in clean.items():
        setattr(task, field, value)
    task.updated_at = utcnow()
    commit()
    logger.info("Task atualizada: %s por usuário %s", task.id, actor.id)
    return task.to_dict()


def delete_task(task_id, actor):
    task = _get_or_404(task_id)
    ensure_owner_or_supervisor(actor, task.user_id)
    db.session.delete(task)
    commit()
    logger.info("Task deletada: %s por usuário %s", task_id, actor.id)
    return {"message": "Task deletada com sucesso"}


def search_tasks(args, actor):
    filters = task_validator.validate_search(args)
    scope = read_scope(actor)
    if scope is not None:
        if filters["user_id"] is not None and filters["user_id"] != scope:
            raise ForbiddenError()
        filters["user_id"] = scope
    return [task.to_dict() for task in Task.search(**filters)]


def task_stats(actor):
    scope = read_scope(actor)
    by_status = Task.count_by_status(owner_id=scope)
    total = sum(by_status.values())
    return {
        "total": total,
        **by_status,
        "overdue": Task.count_overdue(utcnow(), owner_id=scope),
        "completion_rate": round(by_status[STATUS_DONE] / total * 100, 2) if total else 0,
    }
