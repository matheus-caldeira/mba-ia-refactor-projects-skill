from controllers.access import ensure_supervisor, read_scope
from database import commit, db
from errors import NotFoundError
from models.category import Category
from models.task import Task
from validators import category_validator


def _get_or_404(category_id):
    category = Category.find(category_id)
    if category is None:
        raise NotFoundError("Categoria não encontrada")
    return category


def list_categories(actor):
    counts = Task.count_by_category(owner_id=read_scope(actor))
    result = []
    for category in Category.list_all():
        data = category.to_dict()
        data["task_count"] = counts.get(category.id, 0)
        result.append(data)
    return result


def create_category(payload, actor):
    ensure_supervisor(actor)
    category = Category(**category_validator.validate_create(payload))
    db.session.add(category)
    commit()
    return category.to_dict()


def update_category(category_id, payload, actor):
    ensure_supervisor(actor)
    category = _get_or_404(category_id)
    for field, value in category_validator.validate_update(payload).items():
        setattr(category, field, value)
    commit()
    return category.to_dict()


def delete_category(category_id, actor):
    ensure_supervisor(actor)
    category = _get_or_404(category_id)
    db.session.delete(category)  # tasks da categoria ficam sem categoria
    commit()
    return {"message": "Categoria deletada"}
