"""Entidade Produto: persistência parametrizada e serialização explícita."""

from .database import get_db

CATEGORIAS_VALIDAS = (
    "informatica",
    "moveis",
    "vestuario",
    "geral",
    "eletronicos",
    "livros",
)

# Lista de permissão: campo novo na tabela só aparece na API se entrar aqui.
CAMPOS_PUBLICOS = (
    "id",
    "nome",
    "descricao",
    "preco",
    "estoque",
    "categoria",
    "ativo",
    "criado_em",
)


def serializar(row):
    if row is None:
        return None
    return {campo: row[campo] for campo in CAMPOS_PUBLICOS}


def listar_todos():
    rows = get_db().execute("SELECT * FROM produtos").fetchall()
    return [serializar(row) for row in rows]


def buscar_por_id(produto_id):
    row = get_db().execute(
        "SELECT * FROM produtos WHERE id = ?", (produto_id,)
    ).fetchone()
    return serializar(row)


def criar(nome, descricao, preco, estoque, categoria):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) "
        "VALUES (?, ?, ?, ?, ?)",
        (nome, descricao, preco, estoque, categoria),
    )
    db.commit()
    return cursor.lastrowid


def atualizar(produto_id, nome, descricao, preco, estoque, categoria):
    db = get_db()
    db.execute(
        "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, "
        "categoria = ? WHERE id = ?",
        (nome, descricao, preco, estoque, categoria, produto_id),
    )
    db.commit()
    return True


def deletar(produto_id):
    db = get_db()
    db.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
    db.commit()
    return True


def buscar(termo=None, categoria=None, preco_min=None, preco_max=None):
    """Filtro dinâmico com placeholders — os valores nunca entram no SQL (P-01)."""
    sql = "SELECT * FROM produtos WHERE 1=1"
    params = []

    if termo:
        sql += " AND (nome LIKE ? OR descricao LIKE ?)"
        curinga = f"%{termo}%"
        params.extend([curinga, curinga])
    if categoria:
        sql += " AND categoria = ?"
        params.append(categoria)
    if preco_min is not None:
        sql += " AND preco >= ?"
        params.append(preco_min)
    if preco_max is not None:
        sql += " AND preco <= ?"
        params.append(preco_max)

    rows = get_db().execute(sql, params).fetchall()
    return [serializar(row) for row in rows]
