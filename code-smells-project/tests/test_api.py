import pytest

from config import ConfigError, Settings

PRODUTO = {"nome": "Caneca", "descricao": "x", "preco": 25.5, "estoque": 3, "categoria": "geral"}
PEDIDO_JOAO = {"itens": [{"produto_id": 2, "quantidade": 1}]}

# (método, caminho, corpo) de toda rota que exige autenticação
ROTAS_PROTEGIDAS = [
    ("get", "/usuarios", None),
    ("get", "/usuarios/2", None),
    ("post", "/pedidos", PEDIDO_JOAO),
    ("get", "/pedidos", None),
    ("get", "/pedidos/usuario/2", None),
    ("put", "/pedidos/1/status", {"status": "aprovado"}),
    ("get", "/relatorios/vendas", None),
    ("post", "/produtos", PRODUTO),
    ("put", "/produtos/1", PRODUTO),
    ("delete", "/produtos/1", None),
    ("post", "/admin/reset-db", None),
]

# Rotas que a Maria (cliente, id 3) não pode usar sobre recursos do João (id 2) ou de admin
ROTAS_PROIBIDAS_PARA_MARIA = [
    ("get", "/usuarios/2", None),
    ("get", "/pedidos/usuario/2", None),
    ("post", "/pedidos", {"usuario_id": 2, **PEDIDO_JOAO}),
    ("put", "/pedidos/1/status", {"status": "aprovado"}),
    ("get", "/relatorios/vendas", None),
    ("post", "/produtos", PRODUTO),
    ("put", "/produtos/1", PRODUTO),
    ("delete", "/produtos/1", None),
    ("post", "/admin/reset-db", None),
]


def _chamar(client, metodo, caminho, corpo, headers=None):
    return getattr(client, metodo)(caminho, json=corpo, headers=headers or {})


# --- rotas públicas e contrato -------------------------------------------------

def test_rotas_publicas_respondem(client):
    assert client.get("/").status_code == 200
    assert client.get("/produtos").get_json()["sucesso"] is True
    busca = client.get("/produtos/busca?q=Mouse").get_json()
    assert busca["total"] == 1 and busca["dados"][0]["nome"] == "Mouse Wireless"
    assert client.get("/produtos/1").status_code == 200
    assert client.get("/produtos/999").status_code == 404


def test_health_nao_vaza_configuracao(client):
    corpo = client.get("/health").get_json()
    assert corpo["status"] == "ok"
    for campo in ("secret_key", "db_path", "debug", "ambiente"):
        assert campo not in corpo


def test_admin_query_removido(client, headers):
    assert client.post("/admin/query", json={"sql": "SELECT 1"}, headers=headers["admin"]).status_code == 404


# --- autenticação e autorização ------------------------------------------------

@pytest.mark.parametrize("metodo,caminho,corpo", ROTAS_PROTEGIDAS)
def test_rota_protegida_sem_token_retorna_401(client, metodo, caminho, corpo):
    assert _chamar(client, metodo, caminho, corpo).status_code == 401


@pytest.mark.parametrize("metodo,caminho,corpo", ROTAS_PROTEGIDAS)
def test_rota_protegida_com_token_invalido_retorna_401(client, metodo, caminho, corpo):
    resposta = _chamar(client, metodo, caminho, corpo, {"Authorization": "Bearer forjado"})
    assert resposta.status_code == 401


@pytest.mark.parametrize("metodo,caminho,corpo", ROTAS_PROIBIDAS_PARA_MARIA)
def test_cliente_sem_posse_nem_admin_recebe_403(client, headers, metodo, caminho, corpo):
    client.post("/pedidos", json=PEDIDO_JOAO, headers=headers["joao"])  # garante o pedido 1 do João
    assert _chamar(client, metodo, caminho, corpo, headers["maria"]).status_code == 403


def test_leituras_devolvem_apenas_escopo_do_ator(client, headers):
    client.post("/pedidos", json=PEDIDO_JOAO, headers=headers["joao"])

    usuarios_maria = client.get("/usuarios", headers=headers["maria"]).get_json()["dados"]
    assert [u["id"] for u in usuarios_maria] == [3]
    assert client.get("/pedidos", headers=headers["maria"]).get_json()["dados"] == []

    pedidos_joao = client.get("/pedidos", headers=headers["joao"]).get_json()["dados"]
    assert {p["usuario_id"] for p in pedidos_joao} == {2}
    assert len(client.get("/usuarios", headers=headers["admin"]).get_json()["dados"]) == 3


def test_senha_nunca_aparece_nas_respostas(client, headers):
    for corpo in (client.get("/usuarios", headers=headers["admin"]).get_json(),
                  client.get("/usuarios/2", headers=headers["joao"]).get_json()):
        assert "senha" not in str(corpo) and "senha_hash" not in str(corpo)


def test_login_nao_aceita_injecao_sql(client):
    resposta = client.post("/login", json={"email": "admin@loja.com' --", "senha": "x"})
    assert resposta.status_code == 401


def test_busca_nao_aceita_union(client):
    termo = "' UNION SELECT id,nome,email,senha_hash,tipo,0,0,criado_em FROM usuarios --"
    assert client.get("/produtos/busca", query_string={"q": termo}).get_json()["dados"] == []


def test_cadastro_publico_nao_cria_admin(client):
    client.post("/usuarios", json={"nome": "Eve", "email": "eve@x.com", "senha": "segredo1", "tipo": "admin"})
    login = client.post("/login", json={"email": "eve@x.com", "senha": "segredo1"}).get_json()
    assert login["dados"]["tipo"] == "cliente"


# --- conta privilegiada sem senha conhecida em produção ------------------------

def test_producao_exige_credenciais_de_admin_do_ambiente():
    with pytest.raises(ConfigError):
        Settings({"APP_ENV": "production", "SECRET_KEY": "x"})
    with pytest.raises(ConfigError):
        Settings({"APP_ENV": "development"})  # sem SECRET_KEY


def test_producao_nao_cria_contas_com_senha_conhecida(make_app):
    app = make_app(APP_ENV="production", ADMIN_EMAIL="ops@loja.com", ADMIN_PASSWORD="S3nh@-forte-do-ambiente")
    client = app.test_client()
    for email, senha in (("admin@loja.com", "admin123"), ("joao@email.com", "123456"), ("maria@email.com", "senha123")):
        assert client.post("/login", json={"email": email, "senha": senha}).status_code == 401
    assert client.post("/login", json={"email": "ops@loja.com", "senha": "S3nh@-forte-do-ambiente"}).status_code == 200
    assert client.get("/produtos").get_json()["dados"] == []  # sem dados de demonstração


def test_reset_db_desabilitado_por_padrao(make_app):
    client = make_app().test_client()  # ENABLE_RESET_DB ausente
    token = client.post("/login", json={"email": "admin@loja.com", "senha": "admin123"}).get_json()["token"]
    resposta = client.post("/admin/reset-db", headers={"Authorization": "Bearer " + token})
    assert resposta.status_code == 403


# --- regras de negócio ---------------------------------------------------------

def _estoque(client, produto_id):
    return client.get(f"/produtos/{produto_id}").get_json()["dados"]["estoque"]


def test_cancelamento_devolve_estoque(client, headers):
    antes = _estoque(client, 2)
    pedido = client.post("/pedidos", json={"itens": [{"produto_id": 2, "quantidade": 2}]}, headers=headers["joao"])
    assert pedido.status_code == 201 and pedido.get_json()["dados"]["total"] == pytest.approx(179.8)
    assert _estoque(client, 2) == antes - 2

    pedido_id = pedido.get_json()["dados"]["pedido_id"]
    assert client.put(f"/pedidos/{pedido_id}/status", json={"status": "cancelado"},
                      headers=headers["admin"]).status_code == 200
    assert _estoque(client, 2) == antes
    # cancelar de novo não devolve em dobro; sair de cancelado é conflito
    client.put(f"/pedidos/{pedido_id}/status", json={"status": "cancelado"}, headers=headers["admin"])
    assert _estoque(client, 2) == antes
    assert client.put(f"/pedidos/{pedido_id}/status", json={"status": "aprovado"},
                      headers=headers["admin"]).status_code == 409


def test_quantidade_invalida_e_itens_repetidos(client, headers):
    estoque = _estoque(client, 6)
    negativa = client.post("/pedidos", json={"itens": [{"produto_id": 6, "quantidade": -5}]}, headers=headers["joao"])
    assert negativa.status_code == 400
    repetidos = {"itens": [{"produto_id": 6, "quantidade": estoque}, {"produto_id": 6, "quantidade": 1}]}
    assert client.post("/pedidos", json=repetidos, headers=headers["joao"]).status_code == 400
    assert _estoque(client, 6) == estoque  # rollback: nada foi baixado


def test_status_de_pedido_inexistente_retorna_404(client, headers):
    assert client.put("/pedidos/999/status", json={"status": "aprovado"}, headers=headers["admin"]).status_code == 404


def test_produto_com_pedidos_nao_pode_ser_removido(client, headers):
    client.post("/pedidos", json=PEDIDO_JOAO, headers=headers["joao"])
    assert client.delete("/produtos/2", headers=headers["admin"]).status_code == 409


def test_crud_de_produto_como_admin(client, headers):
    criado = client.post("/produtos", json=PRODUTO, headers=headers["admin"])
    assert criado.status_code == 201
    produto_id = criado.get_json()["dados"]["id"]
    assert client.put(f"/produtos/{produto_id}", json={**PRODUTO, "nome": "Caneca 2"},
                      headers=headers["admin"]).status_code == 200
    assert client.delete(f"/produtos/{produto_id}", headers=headers["admin"]).status_code == 200


def test_validacao_retorna_400_e_nao_500(client, headers):
    assert client.post("/produtos", json={**PRODUTO, "preco": "abc"}, headers=headers["admin"]).status_code == 400
    assert client.put("/produtos/1", json={**PRODUTO, "categoria": "x"}, headers=headers["admin"]).status_code == 400
    assert client.post("/login", data="nao-json").status_code == 400
    assert client.get("/produtos/busca?preco_min=abc").status_code == 400
    assert client.post("/usuarios", json={"nome": "J", "email": "joao@email.com", "senha": "abcdef"}).status_code == 409


def test_relatorio_de_vendas(client, headers):
    client.post("/pedidos", json={"itens": [{"produto_id": 1, "quantidade": 1}]}, headers=headers["joao"])
    dados = client.get("/relatorios/vendas", headers=headers["admin"]).get_json()["dados"]
    assert dados["total_pedidos"] == 1
    assert dados["desconto_aplicavel"] == pytest.approx(5999.99 * 0.05, abs=0.01)
