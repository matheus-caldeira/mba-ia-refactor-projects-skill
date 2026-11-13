from datetime import timedelta

from controllers.access import ensure_owner_or_supervisor, ensure_supervisor
from errors import NotFoundError
from models.category import Category
from models.task import (
    HIGH_PRIORITY_MAX,
    PRIORITY_LABELS,
    STATUS_CANCELLED,
    STATUS_DONE,
    STATUS_IN_PROGRESS,
    STATUS_PENDING,
    Task,
)
from models.user import User
from utils.clock import utcnow

RECENT_ACTIVITY_DAYS = 7


def _rate(part, total):
    return round(part / total * 100, 2) if total else 0


def summary_report(actor):
    """Visão da equipe inteira: só para supervisores."""
    ensure_supervisor(actor)
    now = utcnow()
    since = now - timedelta(days=RECENT_ACTIVITY_DAYS)
    by_priority = Task.count_by_priority()
    totals = Task.totals_by_user()

    overdue = [
        {
            "id": task.id,
            "title": task.title,
            "due_date": str(task.due_date),
            "days_overdue": (now - task.due_date).days,
        }
        for task in Task.list_overdue(now)
    ]

    productivity = []
    for user in User.list_all():
        total, completed = totals.get(user.id, (0, 0))
        productivity.append({
            "user_id": user.id,
            "user_name": user.name,
            "total_tasks": total,
            "completed_tasks": completed,
            "completion_rate": _rate(completed, total),
        })

    return {
        "generated_at": str(now),
        "overview": {
            "total_tasks": Task.count(),
            "total_users": User.count(),
            "total_categories": Category.count(),
        },
        "tasks_by_status": Task.count_by_status(),
        "tasks_by_priority": {label: by_priority.get(p, 0) for p, label in PRIORITY_LABELS.items()},
        "overdue": {"count": len(overdue), "tasks": overdue},
        "recent_activity": {
            f"tasks_created_last_{RECENT_ACTIVITY_DAYS}_days": Task.count_created_since(since),
            f"tasks_completed_last_{RECENT_ACTIVITY_DAYS}_days": Task.count_done_since(since),
        },
        "user_productivity": productivity,
    }


def user_report(user_id, actor):
    user = User.find(user_id)
    if user is None:
        raise NotFoundError("Usuário não encontrado")
    ensure_owner_or_supervisor(actor, user.id)

    now = utcnow()
    tasks = Task.list_for_user(user.id)
    by_status = {status: 0 for status in (STATUS_DONE, STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_CANCELLED)}
    for task in tasks:
        if task.status in by_status:
            by_status[task.status] += 1

    return {
        "user": {"id": user.id, "name": user.name, "email": user.email},
        "statistics": {
            "total_tasks": len(tasks),
            **by_status,
            "overdue": sum(1 for task in tasks if task.is_overdue(now)),
            "high_priority": sum(1 for task in tasks if task.priority <= HIGH_PRIORITY_MAX),
            "completion_rate": _rate(by_status[STATUS_DONE], len(tasks)),
        },
    }
