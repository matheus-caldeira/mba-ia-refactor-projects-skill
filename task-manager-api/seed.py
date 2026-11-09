"""Popula o banco com dados iniciais de desenvolvimento.

As senhas vêm de variável de ambiente (``SEED_PASSWORD``) com fallback de dev,
e são gravadas com o mesmo KDF da aplicação — não há mais senha trivial fixa
no código.
"""

import os
from datetime import timedelta

from app import app, init_database
from database import db
from models.category import Category
from models.clock import utcnow
from models.task import Task
from models.user import User

DEV_ONLY_SEED_PASSWORD = 'dev-password-123'
SEED_PASSWORD = os.environ.get('SEED_PASSWORD', DEV_ONLY_SEED_PASSWORD)


def seed_data():
    if app.extensions['settings'].IS_PRODUCTION:
        raise SystemExit('seed.py popula contas de exemplo com senha conhecida e só roda fora de produção.')
    init_database(app)
    with app.app_context():
        Task.query.delete()
        User.query.delete()
        Category.query.delete()
        db.session.commit()

        users_data = [
            ('João Silva', 'joao@email.com', 'admin'),
            ('Maria Santos', 'maria@email.com', 'user'),
            ('Pedro Oliveira', 'pedro@email.com', 'manager'),
        ]
        users = []
        for name, email, role in users_data:
            u = User()
            u.name = name
            u.email = email
            u.set_password(SEED_PASSWORD)
            u.role = role
            db.session.add(u)
            users.append(u)
        db.session.commit()
        u1, u2, u3 = users

        categories_data = [
            ('Backend', 'Tarefas de backend', '#3498db'),
            ('Frontend', 'Tarefas de frontend', '#2ecc71'),
            ('DevOps', 'Tarefas de infraestrutura', '#e74c3c'),
            ('Bug', 'Correção de bugs', '#e67e22'),
        ]
        categories = []
        for name, description, color in categories_data:
            c = Category()
            c.name = name
            c.description = description
            c.color = color
            db.session.add(c)
            categories.append(c)
        db.session.commit()
        c1, c2, c3, c4 = categories

        now = utcnow()
        tasks_data = [
            {'title': 'Implementar autenticação JWT', 'description': 'Adicionar autenticação real com JWT', 'status': 'pending', 'priority': 1, 'user_id': u1.id, 'category_id': c1.id, 'due_date': now - timedelta(days=3)},
            {'title': 'Criar tela de login', 'description': 'Tela de login responsiva', 'status': 'in_progress', 'priority': 2, 'user_id': u2.id, 'category_id': c2.id, 'due_date': now + timedelta(days=5)},
            {'title': 'Configurar CI/CD', 'description': 'Pipeline com GitHub Actions', 'status': 'done', 'priority': 2, 'user_id': u3.id, 'category_id': c3.id, 'tags': 'devops,ci,github'},
            {'title': 'Corrigir bug no filtro de busca', 'description': 'Filtro não funciona com caracteres especiais', 'status': 'pending', 'priority': 1, 'user_id': u1.id, 'category_id': c4.id, 'due_date': now - timedelta(days=1)},
            {'title': 'Adicionar paginação na API', 'description': 'Endpoints retornam todos os registros', 'status': 'pending', 'priority': 3, 'user_id': u1.id, 'category_id': c1.id, 'due_date': now + timedelta(days=10)},
            {'title': 'Escrever testes unitários', 'description': 'Cobertura mínima de 80%', 'status': 'pending', 'priority': 2, 'user_id': u2.id, 'category_id': c1.id},
            {'title': 'Documentar API com Swagger', 'description': 'Gerar documentação automática', 'status': 'cancelled', 'priority': 4, 'user_id': u3.id, 'category_id': c1.id},
            {'title': 'Refatorar models', 'description': 'Melhorar organização dos models', 'status': 'in_progress', 'priority': 3, 'user_id': u2.id, 'category_id': c1.id, 'tags': 'refactor,tech-debt'},
            {'title': 'Configurar monitoramento', 'description': 'Prometheus + Grafana', 'status': 'pending', 'priority': 4, 'user_id': u3.id, 'category_id': c3.id, 'due_date': now + timedelta(days=20)},
            {'title': 'Melhorar validações de input', 'description': 'Usar marshmallow ou pydantic', 'status': 'pending', 'priority': 3, 'user_id': u1.id, 'category_id': c1.id, 'tags': 'improvement,validation'},
        ]

        for td in tasks_data:
            t = Task()
            t.title = td['title']
            t.description = td['description']
            t.status = td['status']
            t.priority = td['priority']
            t.user_id = td['user_id']
            t.category_id = td['category_id']
            if 'due_date' in td:
                t.due_date = td['due_date']
            if 'tags' in td:
                t.tags = td['tags']
            db.session.add(t)

        db.session.commit()
        print('Seed concluído com sucesso!')
        print(f'  {User.query.count()} usuários')
        print(f'  {Category.query.count()} categorias')
        print(f'  {Task.query.count()} tasks')


if __name__ == '__main__':
    seed_data()
