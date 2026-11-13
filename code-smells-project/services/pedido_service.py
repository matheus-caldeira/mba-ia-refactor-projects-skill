"""Fluxos de pedido que cruzam entidades: checkout e mudança de status com estoque."""
import logging

from database import transaction
from errors import ConflictError, NotFoundError, ValidationError
from models.pedido_model import StatusPedido

logger = logging.getLogger(__name__)


def _normalizar_itens(itens):
    """Valida os itens e soma quantidades repetidas do mesmo produto."""
    if not isinstance(itens, list) or len(itens) == 0:
        raise ValidationError("Pedido deve ter pelo menos 1 item")
    quantidades = {}
    for item in itens:
        if not isinstance(item, dict):
            raise ValidationError("Item de pedido inválido")
        produto_id, quantidade = item.get("produto_id"), item.get("quantidade")
        if not isinstance(produto_id, int) or isinstance(produto_id, bool):
            raise ValidationError("produto_id deve ser um número inteiro")
        if not isinstance(quantidade, int) or isinstance(quantidade, bool) or quantidade <= 0:
            raise ValidationError("Quantidade deve ser um inteiro maior que zero")
        quantidades[produto_id] = quantidades.get(produto_id, 0) + quantidade
    return quantidades


class PedidoService:
    def __init__(self, get_conn, pedidos, produtos, usuarios, notificador):
        self._conn = get_conn
        self._pedidos = pedidos
        self._produtos = produtos
        self._usuarios = usuarios
        self._notificador = notificador

    def criar(self, usuario_id, itens):
        quantidades = _normalizar_itens(itens)

        with transaction(self._conn()):
            if self._usuarios.buscar_por_id(usuario_id) is None:
                raise ValidationError("Usuário " + str(usuario_id) + " não encontrado")

            produtos = self._produtos.buscar_por_ids(quantidades.keys())
            itens_pedido, total = [], 0
            for produto_id, quantidade in quantidades.items():
                produto = produtos.get(produto_id)
                if produto is None:
                    raise ValidationError("Produto " + str(produto_id) + " não encontrado")
                # Baixa condicional: duas compras simultâneas não passam juntas pela checagem.
                if not self._produtos.baixar_estoque(produto_id, quantidade):
                    raise ValidationError("Estoque insuficiente para " + produto["nome"])
                itens_pedido.append({"produto_id": produto_id, "quantidade": quantidade,
                                     "preco_unitario": produto["preco"]})
                total += produto["preco"] * quantidade

            pedido_id = self._pedidos.criar(usuario_id, total, itens_pedido)

        self._notificador.pedido_criado(pedido_id, usuario_id)
        return {"pedido_id": pedido_id, "total": total}

    def alterar_status(self, pedido_id, novo_status):
        if novo_status not in StatusPedido.valores():
            raise ValidationError("Status inválido")

        with transaction(self._conn()):
            pedido = self._pedidos.buscar_por_id(pedido_id)
            if pedido is None:
                raise NotFoundError("Pedido não encontrado")
            status_atual = pedido["status"]
            if status_atual == StatusPedido.CANCELADO.value and novo_status != status_atual:
                raise ConflictError("Pedido cancelado não pode mudar de status")

            if novo_status == StatusPedido.CANCELADO.value and status_atual != novo_status:
                for item in self._pedidos.itens(pedido_id):
                    self._produtos.devolver_estoque(item["produto_id"], item["quantidade"])
            self._pedidos.atualizar_status(pedido_id, novo_status)

        self._notificador.status_alterado(pedido_id, novo_status)
