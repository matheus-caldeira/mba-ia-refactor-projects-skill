import pytest

ROTAS_AUTENTICADAS = [
    ('get', '/tasks'),
    ('get', '/tasks/search?q=Task'),
    ('get', '/tasks/stats'),
    ('get', '/tasks/1'),
    ('post', '/tasks'),
    ('put', '/tasks/1'),
    ('delete', '/tasks/1'),
    ('get', '/users'),
    ('get', '/users/1'),
    ('put', '/users/1'),
    ('delete', '/users/1'),
    ('get', '/users/1/tasks'),
    ('get', '/reports/summary'),
    ('get', '/reports/user/1'),
    ('get', '/categories'),
    ('post', '/categories'),
    ('put', '/categories/1'),
    ('delete', '/categories/1'),
]


@pytest.mark.parametrize('metodo,rota', ROTAS_AUTENTICADAS)
def test_rota_sem_token_responde_401(client, metodo, rota):
    resposta = getattr(client, metodo)(rota, json={})
    assert resposta.status_code == 401


def test_token_forjado_no_formato_antigo_responde_401(client):
    resposta = client.get('/tasks', headers={'Authorization': 'Bearer fake-jwt-token-1'})
    assert resposta.status_code == 401


def test_rotas_publicas_continuam_abertas(client):
    assert client.get('/').status_code == 200
    assert client.get('/health').status_code == 200
    novo = client.post('/users', json={'name': 'Novo', 'email': 'novo@x.com', 'password': 'segredo1'})
    assert novo.status_code == 201
    assert 'password' not in novo.get_json()


def test_usuario_nao_altera_outro_usuario(client, auth, ids):
    maria = auth('maria@x.com')
    ana_id = ids['users']['ana@x.com']
    resposta = client.put(f'/users/{ana_id}', json={'name': 'Hackeada', 'password': 'nova-senha'}, headers=maria)
    assert resposta.status_code == 403
    assert client.post('/login', json={'email': 'ana@x.com', 'password': 'senha-de-teste'}).status_code == 200


def test_usuario_nao_promove_a_si_mesmo(client, auth, ids):
    maria = auth('maria@x.com')
    maria_id = ids['users']['maria@x.com']
    assert client.put(f'/users/{maria_id}', json={'role': 'admin'}, headers=maria).status_code == 403
    assert client.put(f'/users/{maria_id}', json={'active': False}, headers=maria).status_code == 403


def test_troca_da_propria_senha_exige_senha_atual(client, auth, ids):
    maria = auth('maria@x.com')
    maria_id = ids['users']['maria@x.com']
    sem_atual = client.put(f'/users/{maria_id}', json={'password': 'nova-senha'}, headers=maria)
    assert sem_atual.status_code == 403
    com_atual = client.put(
        f'/users/{maria_id}',
        json={'password': 'nova-senha', 'current_password': 'senha-de-teste'},
        headers=maria,
    )
    assert com_atual.status_code == 200
    assert client.post('/login', json={'email': 'maria@x.com', 'password': 'nova-senha'}).status_code == 200


def test_usuario_atualiza_o_proprio_nome(client, auth, ids):
    maria = auth('maria@x.com')
    resposta = client.put(f"/users/{ids['users']['maria@x.com']}", json={'name': 'Maria S.'}, headers=maria)
    assert resposta.status_code == 200
    assert resposta.get_json()['name'] == 'Maria S.'


def test_admin_altera_role_e_senha_de_outro_usuario(client, auth, ids):
    admin = auth('admin@x.com')
    ana_id = ids['users']['ana@x.com']
    resposta = client.put(f'/users/{ana_id}', json={'role': 'manager', 'password': 'definida-pelo-admin'},
                          headers=admin)
    assert resposta.status_code == 200
    assert resposta.get_json()['role'] == 'manager'


def test_leitura_de_dados_de_outro_usuario(client, auth, ids):
    maria = auth('maria@x.com')
    ana_id = ids['users']['ana@x.com']
    assert client.get(f'/users/{ana_id}', headers=maria).status_code == 403
    assert client.get(f'/users/{ana_id}/tasks', headers=maria).status_code == 403
    assert client.get(f'/reports/user/{ana_id}', headers=maria).status_code == 403
    assert client.get('/users', headers=maria).status_code == 403
    assert client.get('/reports/summary', headers=maria).status_code == 403
    gerente = auth('pedro@x.com')
    assert client.get(f'/users/{ana_id}', headers=gerente).status_code == 200
    assert client.get('/reports/summary', headers=gerente).status_code == 200


def test_task_de_outro_usuario_nao_pode_ser_alterada_nem_apagada(client, auth, ids):
    maria = auth('maria@x.com')
    task_ana = ids['tasks']['Task da Ana']
    assert client.put(f'/tasks/{task_ana}', json={'status': 'done'}, headers=maria).status_code == 403
    assert client.delete(f'/tasks/{task_ana}', headers=maria).status_code == 403
    task_maria = ids['tasks']['Task da Maria']
    assert client.put(f'/tasks/{task_maria}', json={'status': 'done'}, headers=maria).status_code == 200


def test_usuario_nao_atribui_task_a_outro(client, auth, ids):
    maria = auth('maria@x.com')
    ana_id = ids['users']['ana@x.com']
    resposta = client.post('/tasks', json={'title': 'Para a Ana', 'user_id': ana_id}, headers=maria)
    assert resposta.status_code == 403
    propria = client.post('/tasks', json={'title': 'Minha task', 'user_id': ids['users']['maria@x.com']},
                          headers=maria)
    assert propria.status_code == 201


def test_categorias_so_admin_ou_manager_alteram(client, auth):
    maria = auth('maria@x.com')
    assert client.get('/categories', headers=maria).status_code == 200
    assert client.post('/categories', json={'name': 'QA'}, headers=maria).status_code == 403
    assert client.post('/categories', json={'name': 'QA'}, headers=auth('pedro@x.com')).status_code == 201


def test_exclusao_de_usuario_exige_admin(client, auth, ids):
    ana_id = ids['users']['ana@x.com']
    assert client.delete(f'/users/{ana_id}', headers=auth('pedro@x.com')).status_code == 403
    assert client.delete(f'/users/{ana_id}', headers=auth('admin@x.com')).status_code == 200


def test_cadastro_publico_nao_cria_admin(client):
    resposta = client.post('/users', json={'name': 'H', 'email': 'h@x.com', 'password': 'segredo1', 'role': 'admin'})
    assert resposta.status_code == 403


def test_resposta_nunca_expoe_hash_de_senha(client, auth, ids):
    admin = auth('admin@x.com')
    for rota in ('/users', f"/users/{ids['users']['maria@x.com']}"):
        assert 'password' not in client.get(rota, headers=admin).get_data(as_text=True)
