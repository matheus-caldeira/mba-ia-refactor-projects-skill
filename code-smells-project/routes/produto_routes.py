"""Fronteira HTTP de Produto: mapeia, extrai parâmetros, devolve resposta."""

from flask import Blueprint, jsonify, request

from controllers import produto_controller
from middlewares.auth import require_admin

produto_bp = Blueprint("produtos", __name__)


@produto_bp.get("/produtos")
def listar_produtos():
    return jsonify({"dados": produto_controller.listar(), "sucesso": True}), 200


@produto_bp.get("/produtos/busca")
def buscar_produtos():
    resultados = produto_controller.pesquisar(
        termo=request.args.get("q", ""),
        categoria=request.args.get("categoria"),
        preco_min=request.args.get("preco_min"),
        preco_max=request.args.get("preco_max"),
    )
    return (
        jsonify({"dados": resultados, "total": len(resultados), "sucesso": True}),
        200,
    )


@produto_bp.get("/produtos/<int:id>")
def buscar_produto(id):
    return jsonify({"dados": produto_controller.buscar(id), "sucesso": True}), 200


@produto_bp.post("/produtos")
@require_admin
def criar_produto():
    produto_id = produto_controller.criar(request.get_json(silent=True))
    return (
        jsonify(
            {"dados": {"id": produto_id}, "sucesso": True, "mensagem": "Produto criado"}
        ),
        201,
    )


@produto_bp.put("/produtos/<int:id>")
@require_admin
def atualizar_produto(id):
    produto_controller.atualizar(id, request.get_json(silent=True))
    return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200


@produto_bp.delete("/produtos/<int:id>")
@require_admin
def deletar_produto(id):
    produto_controller.deletar(id)
    return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200
