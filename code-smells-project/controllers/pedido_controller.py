"""Orquestra os casos de uso de Pedido, delegando a regra ao serviço."""

from middlewares.errors import ValidationError


class PedidoController:
    def __init__(self, service):
        self._service = service

    def criar(self, dados):
        if not dados:
            raise ValidationError("Dados inválidos")

        usuario_id = dados.get("usuario_id")
        itens = dados.get("itens") or []

        if not usuario_id:
            raise ValidationError("Usuario ID é obrigatório")
        if not itens:
            raise ValidationError("Pedido deve ter pelo menos 1 item")

        return self._service.criar(usuario_id, itens)

    def listar_todos(self):
        return self._service.listar_todos()

    def listar_por_usuario(self, usuario_id):
        return self._service.listar_por_usuario(usuario_id)

    def alterar_status(self, pedido_id, dados):
        novo_status = (dados or {}).get("status", "")
        return self._service.alterar_status(pedido_id, novo_status)


class RelatorioController:
    def __init__(self, service):
        self._service = service

    def vendas(self):
        return self._service.vendas()
