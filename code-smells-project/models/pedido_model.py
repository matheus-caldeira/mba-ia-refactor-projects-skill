"""Entidade Pedido: persistência transacional e leitura sem N+1."""

from enum import Enum

from .database import get_db


class StatusPedido(str, Enum):
    PENDENTE = "pendente"
    APROVADO = "aprovado"
    ENVIADO = "enviado"
    ENTREGUE = "entregue"
    CANCELADO = "cancelado"

    @classmethod
    def valores(cls):
        return [status.value for status in cls]


def _montar_pedidos(rows_pedidos, rows_itens):
    """Agrupa itens por pedido em memória — uma query para cada tabela."""
    itens_por_pedido = {}
    for item in rows_itens:
        itens_por_pedido.setdefault(item["pedido_id"], []).append(
            {
                "produto_id": item["produto_id"],
                "produto_nome": item["produto_nome"] or "Desconhecido",
                "quantidade": item["quantidade"],
                "preco_unitario": item["preco_unitario"],
            }
        )

    return [
        {
            "id": row["id"],
            "usuario_id": row["usuario_id"],
            "status": row["status"],
            "total": row["total"],
            "criado_em": row["criado_em"],
            "itens": itens_por_pedido.get(row["id"], []),
        }
        for row in rows_pedidos
    ]


SQL_ITENS = (
    "SELECT i.pedido_id, i.produto_id, i.quantidade, i.preco_unitario, "
    "p.nome AS produto_nome "
    "FROM itens_pedido i LEFT JOIN produtos p ON p.id = i.produto_id"
)


def listar_todos():
    db = get_db()
    pedidos = db.execute("SELECT * FROM pedidos").fetchall()
    itens = db.execute(SQL_ITENS).fetchall()
    return _montar_pedidos(pedidos, itens)


def listar_por_usuario(usuario_id):
    db = get_db()
    pedidos = db.execute(
        "SELECT * FROM pedidos WHERE usuario_id = ?", (usuario_id,)
    ).fetchall()
    itens = db.execute(
        SQL_ITENS + " WHERE i.pedido_id IN (SELECT id FROM pedidos WHERE usuario_id = ?)",
        (usuario_id,),
    ).fetchall()
    return _montar_pedidos(pedidos, itens)


def buscar_por_id(pedido_id):
    row = get_db().execute(
        "SELECT * FROM pedidos WHERE id = ?", (pedido_id,)
    ).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "usuario_id": row["usuario_id"],
        "status": row["status"],
        "total": row["total"],
        "criado_em": row["criado_em"],
    }


def buscar_itens(pedido_id):
    rows = get_db().execute(
        "SELECT produto_id, quantidade FROM itens_pedido WHERE pedido_id = ?",
        (pedido_id,),
    ).fetchall()
    return [{"produto_id": r["produto_id"], "quantidade": r["quantidade"]} for r in rows]


def criar(usuario_id, linhas, total):
    """Insere pedido, itens e baixa de estoque em uma transação única (P-07)."""
    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
            (usuario_id, StatusPedido.PENDENTE.value, total),
        )
        pedido_id = cursor.lastrowid

        for linha in linhas:
            db.execute(
                "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, "
                "preco_unitario) VALUES (?, ?, ?, ?)",
                (pedido_id, linha["produto_id"], linha["quantidade"], linha["preco"]),
            )
            db.execute(
                "UPDATE produtos SET estoque = estoque - ? WHERE id = ?",
                (linha["quantidade"], linha["produto_id"]),
            )
        db.commit()
        return pedido_id
    except Exception:
        db.rollback()
        raise


def atualizar_status(pedido_id, novo_status, devolver_estoque=False):
    """Atualiza status e, no cancelamento, repõe o estoque de fato."""
    db = get_db()
    try:
        if devolver_estoque:
            itens = db.execute(
                "SELECT produto_id, quantidade FROM itens_pedido WHERE pedido_id = ?",
                (pedido_id,),
            ).fetchall()
            for item in itens:
                db.execute(
                    "UPDATE produtos SET estoque = estoque + ? WHERE id = ?",
                    (item["quantidade"], item["produto_id"]),
                )

        db.execute(
            "UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id)
        )
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise


def relatorio_vendas():
    db = get_db()
    total_pedidos = db.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
    faturamento = db.execute("SELECT SUM(total) FROM pedidos").fetchone()[0] or 0

    contagens = dict(
        db.execute("SELECT status, COUNT(*) FROM pedidos GROUP BY status").fetchall()
    )
    return {
        "total_pedidos": total_pedidos,
        "faturamento": faturamento,
        "pendentes": contagens.get(StatusPedido.PENDENTE.value, 0),
        "aprovados": contagens.get(StatusPedido.APROVADO.value, 0),
        "cancelados": contagens.get(StatusPedido.CANCELADO.value, 0),
    }
