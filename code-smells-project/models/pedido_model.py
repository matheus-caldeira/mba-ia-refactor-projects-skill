"""Pedido e itens: acesso parametrizado a `pedidos` e `itens_pedido`, sem N+1."""
from enum import Enum

PRODUTO_DESCONHECIDO = "Desconhecido"
CAMPOS_PEDIDO = ("id", "usuario_id", "status", "total", "criado_em")


class StatusPedido(str, Enum):
    PENDENTE = "pendente"
    APROVADO = "aprovado"
    ENVIADO = "enviado"
    ENTREGUE = "entregue"
    CANCELADO = "cancelado"

    @classmethod
    def valores(cls):
        return [s.value for s in cls]


class PedidoModel:
    def __init__(self, get_conn):
        self._conn = get_conn

    def listar(self, usuario_id=None):
        """Pedidos com itens em duas consultas, independente do número de pedidos."""
        sql = "SELECT " + ", ".join(CAMPOS_PEDIDO) + " FROM pedidos"
        params = ()
        if usuario_id is not None:
            sql += " WHERE usuario_id = ?"
            params = (usuario_id,)
        pedidos = [dict(row) for row in self._conn().execute(sql + " ORDER BY id", params).fetchall()]
        itens = self._itens_por_pedido([p["id"] for p in pedidos])
        for pedido in pedidos:
            pedido["itens"] = itens.get(pedido["id"], [])
        return pedidos

    def _itens_por_pedido(self, pedido_ids):
        if not pedido_ids:
            return {}
        placeholders = ", ".join("?" for _ in pedido_ids)
        rows = self._conn().execute(
            f"""SELECT i.pedido_id, i.produto_id, i.quantidade, i.preco_unitario, p.nome AS produto_nome
                FROM itens_pedido i LEFT JOIN produtos p ON p.id = i.produto_id
                WHERE i.pedido_id IN ({placeholders}) ORDER BY i.id""",
            pedido_ids,
        ).fetchall()
        agrupado = {}
        for row in rows:
            agrupado.setdefault(row["pedido_id"], []).append({
                "produto_id": row["produto_id"],
                "produto_nome": row["produto_nome"] or PRODUTO_DESCONHECIDO,
                "quantidade": row["quantidade"],
                "preco_unitario": row["preco_unitario"],
            })
        return agrupado

    def buscar_por_id(self, pedido_id):
        row = self._conn().execute(
            "SELECT " + ", ".join(CAMPOS_PEDIDO) + " FROM pedidos WHERE id = ?", (pedido_id,)
        ).fetchone()
        return dict(row) if row else None

    def itens(self, pedido_id):
        rows = self._conn().execute(
            "SELECT produto_id, quantidade FROM itens_pedido WHERE pedido_id = ?", (pedido_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def criar(self, usuario_id, total, itens):
        """itens: [{produto_id, quantidade, preco_unitario}]. Chamar dentro de transação."""
        conn = self._conn()
        cursor = conn.execute(
            "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
            (usuario_id, StatusPedido.PENDENTE.value, total),
        )
        pedido_id = cursor.lastrowid
        conn.executemany(
            "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
            [(pedido_id, i["produto_id"], i["quantidade"], i["preco_unitario"]) for i in itens],
        )
        return pedido_id

    def atualizar_status(self, pedido_id, status):
        self._conn().execute("UPDATE pedidos SET status = ? WHERE id = ?", (status, pedido_id))

    def contar(self):
        return self._conn().execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]

    def resumo_vendas(self):
        """Agregados do relatório numa única consulta."""
        row = self._conn().execute(
            """SELECT COUNT(*) AS total_pedidos,
                      COALESCE(SUM(total), 0) AS faturamento,
                      COALESCE(SUM(CASE WHEN status = ? THEN 1 ELSE 0 END), 0) AS pendentes,
                      COALESCE(SUM(CASE WHEN status = ? THEN 1 ELSE 0 END), 0) AS aprovados,
                      COALESCE(SUM(CASE WHEN status = ? THEN 1 ELSE 0 END), 0) AS cancelados
               FROM pedidos""",
            (StatusPedido.PENDENTE.value, StatusPedido.APROVADO.value, StatusPedido.CANCELADO.value),
        ).fetchone()
        return dict(row)
