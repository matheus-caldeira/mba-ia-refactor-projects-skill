"""Casos de uso de User. Sem HTTP, sem SQL cru."""

import re

from errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from models.user import ROLES, User

EMAIL_RE = re.compile(r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$')
MIN_PASSWORD_LENGTH = 4


class UserController:
    def __init__(self, user_repository, task_repository, auth_service):
        self._users = user_repository
        self._tasks = task_repository
        self._auth = auth_service

    # ---------- leitura ----------

    def list(self):
        users = self._users.list_all()
        task_counts = self._tasks.count_grouped_by_user()
        return [
            {
                'id': u.id,
                'name': u.name,
                'email': u.email,
                'role': u.role,
                'active': u.active,
                'created_at': str(u.created_at),
                'task_count': task_counts.get(u.id, 0),
            }
            for u in users
        ]

    def get(self, user_id):
        user = self._require_user(user_id)
        data = user.to_dict()
        data['tasks'] = [t.to_dict() for t in self._tasks.list_by_user(user_id)]
        return data

    def list_tasks(self, user_id):
        self._require_user(user_id)
        result = []
        for t in self._tasks.list_by_user(user_id):
            result.append(
                {
                    'id': t.id,
                    'title': t.title,
                    'description': t.description,
                    'status': t.status,
                    'priority': t.priority,
                    'created_at': str(t.created_at),
                    'due_date': str(t.due_date) if t.due_date else None,
                    'overdue': t.is_overdue(),
                }
            )
        return result

    # ---------- escrita ----------

    def create(self, data, actor=None):
        if not data:
            raise ValidationError('Dados inválidos')

        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', 'user')

        if not name:
            raise ValidationError('Nome é obrigatório')
        if not email:
            raise ValidationError('Email é obrigatório')
        if not password:
            raise ValidationError('Senha é obrigatória')

        self._validate_email_format(email)
        self._validate_password(password, 'Senha deve ter no mínimo 4 caracteres')

        if self._users.find_by_email(email):
            raise ConflictError('Email já cadastrado')

        self._validate_role(role)
        # Auto-cadastro não escolhe papel privilegiado: só um admin autenticado
        # pode criar usuário com role diferente de 'user'.
        if role != 'user' and not (actor and actor.is_admin()):
            raise ForbiddenError('Apenas administradores podem definir o role')

        user = User()
        user.name = name
        user.email = email
        user.set_password(password)
        user.role = role

        self._users.add(user)
        self._users.commit()
        return user.to_dict()

    def update(self, user_id, data, actor=None):
        user = self._require_user(user_id)
        if not data:
            raise ValidationError('Dados inválidos')

        if 'name' in data:
            user.name = data['name']

        if 'email' in data:
            self._validate_email_format(data['email'])
            existing = self._users.find_by_email(data['email'])
            if existing and existing.id != user_id:
                raise ConflictError('Email já cadastrado')
            user.email = data['email']

        if 'password' in data:
            self._validate_password(data['password'], 'Senha muito curta')
            user.set_password(data['password'])

        if 'role' in data:
            self._validate_role(data['role'])
            if not (actor and actor.is_admin()):
                raise ForbiddenError('Apenas administradores podem alterar o role')
            user.role = data['role']

        if 'active' in data:
            if not (actor and actor.is_admin()):
                raise ForbiddenError('Apenas administradores podem ativar/desativar')
            user.active = data['active']

        self._users.commit()
        return user.to_dict()

    def delete(self, user_id):
        user = self._require_user(user_id)
        self._tasks.delete_by_user(user_id)
        self._users.delete(user)
        self._users.commit()
        return {'message': 'Usuário deletado com sucesso'}

    def login(self, data):
        if not data:
            raise ValidationError('Dados inválidos')

        email = data.get('email')
        password = data.get('password')
        if not email or not password:
            raise ValidationError('Email e senha são obrigatórios')

        user = self._auth.authenticate(email, password)
        if not user.active:
            raise ForbiddenError('Usuário inativo')

        return {
            'message': 'Login realizado com sucesso',
            'user': user.to_dict(),
            'token': self._auth.issue_token(user),
        }

    # ---------- helpers ----------

    def _require_user(self, user_id):
        user = self._users.get(user_id)
        if not user:
            raise NotFoundError('Usuário não encontrado')
        return user

    def _validate_email_format(self, email):
        if not email or not EMAIL_RE.match(email):
            raise ValidationError('Email inválido')

    def _validate_password(self, password, message):
        if not password or len(password) < MIN_PASSWORD_LENGTH:
            raise ValidationError(message)

    def _validate_role(self, role):
        if role not in ROLES:
            raise ValidationError('Role inválido')
