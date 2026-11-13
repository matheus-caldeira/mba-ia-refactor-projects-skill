import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app  # noqa: E402
from config import Settings  # noqa: E402


def _settings(tmp_path, **extra):
    env = {"APP_ENV": "development", "SECRET_KEY": "chave-de-teste", "DB_PATH": str(tmp_path / "teste.db")}
    env.update(extra)
    return Settings(env)


@pytest.fixture
def make_app(tmp_path):
    return lambda **extra: create_app(_settings(tmp_path, **extra))


@pytest.fixture
def client(make_app):
    return make_app(ENABLE_RESET_DB="true").test_client()


def _token(client, email, senha):
    resposta = client.post("/login", json={"email": email, "senha": senha})
    assert resposta.status_code == 200, resposta.get_json()
    return resposta.get_json()["token"]


@pytest.fixture
def headers(client):
    """Cabeçalhos de admin, do João (id 2) e da Maria (id 3) — contas de demonstração."""
    return {
        "admin": {"Authorization": "Bearer " + _token(client, "admin@loja.com", "admin123")},
        "joao": {"Authorization": "Bearer " + _token(client, "joao@email.com", "123456")},
        "maria": {"Authorization": "Bearer " + _token(client, "maria@email.com", "senha123")},
    }
