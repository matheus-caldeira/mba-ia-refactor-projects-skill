from flask import Blueprint, g, jsonify

from middlewares.auth import require_admin
from routes._http import deps, ok

sistema_bp = Blueprint("sistema", __name__)


@sistema_bp.get("/")
def index():
    return jsonify({
        "mensagem": "Bem-vindo à API da Loja",
        "versao": deps().settings.APP_VERSION,
        "endpoints": {
            "produtos": "/produtos",
            "usuarios": "/usuarios",
            "pedidos": "/pedidos",
            "login": "/login",
            "relatorios": "/relatorios/vendas",
            "health": "/health",
        },
    })


@sistema_bp.get("/health")
def health_check():
    return jsonify(deps().sistema_controller.health()), 200


@sistema_bp.post("/admin/reset-db")
@require_admin
def reset_database():
    deps().sistema_controller.reset_db(g.ator)
    return ok(mensagem="Banco de dados resetado")
