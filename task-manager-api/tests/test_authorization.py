"""Matriz rota × quem pode: 401 sem token, 403 para quem não é dono nem supervisor."""
import hashlib

import pytest

from config import ConfigError, Settings
from database import db
from models.user import User
from seed import seed_data

# Ids do seed: 1 = admin (joao), 2 = user (maria), 3 = manager (pedro).
# Task 1 é do admin; task 2 é da maria.
PROTECTED = [
    ("get", "/tasks"), ("get", "/tasks/1"), ("post", "/tasks"), ("put", "/tasks/1"),
    ("delete", "/tasks/1"), ("get", "/tasks/search"), ("get", "/tasks/stats"),
    ("get", "/users"), ("get", "/users/1"), ("put", "/users/1"), ("delete", "/users/1"),
    ("get", "/users/1/tasks"), ("get", "/reports/summary"), ("get", "/reports/user/1"),
    ("get", "/categories"), ("post", "/categories"), ("put", "/categories/1"),
    ("delete", "/categories/1"),
]

FORBIDDEN_FOR_USER = [
    ("get", "/tasks/1", None), ("put", "/tasks/1", {"status": "done"}), ("delete", "/tasks/1", None),
    ("get", "/tasks/search?user_id=1", None),
    ("post", "/tasks", {"title": "Para outro", "user_id": 1}),
    ("put", "/tasks/2", {"user_id": 1}),
    ("get", "/users/1", None), ("put", "/users/1", {"name": "x"}), ("delete", "/users/3", None),
    ("get", "/users/1/tasks", None), ("get", "/reports/summary", None), ("get", "/reports/user/1", None),
    ("post", "/categories", {"name": "QA"}), ("put", "/categories/1", {"name": "x"}),
    ("delete", "/categories/1", None),
]


@pytest.mark.parametrize("method,path", PROTECTED)
def test_protected_routes_require_token(client, method, path):
    assert getattr(client, method)(path, json={}).status_code == 401


def test_invalid_token_is_rejected(client):
    response = client.get("/tasks", headers={"Authorization": "Bearer fake-jwt-token-1"})
    assert response.status_code == 401


@pytest.mark.parametrize("method,path,body", FORBIDDEN_FOR_USER)
def test_user_cannot_touch_other_users_resources(client, user, method, path, body):
    assert getattr(client, method)(path, json=body, headers=user).status_code == 403


def test_public_routes(client):
    assert client.get("/").status_code == 200
    assert client.get("/health").status_code == 200


def test_reads_are_scoped_to_the_actor(client, user):
    tasks = client.get("/tasks", headers=user).get_json()
    assert tasks and {t["user_id"] for t in tasks} == {2}
    assert {t["user_id"] for t in client.get("/tasks/search", headers=user).get_json()} == {2}
    assert client.get("/tasks/stats", headers=user).get_json()["total"] == len(tasks)
    assert [u["id"] for u in client.get("/users", headers=user).get_json()] == [2]
    categories = client.get("/categories", headers=user).get_json()
    assert sum(c["task_count"] for c in categories) == len(tasks)
    assert client.get("/users/2", headers=user).status_code == 200
    assert client.get("/reports/user/2", headers=user).status_code == 200


def test_supervisors_see_the_whole_team(client, admin, manager):
    for headers in (admin, manager):
        assert len(client.get("/tasks", headers=headers).get_json()) == 10
        assert client.get("/reports/summary", headers=headers).status_code == 200
    assert client.delete("/users/2", headers=manager).status_code == 403


def test_user_creates_task_for_self_by_default(client, user):
    response = client.post("/tasks", json={"title": "Minha task"}, headers=user)
    assert response.status_code == 201
    assert response.get_json()["user_id"] == 2


def test_role_and_active_require_admin(client, user, admin):
    anon = client.post("/users", json={"name": "X", "email": "x@email.com", "password": "abcd", "role": "admin"})
    assert anon.status_code == 403
    assert client.put("/users/2", json={"role": "admin"}, headers=user).status_code == 403
    assert client.put("/users/2", json={"active": False}, headers=user).status_code == 403
    created = client.post("/users", json={"name": "Y", "email": "y@email.com", "password": "abcd", "role": "manager"}, headers=admin)
    assert created.status_code == 201 and created.get_json()["role"] == "manager"
    public = client.post("/users", json={"name": "Z", "email": "z@email.com", "password": "abcd"})
    assert public.status_code == 201 and public.get_json()["role"] == "user"


def test_password_change_requires_current_password(client, user):
    assert client.put("/users/2", json={"password": "nova1234"}, headers=user).status_code == 403
    ok = client.put("/users/2", json={"password": "nova1234", "current_password": "abcd"}, headers=user)
    assert ok.status_code == 200
    assert client.post("/login", json={"email": "maria@email.com", "password": "nova1234"}).status_code == 200


def test_password_hash_never_leaves_the_api(client, admin):
    for path in ("/users", "/users/1"):
        assert "password" not in client.get(path, headers=admin).get_data(as_text=True)
    login = client.post("/login", json={"email": "joao@email.com", "password": "1234"}).get_json()
    assert "password" not in login["user"]


def test_invalid_input_returns_400_not_500(client, admin):
    assert client.post("/tasks", json={"title": "abc", "priority": "alta"}, headers=admin).status_code == 400
    assert client.put("/tasks/1", json={"title": 123}, headers=admin).status_code == 400
    assert client.get("/tasks/search?priority=x", headers=admin).status_code == 400
    assert client.put("/categories/1", headers=admin).status_code == 400
    assert client.post("/categories", json={"name": "QA", "color": "azul"}, headers=admin).status_code == 400


def test_duplicate_email_is_409(client):
    body = {"name": "Ana", "email": "maria@email.com", "password": "abcd"}
    assert client.post("/users", json=body).status_code == 409


def test_legacy_md5_hash_is_upgraded_on_login(client, app):
    with app.app_context():
        maria = db.session.get(User, 2)
        maria.password = hashlib.md5(b"abcd").hexdigest()
        db.session.commit()
    assert client.post("/login", json={"email": "maria@email.com", "password": "abcd"}).status_code == 200
    with app.app_context():
        assert db.session.get(User, 2).password.startswith("scrypt:")


def test_settings_require_secret_key():
    with pytest.raises(ConfigError):
        Settings.from_env({})


def test_production_seed_has_no_known_password_accounts(tmp_path):
    base = {"SECRET_KEY": "x" * 40, "APP_ENV": "production", "DATABASE_URL": f"sqlite:///{tmp_path / 'p.db'}"}
    with pytest.raises(ConfigError):
        seed_data(settings=Settings.from_env(base))
    env = {**base, "SEED_ADMIN_EMAIL": "ops@empresa.com", "SEED_ADMIN_PASSWORD": "uma-senha-forte-do-ambiente"}
    settings = Settings.from_env(env)
    seed_data(settings=settings)
    from app import create_app
    client = create_app(settings).test_client()
    for email, password in (("joao@email.com", "1234"), ("pedro@email.com", "pass"), ("maria@email.com", "abcd")):
        assert client.post("/login", json={"email": email, "password": password}).status_code == 401
    assert client.post("/login", json={"email": "ops@empresa.com", "password": "uma-senha-forte-do-ambiente"}).status_code == 200
    with pytest.raises(ConfigError):
        seed_data(reset=True, settings=settings)
