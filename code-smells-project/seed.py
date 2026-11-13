"""Dados iniciais. Admin vem da config; produtos e clientes de exemplo só fora de produção."""
import logging

from database import transaction
from models.produto_model import ProdutoModel
from models.usuario_model import TIPO_ADMIN, TIPO_CLIENTE, UsuarioModel

logger = logging.getLogger(__name__)

PRODUTOS_DEMO = [
    ("Notebook Gamer", "Notebook potente para jogos", 5999.99, 10, "informatica"),
    ("Mouse Wireless", "Mouse sem fio ergonômico", 89.90, 50, "informatica"),
    ("Teclado Mecânico", "Teclado mecânico RGB", 299.90, 30, "informatica"),
    ("Monitor 27''", "Monitor 27 polegadas 144hz", 1899.90, 15, "informatica"),
    ("Headset Gamer", "Headset com microfone", 199.90, 25, "informatica"),
    ("Cadeira Gamer", "Cadeira ergonômica", 1299.90, 8, "moveis"),
    ("Webcam HD", "Webcam 1080p", 249.90, 20, "informatica"),
    ("Hub USB", "Hub USB 3.0 7 portas", 79.90, 40, "informatica"),
    ("SSD 1TB", "SSD NVMe 1TB", 449.90, 35, "informatica"),
    ("Camiseta Dev", "Camiseta estampa código", 59.90, 100, "vestuario"),
]

# Somente desenvolvimento: senhas conhecidas, nunca criadas com APP_ENV=production.
CLIENTES_DEMO = [
    ("João Silva", "joao@email.com", "123456"),
    ("Maria Santos", "maria@email.com", "senha123"),
]


def seed(conn, settings):
    get_conn = lambda: conn  # noqa: E731 — o seed roda fora de requisição, com conexão própria
    produtos, usuarios = ProdutoModel(get_conn), UsuarioModel(get_conn)

    with transaction(conn):
        if settings.ADMIN_EMAIL and usuarios.buscar_por_email(settings.ADMIN_EMAIL.lower()) is None:
            usuarios.criar("Admin", settings.ADMIN_EMAIL.lower(), settings.ADMIN_PASSWORD, TIPO_ADMIN)
            logger.info("Conta administradora criada a partir da configuração")

        if not settings.SEED_DEMO_DATA:
            return
        if produtos.contar() == 0:
            for nome, descricao, preco, estoque, categoria in PRODUTOS_DEMO:
                produtos.criar({"nome": nome, "descricao": descricao, "preco": preco,
                                "estoque": estoque, "categoria": categoria})
        for nome, email, senha in CLIENTES_DEMO:
            if usuarios.buscar_por_email(email) is None:
                usuarios.criar(nome, email, senha, TIPO_CLIENTE)
        logger.info("Dados de demonstração garantidos (APP_ENV=%s)", settings.APP_ENV)
