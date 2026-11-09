"""Relatórios agregados. A contagem acontece no banco, não em laço Python."""

from datetime import timedelta

from controllers.policies import ensure_self_or_supervisor
from errors import NotFoundError
from models.clock import utcnow

PRIORITY_LABELS = {1: 'critical', 2: 'high', 3: 'medium', 4: 'low', 5: 'minimal'}


class ReportController:
    def __init__(self, task_repository, user_repository, category_repository):
        self._tasks = task_repository
        self._users = user_repository
        self._categories = category_repository

    def summary(self):
        overdue_tasks = [t for t in self._tasks.list_with_due_date() if t.is_overdue()]
        overdue_list = [
            {
                'id': t.id,
                'title': t.title,
                'due_date': str(t.due_date),
                'days_overdue': t.days_overdue(),
            }
            for t in overdue_tasks
        ]

        seven_days_ago = utcnow() - timedelta(days=7)

        # Uma única query agregada por usuário (antes: 1 query por usuário).
        productivity = self._tasks.productivity_by_user()
        user_stats = []
        for u in self._users.list_all():
            total, completed = productivity.get(u.id, (0, 0))
            user_stats.append(
                {
                    'user_id': u.id,
                    'user_name': u.name,
                    'total_tasks': total,
                    'completed_tasks': completed,
                    'completion_rate': (
                        round((completed / total) * 100, 2) if total > 0 else 0
                    ),
                }
            )

        return {
            'generated_at': str(utcnow()),
            'overview': {
                'total_tasks': self._tasks.count(),
                'total_users': self._users.count(),
                'total_categories': self._categories.count(),
            },
            'tasks_by_status': {
                'pending': self._tasks.count_by_status('pending'),
                'in_progress': self._tasks.count_by_status('in_progress'),
                'done': self._tasks.count_by_status('done'),
                'cancelled': self._tasks.count_by_status('cancelled'),
            },
            'tasks_by_priority': {
                label: self._tasks.count_by_priority(priority)
                for priority, label in PRIORITY_LABELS.items()
            },
            'overdue': {
                'count': len(overdue_list),
                'tasks': overdue_list,
            },
            'recent_activity': {
                'tasks_created_last_7_days': self._tasks.count_created_since(
                    seven_days_ago
                ),
                'tasks_completed_last_7_days': self._tasks.count_completed_since(
                    seven_days_ago
                ),
            },
            'user_productivity': user_stats,
        }

    def user_report(self, user_id, actor=None):
        ensure_self_or_supervisor(actor, user_id)
        user = self._users.get(user_id)
        if not user:
            raise NotFoundError('Usuário não encontrado')

        tasks = self._tasks.list_by_user(user_id)
        counters = {'done': 0, 'pending': 0, 'in_progress': 0, 'cancelled': 0}
        overdue = 0
        high_priority = 0

        for t in tasks:
            if t.status in counters:
                counters[t.status] += 1
            if t.priority <= 2:
                high_priority += 1
            if t.is_overdue():
                overdue += 1

        total = len(tasks)
        done = counters['done']

        return {
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
            },
            'statistics': {
                'total_tasks': total,
                'done': done,
                'pending': counters['pending'],
                'in_progress': counters['in_progress'],
                'cancelled': counters['cancelled'],
                'overdue': overdue,
                'high_priority': high_priority,
                'completion_rate': round((done / total) * 100, 2) if total > 0 else 0,
            },
        }
