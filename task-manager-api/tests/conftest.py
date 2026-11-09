import os
import sys
import tempfile
from datetime import timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(tempfile.mkdtemp(), 'import.db')

from app import create_app  # noqa: E402
from config.settings import load_settings  # noqa: E402
from database import db  # noqa: E402
from models.category import Category  # noqa: E402
from models.clock import utcnow  # noqa: E402
from models.task import Task  # noqa: E402
from models.user import User  # noqa: E402

PASSWORD = 'senha-de-teste'


def _seed():
    users = {}
    for name, email, role in (
        ('Admin', 'admin@x.com', 'admin'),
        ('Maria', 'maria@x.com', 'user'),
        ('Pedro', 'pedro@x.com', 'manager'),
        ('Ana', 'ana@x.com', 'user'),
    ):
        user = User(name=name, email=email, role=role)
        user.set_password(PASSWORD)
        db.session.add(user)
        users[email] = user
    db.session.add(Category(name='Backend', color='#3498db'))
    db.session.commit()
    db.session.add(Task(title='Task da Maria', user_id=users['maria@x.com'].id, priority=2,
                        due_date=utcnow() - timedelta(days=1)))
    db.session.add(Task(title='Task da Ana', user_id=users['ana@x.com'].id, priority=3))
    db.session.commit()


@pytest.fixture()
def app(tmp_path):
    settings = load_settings({
        'APP_ENV': 'development',
        'SECRET_KEY': 'segredo-de-teste',
        'DATABASE_URL': 'sqlite:///' + str(tmp_path / 'tasks.db'),
    })
    application = create_app(settings)
    application.config['TESTING'] = True
    with application.app_context():
        _seed()
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth(client):
    def _login(email, password=PASSWORD):
        response = client.post('/login', json={'email': email, 'password': password})
        assert response.status_code == 200, response.get_json()
        return {'Authorization': f"Bearer {response.get_json()['token']}"}

    return _login


@pytest.fixture()
def ids(app):
    with app.app_context():
        users = {u.email: u.id for u in User.query.all()}
        tasks = {t.title: t.id for t in Task.query.all()}
    return {'users': users, 'tasks': tasks}
