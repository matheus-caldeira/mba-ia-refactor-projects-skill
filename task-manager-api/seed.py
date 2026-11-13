"""Popula o banco com dados iniciais.

    python seed.py            # banco vazio: cria admin + dados de exemplo
    python seed.py --reset    # apaga tudo antes (recusado em produção)

Em produção só a conta admin é criada, com SEED_ADMIN_EMAIL/SEED_ADMIN_PASSWORD
obrigatórios. As contas de exemplo (senhas conhecidas) existem só fora de produção.
"""
import sys
from datetime import timedelta

from sqlalchemy import delete

from app import create_app
from config import ConfigError, Settings
from database import commit, db
from models.category import Category
from models.task import Task
from models.user import ROLE_ADMIN, ROLE_MANAGER, ROLE_USER, User
from utils.clock import utcnow

# Somente desenvolvimento: credenciais públicas das contas de demonstração.
DEV_ADMIN = ("João Silva", "joao@email.com", "1234")
DEV_USERS = [
    ("Maria Santos", "maria@email.com", "abcd", ROLE_USER),
    ("Pedro Oliveira", "pedro@email.com", "pass", ROLE_MANAGER),
]
CATEGORIES = [
    ("Backend", "Tarefas de backend", "#3498db"),
    ("Frontend", "Tarefas de frontend", "#2ecc71"),
    ("DevOps", "Tarefas de infraestrutura", "#e74c3c"),
    ("Bug", "Correção de bugs", "#e67e22"),
]


def _admin_credentials(settings):
    if settings.SEED_ADMIN_EMAIL and settings.SEED_ADMIN_PASSWORD:
        return DEV_ADMIN[0], settings.SEED_ADMIN_EMAIL, settings.SEED_ADMIN_PASSWORD
    if settings.IS_PRODUCTION:
        raise ConfigError("SEED_ADMIN_EMAIL e SEED_ADMIN_PASSWORD são obrigatórios em produção")
    return DEV_ADMIN


def _user(name, email, password, role):
    user = User(name=name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    return user


def _demo_data(admin):
    maria, pedro = (_user(*data) for data in DEV_USERS)
    backend, frontend, devops, bug = (Category(name=n, description=d, color=c) for n, d, c in CATEGORIES)
    db.session.add_all([backend, frontend, devops, bug])
    db.session.flush()

    now = utcnow()
    tasks = [
        ("Implementar autenticação JWT", "Adicionar autenticação real com JWT", "pending", 1, admin, backend, now - timedelta(days=3), None),
        ("Criar tela de login", "Tela de login responsiva", "in_progress", 2, maria, frontend, now + timedelta(days=5), None),
        ("Configurar CI/CD", "Pipeline com GitHub Actions", "done", 2, pedro, devops, None, "devops,ci,github"),
        ("Corrigir bug no filtro de busca", "Filtro não funciona com caracteres especiais", "pending", 1, admin, bug, now - timedelta(days=1), None),
        ("Adicionar paginação na API", "Endpoints retornam todos os registros", "pending", 3, admin, backend, now + timedelta(days=10), None),
        ("Escrever testes unitários", "Cobertura mínima de 80%", "pending", 2, maria, backend, None, None),
        ("Documentar API com Swagger", "Gerar documentação automática", "cancelled", 4, pedro, backend, None, None),
        ("Refatorar models", "Melhorar organização dos models", "in_progress", 3, maria, backend, None, "refactor,tech-debt"),
        ("Configurar monitoramento", "Prometheus + Grafana", "pending", 4, pedro, devops, now + timedelta(days=20), None),
        ("Melhorar validações de input", "Usar marshmallow ou pydantic", "pending", 3, admin, backend, None, "improvement,validation"),
    ]
    for title, description, status, priority, owner, category, due_date, tags in tasks:
        db.session.add(Task(
            title=title, description=description, status=status, priority=priority,
            user_id=owner.id, category_id=category.id, due_date=due_date, tags=tags,
        ))


def seed_data(reset=False, settings=None):
    settings = settings or Settings.from_env()
    if reset and settings.IS_PRODUCTION:
        raise ConfigError("--reset é recusado em produção")
    admin_name, admin_email, admin_password = _admin_credentials(settings)

    app = create_app(settings)
    with app.app_context():
        if reset:
            for model in (Task, User, Category):
                db.session.execute(delete(model))
            commit()
        elif User.count() > 0:
            print("Banco já populado. Use --reset para recriar (apaga todos os dados).")
            return

        admin = _user(admin_name, admin_email, admin_password, ROLE_ADMIN)
        db.session.flush()
        if not settings.IS_PRODUCTION:
            _demo_data(admin)
        commit()

        print("Seed concluído com sucesso!")
        print(f"  {User.count()} usuários")
        print(f"  {Category.count()} categorias")
        print(f"  {Task.count()} tasks")


if __name__ == "__main__":
    seed_data(reset="--reset" in sys.argv[1:])
