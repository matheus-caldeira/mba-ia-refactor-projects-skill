import os
import subprocess
import sys

import pytest

from app import create_app
from config.settings import MissingConfigError, load_settings

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def titles(response):
    return sorted(task['title'] for task in response.get_json())


def test_usuario_le_apenas_a_propria_task(client, auth, ids):
    maria = auth('maria@x.com')
    assert client.get(f"/tasks/{ids['tasks']['Task da Maria']}", headers=maria).status_code == 200
    assert client.get(f"/tasks/{ids['tasks']['Task da Ana']}", headers=maria).status_code == 403


def test_listagem_de_usuario_comum_tem_escopo_do_ator(client, auth):
    response = client.get('/tasks', headers=auth('maria@x.com'))
    assert response.status_code == 200
    assert titles(response) == ['Task da Maria']


def test_supervisor_lista_todas_as_tasks(client, auth):
    for email in ('admin@x.com', 'pedro@x.com'):
        assert titles(client.get('/tasks', headers=auth(email))) == ['Task da Ana', 'Task da Maria']


def test_busca_de_usuario_comum_tem_escopo_do_ator(client, auth, ids):
    maria = auth('maria@x.com')
    assert titles(client.get('/tasks/search?q=Task', headers=maria)) == ['Task da Maria']
    other = client.get(f"/tasks/search?user_id={ids['users']['ana@x.com']}", headers=maria)
    assert other.status_code == 403
    own = client.get(f"/tasks/search?user_id={ids['users']['maria@x.com']}", headers=maria)
    assert titles(own) == ['Task da Maria']


def test_supervisor_busca_por_qualquer_usuario(client, auth, ids):
    response = client.get(f"/tasks/search?user_id={ids['users']['ana@x.com']}", headers=auth('pedro@x.com'))
    assert titles(response) == ['Task da Ana']


def test_estatisticas_de_usuario_comum_cobrem_so_as_proprias_tasks(client, auth):
    own = client.get('/tasks/stats', headers=auth('maria@x.com')).get_json()
    assert own['total'] == 1
    assert own['overdue'] == 1
    assert client.get('/tasks/stats', headers=auth('admin@x.com')).get_json()['total'] == 2


def test_contagem_por_categoria_respeita_o_escopo(client, auth, app, ids):
    with app.app_context():
        from database import db
        from models.task import Task

        task = db.session.get(Task, ids['tasks']['Task da Ana'])
        task.category_id = 1
        db.session.commit()
    assert client.get('/categories', headers=auth('maria@x.com')).get_json()[0]['task_count'] == 0
    assert client.get('/categories', headers=auth('admin@x.com')).get_json()[0]['task_count'] == 1


@pytest.mark.parametrize('missing', ['SECRET_KEY', 'ADMIN_EMAIL', 'ADMIN_PASSWORD'])
def test_producao_sem_credencial_obrigatoria_falha_no_boot(missing):
    env = {
        'APP_ENV': 'production',
        'SECRET_KEY': 'segredo-de-producao',
        'ADMIN_EMAIL': 'ops@empresa.com',
        'ADMIN_PASSWORD': 'senha-forte-de-producao',
    }
    env.pop(missing)
    with pytest.raises(MissingConfigError, match=missing):
        load_settings(env)


def test_producao_cria_admin_apenas_com_credenciais_do_ambiente(tmp_path):
    settings = load_settings({
        'APP_ENV': 'production',
        'SECRET_KEY': 'segredo-de-producao',
        'ADMIN_EMAIL': 'ops@empresa.com',
        'ADMIN_PASSWORD': 'senha-forte-de-producao',
        'DATABASE_URL': 'sqlite:///' + str(tmp_path / 'prod.db'),
    })
    client = create_app(settings).test_client()
    login = client.post('/login', json={'email': 'ops@empresa.com', 'password': 'senha-forte-de-producao'})
    assert login.status_code == 200
    assert login.get_json()['user']['role'] == 'admin'
    seed_login = client.post('/login', json={'email': 'joao@email.com', 'password': 'dev-password-123'})
    assert seed_login.status_code == 401


def test_seed_se_recusa_a_rodar_em_producao(tmp_path):
    env = {
        **os.environ,
        'APP_ENV': 'production',
        'SECRET_KEY': 'segredo-de-producao',
        'ADMIN_EMAIL': 'ops@empresa.com',
        'ADMIN_PASSWORD': 'senha-forte-de-producao',
        'DATABASE_URL': 'sqlite:///' + str(tmp_path / 'prod.db'),
    }
    result = subprocess.run([sys.executable, 'seed.py'], cwd=PROJECT_DIR, env=env,
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert 'só roda fora de produção' in result.stderr
