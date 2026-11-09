"""Conexão com escopo de requisição, schema e seed.

Substitui o singleton global de `database.py` (AP-07). A conexão vive no `g` do
Flask e é fechada no teardown de cada requisição — sem `check_same_thread=False`,
sem estado de módulo compartilhado entre threads.
"""

import sqlite3

from flask import g
from werkzeug.security import generate_password_hash

from config import settings
from config.runtime import config_atual

SCHEMA = """
CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    descricao TEXT,
    preco REAL NOT NULL,
    estoque INTEGER NOT NULL DEFAULT 0,
    categoria TEXT,
    ativo INTEGER DEFAULT 1,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha TEXT NOT NULL,
    tipo TEXT DEFAULT 'cliente',
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pedidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    status TEXT DEFAULT 'pendente',
    total REAL NOT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
);

CREATE TABLE IF NOT EXISTS itens_pedido (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id INTEGER NOT NULL,
    produto_id INTEGER NOT NULL,
    quantidade INTEGER NOT NULL,
    preco_unitario REAL NOT NULL,
    FOREIGN KEY (pedido_id) REFERENCES pedidos (id) ON DELETE CASCADE,
    FOREIGN KEY (produto_id) REFERENCES produtos (id)
);
"""

PRODUTOS_SEED = [
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

CLIENTES_DEMO = [
    ("João Silva", "joao@email.com", "123456", "cliente"),
    ("Maria Santos", "maria@email.com", "senha123", "cliente"),
]


def conectar(caminho=None):
    """Abre uma conexão nova. Usado pelo app e pelos testes."""
    conexao = sqlite3.connect(caminho or config_atual().DATABASE_PATH)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def get_db():
    if "db" not in g:
        g.db = conectar()
    return g.db


def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def inicializar(conexao, config=None):
    """Cria o schema e popula o seed apenas se o banco estiver vazio."""
    config = config or settings
    conexao.executescript(SCHEMA)
    conexao.commit()

    if conexao.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] == 0:
        conexao.executemany(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) "
            "VALUES (?, ?, ?, ?, ?)",
            PRODUTOS_SEED,
        )

    usuarios = [(config.ADMIN_NAME, config.ADMIN_EMAIL, config.ADMIN_PASSWORD, "admin")]
    if config.SEED_DEMO_USERS:
        usuarios += CLIENTES_DEMO
    for nome, email, senha, tipo in usuarios:
        existe = conexao.execute("SELECT 1 FROM usuarios WHERE email = ?", (email,)).fetchone()
        if existe is None:
            conexao.execute(
                "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                (nome, email, generate_password_hash(senha), tipo),
            )

    conexao.commit()


def contar_registros():
    """Contagens públicas usadas pelo health check (sem SQL na rota)."""
    db = get_db()
    return {
        tabela: db.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
        # nomes de tabela vêm desta tupla fixa, nunca da requisição
        for tabela in ("produtos", "usuarios", "pedidos")
    }


def resetar():
    """Apaga os dados de todas as tabelas numa transação única."""
    db = get_db()
    try:
        for tabela in ("itens_pedido", "pedidos", "produtos", "usuarios"):
            db.execute(f"DELETE FROM {tabela}")  # tupla fixa, sem entrada externa
        db.commit()
    except Exception:
        db.rollback()
        raise
