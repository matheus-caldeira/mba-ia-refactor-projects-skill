import pytest

from app import create_app
from config.settings import ConfigError, Settings

PRODUCAO = {
    "APP_ENV": "production",
    "SECRET_KEY": "segredo-de-producao",
    "ADMIN_EMAIL": "ops@empresa.com",
    "ADMIN_PASSWORD": "senha-forte-de-producao",
}


@pytest.mark.parametrize("ausente", ["SECRET_KEY", "ADMIN_EMAIL", "ADMIN_PASSWORD"])
def test_producao_sem_credencial_obrigatoria_falha_no_boot(ausente):
    env = {chave: valor for chave, valor in PRODUCAO.items() if chave != ausente}
    with pytest.raises(ConfigError, match=ausente):
        Settings(env)


def test_producao_nao_semeia_contas_com_senha_conhecida(tmp_path):
    config = Settings({**PRODUCAO, "DATABASE_PATH": str(tmp_path / "prod.db")})
    client = create_app(config).test_client()

    for email, senha in (("admin@loja.com", "admin123"), ("joao@email.com", "123456")):
        assert client.post("/login", json={"email": email, "senha": senha}).status_code == 401

    login = client.post("/login", json={"email": "ops@empresa.com", "senha": "senha-forte-de-producao"})
    assert login.status_code == 200
    assert login.get_json()["dados"]["tipo"] == "admin"


def test_reset_db_desligado_por_padrao_mesmo_para_admin(client, admin):
    resposta = client.post("/admin/reset-db", headers=admin)
    assert resposta.status_code == 403


def test_reset_db_com_flag_ligada_e_admin(client, admin, monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "ENABLE_RESET_DB", True)
    assert client.post("/admin/reset-db", headers=admin).status_code == 200


def test_flag_de_reset_e_ignorada_em_producao():
    assert Settings({**PRODUCAO, "ENABLE_RESET_DB": "true"}).ENABLE_RESET_DB is False
