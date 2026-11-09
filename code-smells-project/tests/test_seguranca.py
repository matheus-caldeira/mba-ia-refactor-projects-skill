import threading

import pytest

ROTAS_ADMIN = [
    ("get", "/usuarios", None),
    ("get", "/pedidos", None),
    ("get", "/relatorios/vendas", None),
    ("post", "/produtos", {"nome": "Livro", "preco": 10, "estoque": 1, "categoria": "livros"}),
    ("put", "/produtos/1", {"nome": "Notebook", "preco": 10, "estoque": 1, "categoria": "informatica"}),
    ("delete", "/produtos/1", None),
    ("put", "/pedidos/1/status", {"status": "aprovado"}),
    ("post", "/admin/reset-db", None),
]


def chamar(client, metodo, rota, corpo=None, headers=None):
    return getattr(client, metodo)(rota, json=corpo, headers=headers or {})


def estoque(client, produto_id):
    return client.get(f"/produtos/{produto_id}").get_json()["dados"]["estoque"]


@pytest.mark.parametrize("metodo,rota,corpo", ROTAS_ADMIN)
def test_rota_admin_sem_token_responde_401(client, metodo, rota, corpo):
    assert chamar(client, metodo, rota, corpo).status_code == 401


@pytest.mark.parametrize("metodo,rota,corpo", ROTAS_ADMIN)
def test_rota_admin_com_cliente_responde_403(client, joao, metodo, rota, corpo):
    assert chamar(client, metodo, rota, corpo, joao).status_code == 403


def test_admin_acessa_rotas_administrativas(client, admin):
    assert client.get("/usuarios", headers=admin).status_code == 200
    assert client.get("/relatorios/vendas", headers=admin).status_code == 200
    assert client.delete("/produtos/10", headers=admin).status_code == 200


def test_token_forjado_responde_401(client):
    resposta = client.get("/usuarios/1", headers={"Authorization": "Bearer fake-token-1"})
    assert resposta.status_code == 401


def test_usuario_le_apenas_os_proprios_dados(client, joao):
    assert client.get("/usuarios/2", headers=joao).status_code == 200
    assert client.get("/usuarios/1", headers=joao).status_code == 403
    assert client.get("/pedidos/usuario/2", headers=joao).status_code == 200
    assert client.get("/pedidos/usuario/3", headers=joao).status_code == 403


def test_pedido_so_pode_ser_criado_para_o_proprio_usuario(client, joao):
    item = [{"produto_id": 2, "quantidade": 1}]
    assert client.post("/pedidos", json={"usuario_id": 2, "itens": item}).status_code == 401
    assert client.post("/pedidos", json={"usuario_id": 3, "itens": item}, headers=joao).status_code == 403
    assert client.post("/pedidos", json={"usuario_id": 2, "itens": item}, headers=joao).status_code == 201


def test_rotas_publicas_continuam_abertas(client):
    assert client.get("/produtos").status_code == 200
    assert client.get("/produtos/busca?q=Mouse").status_code == 200
    assert client.get("/health").status_code == 200
    novo = client.post("/usuarios", json={"nome": "Ana", "email": "ana@x.com", "senha": "segredo1"})
    assert novo.status_code == 201


def test_login_nao_aceita_sql_injection_e_nao_expoe_senha(client, admin):
    resposta = client.post("/login", json={"email": "admin@loja.com' -- ", "senha": "x"})
    assert resposta.status_code == 401
    assert "senha" not in client.get("/usuarios", headers=admin).get_data(as_text=True)
    assert client.post("/admin/query", json={"sql": "SELECT 1"}).status_code == 404


def test_quantidades_repetidas_do_mesmo_produto_sao_somadas(client, joao):
    itens = [{"produto_id": 6, "quantidade": 5}, {"produto_id": 6, "quantidade": 5}]
    resposta = client.post("/pedidos", json={"usuario_id": 2, "itens": itens}, headers=joao)
    assert resposta.status_code == 400
    assert estoque(client, 6) == 8


def test_pedidos_concorrentes_nao_deixam_estoque_negativo(app, joao):
    resultados = []

    def comprar():
        with app.test_client() as cliente:
            resposta = cliente.post(
                "/pedidos",
                json={"usuario_id": 2, "itens": [{"produto_id": 6, "quantidade": 2}]},
                headers=joao,
            )
            resultados.append(resposta.status_code)

    threads = [threading.Thread(target=comprar) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(resultados) == [201] * 4 + [400] * 4
    assert estoque(app.test_client(), 6) == 0


def test_cancelamento_devolve_estoque(client, admin, joao):
    criado = client.post(
        "/pedidos", json={"usuario_id": 2, "itens": [{"produto_id": 1, "quantidade": 3}]}, headers=joao
    )
    pedido_id = criado.get_json()["dados"]["pedido_id"]
    assert estoque(client, 1) == 7
    assert client.put(f"/pedidos/{pedido_id}/status", json={"status": "cancelado"}, headers=admin).status_code == 200
    assert estoque(client, 1) == 10
