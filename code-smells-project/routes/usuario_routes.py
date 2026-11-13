from flask import Blueprint, g

from middlewares.auth import require_auth
from routes._http import corpo_json, deps, ok

usuario_bp = Blueprint("usuarios", __name__)


@usuario_bp.get("/usuarios")
@require_auth
def listar_usuarios():
    return ok(deps().usuario_controller.listar(g.ator))


@usuario_bp.get("/usuarios/<int:usuario_id>")
@require_auth
def buscar_usuario(usuario_id):
    return ok(deps().usuario_controller.buscar_por_id(usuario_id, g.ator))


@usuario_bp.post("/usuarios")
def criar_usuario():
    usuario_id = deps().usuario_controller.criar(corpo_json())
    return ok({"id": usuario_id}, 201)


@usuario_bp.post("/login")
def login():
    usuario, token = deps().usuario_controller.login(corpo_json())
    return ok(usuario, mensagem="Login OK", token=token)
