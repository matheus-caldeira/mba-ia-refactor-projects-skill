"""Casos de uso de Task. Sem HTTP, sem SQL cru."""

from datetime import datetime

from errors import NotFoundError, ValidationError
from models.clock import utcnow
from models.task import MAX_PRIORITY, MIN_PRIORITY, VALID_STATUSES, Task

MIN_TITLE_LENGTH = 3
MAX_TITLE_LENGTH = 200
DATE_FORMAT = '%Y-%m-%d'


class TaskController:
    def __init__(self, task_repository, user_repository, category_repository,
                 notification_service=None):
        self._tasks = task_repository
        self._users = user_repository
        self._categories = category_repository
        self._notifications = notification_service

    # ---------- leitura ----------

    def list(self):
        """GET /tasks — inclui overdue, user_name e category_name."""
        tasks = self._tasks.list_all()
        result = []
        for t in tasks:
            data = t.to_dict()
            data['overdue'] = t.is_overdue()
            data['user_name'] = t.user.name if t.user else None
            data['category_name'] = t.category.name if t.category else None
            result.append(data)
        return result

    def get(self, task_id):
        """GET /tasks/<id> — to_dict() + overdue."""
        task = self._require_task(task_id)
        data = task.to_dict()
        data['overdue'] = task.is_overdue()
        return data

    def search(self, query=None, status=None, priority=None, user_id=None):
        """GET /tasks/search — contrato original devolve to_dict() puro."""
        tasks = self._tasks.search(
            query=query,
            status=status,
            priority=self._parse_int(priority, 'Prioridade inválida'),
            user_id=self._parse_int(user_id, 'user_id inválido'),
        )
        return [t.to_dict() for t in tasks]

    def stats(self):
        total = self._tasks.count()
        done = self._tasks.count_by_status('done')
        overdue = sum(1 for t in self._tasks.list_with_due_date() if t.is_overdue())
        return {
            'total': total,
            'pending': self._tasks.count_by_status('pending'),
            'in_progress': self._tasks.count_by_status('in_progress'),
            'done': done,
            'cancelled': self._tasks.count_by_status('cancelled'),
            'overdue': overdue,
            'completion_rate': round((done / total) * 100, 2) if total > 0 else 0,
        }

    # ---------- escrita ----------

    def create(self, data):
        if not data:
            raise ValidationError('Dados inválidos')

        title = self._validate_title(data.get('title'), required=True)
        status = data.get('status', 'pending')
        priority = data.get('priority', 3)
        user_id = data.get('user_id')
        category_id = data.get('category_id')

        self._validate_status(status)
        priority = self._validate_priority(priority)

        user = None
        if user_id:
            user = self._users.get(user_id)
            if not user:
                raise NotFoundError('Usuário não encontrado')

        if category_id:
            if not self._categories.get(category_id):
                raise NotFoundError('Categoria não encontrada')

        task = Task()
        task.title = title
        task.description = data.get('description', '')
        task.status = status
        task.priority = priority
        task.user_id = user_id
        task.category_id = category_id

        due_date = data.get('due_date')
        if due_date:
            task.due_date = self._parse_date(
                due_date, 'Formato de data inválido. Use YYYY-MM-DD'
            )

        tags = data.get('tags')
        if tags:
            task.set_tags(tags)

        self._tasks.add(task)
        self._tasks.commit()

        if user and self._notifications:
            self._notifications.notify_task_assigned(user, task)

        return task.to_dict()

    def update(self, task_id, data):
        task = self._require_task(task_id)
        if not data:
            raise ValidationError('Dados inválidos')

        if 'title' in data:
            task.title = self._validate_title(data['title'])

        if 'description' in data:
            task.description = data['description']

        if 'status' in data:
            self._validate_status(data['status'])
            task.status = data['status']

        if 'priority' in data:
            task.priority = self._validate_priority(data['priority'])

        if 'user_id' in data:
            if data['user_id'] and not self._users.get(data['user_id']):
                raise NotFoundError('Usuário não encontrado')
            task.user_id = data['user_id']

        if 'category_id' in data:
            if data['category_id'] and not self._categories.get(data['category_id']):
                raise NotFoundError('Categoria não encontrada')
            task.category_id = data['category_id']

        if 'due_date' in data:
            if data['due_date']:
                task.due_date = self._parse_date(
                    data['due_date'], 'Formato de data inválido'
                )
            else:
                task.due_date = None

        if 'tags' in data:
            task.set_tags(data['tags'])

        task.updated_at = utcnow()
        self._tasks.commit()
        return task.to_dict()

    def delete(self, task_id):
        task = self._require_task(task_id)
        self._tasks.delete(task)
        self._tasks.commit()
        return {'message': 'Task deletada com sucesso'}

    # ---------- helpers ----------

    def _require_task(self, task_id):
        task = self._tasks.get(task_id)
        if not task:
            raise NotFoundError('Task não encontrada')
        return task

    def _validate_title(self, title, required=False):
        if not title:
            if required:
                raise ValidationError('Título é obrigatório')
            raise ValidationError('Título muito curto')
        if len(title) < MIN_TITLE_LENGTH:
            raise ValidationError('Título muito curto')
        if len(title) > MAX_TITLE_LENGTH:
            raise ValidationError('Título muito longo')
        return title

    def _validate_status(self, status):
        if status not in VALID_STATUSES:
            raise ValidationError('Status inválido')

    def _validate_priority(self, priority):
        if isinstance(priority, bool):
            raise ValidationError('Prioridade deve ser entre 1 e 5')
        try:
            value = int(priority)
        except (TypeError, ValueError):
            raise ValidationError('Prioridade deve ser entre 1 e 5')
        if value < MIN_PRIORITY or value > MAX_PRIORITY:
            raise ValidationError('Prioridade deve ser entre 1 e 5')
        return value

    def _parse_date(self, value, message):
        try:
            return datetime.strptime(value, DATE_FORMAT)
        except (TypeError, ValueError):
            raise ValidationError(message)

    def _parse_int(self, value, message):
        if value in (None, ''):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValidationError(message)
