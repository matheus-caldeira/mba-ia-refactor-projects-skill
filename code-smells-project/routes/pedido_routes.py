"""Fronteira HTTP de Pedido e relatórios. Controllers chegam por injeção."""

from flask import Blueprint, jsonify, request


def criar_pedido_bp(pedido_controller, relatorio_controller):
    pedido_bp = Blueprint("pedidos", __name__)

    @pedido_bp.post("/pedidos")
    def criar_pedido():
        resultado = pedido_controller.criar(request.get_json(silent=True))
        return (
            jsonify(
                {
                    "dados": resultado,
                    "sucesso": True,
                    "mensagem": "Pedido criado com sucesso",
                }
            ),
            201,
        )

    @pedido_bp.get("/pedidos")
    def listar_todos_pedidos():
        return jsonify({"dados": pedido_controller.listar_todos(), "sucesso": True}), 200

    @pedido_bp.get("/pedidos/usuario/<int:usuario_id>")
    def listar_pedidos_usuario(usuario_id):
        return (
            jsonify(
                {"dados": pedido_controller.listar_por_usuario(usuario_id), "sucesso": True}
            ),
            200,
        )

    @pedido_bp.put("/pedidos/<int:pedido_id>/status")
    def atualizar_status_pedido(pedido_id):
        pedido_controller.alterar_status(pedido_id, request.get_json(silent=True))
        return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200

    @pedido_bp.get("/relatorios/vendas")
    def relatorio_vendas():
        return jsonify({"dados": relatorio_controller.vendas(), "sucesso": True}), 200

    return pedido_bp
