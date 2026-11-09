import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATABASE_PATH"] = os.path.join(tempfile.mkdtemp(), "loja-import.db")

from app import create_app  # noqa: E402
from config import settings  # noqa: E402

SENHAS_SEED = {"admin@loja.com": "admin123", "joao@email.com": "123456", "maria@email.com": "senha123"}


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_PATH", str(tmp_path / "loja-teste.db"))
    application = create_app(settings)
    application.config["TESTING"] = True
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def token_de(client):
    def _login(email):
        resposta = client.post("/login", json={"email": email, "senha": SENHAS_SEED[email]})
        assert resposta.status_code == 200
        return {"Authorization": f"Bearer {resposta.get_json()['token']}"}

    return _login


@pytest.fixture()
def admin(token_de):
    return token_de("admin@loja.com")


@pytest.fixture()
def joao(token_de):
    return token_de("joao@email.com")
