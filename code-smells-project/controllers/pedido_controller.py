from controllers.acesso import escopo_leitura, exigir_dono_ou_admin
from errors import ValidationError


class PedidoController:
    def __init__(self, pedidos, pedido_service):
        self._pedidos = pedidos
        self._service = pedido_service

    def criar(self, dados, ator):
        if not isinstance(dados, dict) or not dados:
            raise ValidationError("Dados inválidos")
        # Dono do pedido é o ator; só admin compra em nome de outro usuário.
        usuario_id = dados.get("usuario_id", ator["id"])
        if not isinstance(usuario_id, int) or isinstance(usuario_id, bool):
            raise ValidationError("Usuario ID é obrigatório")
        exigir_dono_ou_admin(ator, usuario_id)
        return self._service.criar(usuario_id, dados.get("itens"))

    def listar(self, ator):
        return self._pedidos.listar(usuario_id=escopo_leitura(ator))

    def listar_do_usuario(self, usuario_id, ator):
        exigir_dono_ou_admin(ator, usuario_id)
        return self._pedidos.listar(usuario_id=usuario_id)

    def atualizar_status(self, pedido_id, dados):
        novo_status = dados.get("status", "") if isinstance(dados, dict) else ""
        self._service.alterar_status(pedido_id, novo_status)
