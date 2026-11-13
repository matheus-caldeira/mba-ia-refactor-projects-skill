import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from config import Settings  # noqa: E402
from seed import seed_data  # noqa: E402

ADMIN = ("joao@email.com", "1234")      # contas de exemplo: somente desenvolvimento
USER = ("maria@email.com", "abcd")
MANAGER = ("pedro@email.com", "pass")


@pytest.fixture
def settings(tmp_path):
    return Settings.from_env({
        "SECRET_KEY": "test-secret-key",
        "APP_ENV": "test",
        "DATABASE_URL": f"sqlite:///{tmp_path / 'test.db'}",
    })


@pytest.fixture
def app(settings):
    seed_data(settings=settings)
    return create_app(settings)


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, credentials):
    email, password = credentials
    response = client.post("/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.get_json()
    return {"Authorization": f"Bearer {response.get_json()['token']}"}


@pytest.fixture
def admin(client):
    return login(client, ADMIN)


@pytest.fixture
def user(client):
    return login(client, USER)


@pytest.fixture
def manager(client):
    return login(client, MANAGER)
