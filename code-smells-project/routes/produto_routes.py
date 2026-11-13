from flask import Blueprint, request

from middlewares.auth import require_admin
from routes._http import corpo_json, deps, ok

produto_bp = Blueprint("produtos", __name__)


@produto_bp.get("/produtos")
def listar_produtos():
    return ok(deps().produto_controller.listar())


@produto_bp.get("/produtos/busca")
def buscar_produtos():
    resultados = deps().produto_controller.buscar(
        request.args.get("q", ""),
        request.args.get("categoria"),
        request.args.get("preco_min"),
        request.args.get("preco_max"),
    )
    return ok(resultados, total=len(resultados))


@produto_bp.get("/produtos/<int:produto_id>")
def buscar_produto(produto_id):
    return ok(deps().produto_controller.buscar_por_id(produto_id))


@produto_bp.post("/produtos")
@require_admin
def criar_produto():
    produto_id = deps().produto_controller.criar(corpo_json())
    return ok({"id": produto_id}, 201, mensagem="Produto criado")


@produto_bp.put("/produtos/<int:produto_id>")
@require_admin
def atualizar_produto(produto_id):
    deps().produto_controller.atualizar(produto_id, corpo_json())
    return ok(mensagem="Produto atualizado")


@produto_bp.delete("/produtos/<int:produto_id>")
@require_admin
def deletar_produto(produto_id):
    deps().produto_controller.remover(produto_id)
    return ok(mensagem="Produto deletado")
