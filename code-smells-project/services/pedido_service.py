"""Fluxo de negócio de pedidos — cruza Produto e Pedido, logo é serviço."""

from middlewares.errors import NotFoundError, ValidationError
from models import pedido_model, produto_model
from models.pedido_model import StatusPedido


class PedidoService:
    def __init__(self, notificador):
        self._notificador = notificador

    def criar(self, usuario_id, itens):
        linhas = []
        total = 0.0

        for item in itens:
            produto_id = item.get("produto_id")
            quantidade = item.get("quantidade")

            if produto_id is None or quantidade is None:
                raise ValidationError("Item deve conter produto_id e quantidade")
            if not isinstance(quantidade, int) or quantidade <= 0:
                raise ValidationError("Quantidade deve ser um inteiro positivo")

            produto = produto_model.buscar_por_id(produto_id)
            if produto is None:
                raise ValidationError(f"Produto {produto_id} não encontrado")
            if produto["estoque"] < quantidade:
                raise ValidationError(f"Estoque insuficiente para {produto['nome']}")

            total += produto["preco"] * quantidade
            linhas.append(
                {
                    "produto_id": produto_id,
                    "quantidade": quantidade,
                    "preco": produto["preco"],
                }
            )

        pedido_id = pedido_model.criar(usuario_id, linhas, total)
        self._notificador.pedido_criado(pedido_id, usuario_id)
        return {"pedido_id": pedido_id, "total": total}

    def listar_todos(self):
        return pedido_model.listar_todos()

    def listar_por_usuario(self, usuario_id):
        return pedido_model.listar_por_usuario(usuario_id)

    def alterar_status(self, pedido_id, novo_status):
        if novo_status not in StatusPedido.valores():
            raise ValidationError("Status inválido")

        pedido = pedido_model.buscar_por_id(pedido_id)
        if pedido is None:
            raise NotFoundError("Pedido não encontrado")

        # A regra que o código original só anunciava num print agora acontece.
        deve_devolver = (
            novo_status == StatusPedido.CANCELADO.value
            and pedido["status"] != StatusPedido.CANCELADO.value
        )
        pedido_model.atualizar_status(pedido_id, novo_status, devolver_estoque=deve_devolver)

        if novo_status == StatusPedido.APROVADO.value:
            self._notificador.pedido_aprovado(pedido_id)
        if deve_devolver:
            self._notificador.pedido_cancelado(pedido_id)

        return True


class RelatorioService:
    """Regras de desconto do relatório de vendas, fora do model e da rota."""

    FAIXAS_DESCONTO = ((10000, 0.10), (5000, 0.05), (1000, 0.02))

    def vendas(self):
        dados = pedido_model.relatorio_vendas()
        faturamento = dados["faturamento"]
        total_pedidos = dados["total_pedidos"]

        desconto = 0.0
        for limite, percentual in self.FAIXAS_DESCONTO:
            if faturamento > limite:
                desconto = faturamento * percentual
                break

        return {
            "total_pedidos": total_pedidos,
            "faturamento_bruto": round(faturamento, 2),
            "desconto_aplicavel": round(desconto, 2),
            "faturamento_liquido": round(faturamento - desconto, 2),
            "pedidos_pendentes": dados["pendentes"],
            "pedidos_aprovados": dados["aprovados"],
            "pedidos_cancelados": dados["cancelados"],
            "ticket_medio": round(faturamento / total_pedidos, 2) if total_pedidos else 0,
        }
