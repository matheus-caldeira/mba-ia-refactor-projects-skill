from flask import Blueprint, g

from middlewares.auth import require_admin, require_auth
from routes._http import corpo_json, deps, ok

pedido_bp = Blueprint("pedidos", __name__)


@pedido_bp.post("/pedidos")
@require_auth
def criar_pedido():
    resultado = deps().pedido_controller.criar(corpo_json(), g.ator)
    return ok(resultado, 201, mensagem="Pedido criado com sucesso")


@pedido_bp.get("/pedidos")
@require_auth
def listar_todos_pedidos():
    return ok(deps().pedido_controller.listar(g.ator))


@pedido_bp.get("/pedidos/usuario/<int:usuario_id>")
@require_auth
def listar_pedidos_usuario(usuario_id):
    return ok(deps().pedido_controller.listar_do_usuario(usuario_id, g.ator))


@pedido_bp.put("/pedidos/<int:pedido_id>/status")
@require_admin
def atualizar_status_pedido(pedido_id):
    deps().pedido_controller.atualizar_status(pedido_id, corpo_json())
    return ok(mensagem="Status atualizado")


@pedido_bp.get("/relatorios/vendas")
@require_admin
def relatorio_vendas():
    return ok(deps().relatorio_service.vendas())
