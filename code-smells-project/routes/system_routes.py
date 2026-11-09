"""Rotas de sistema: índice, health check e administração."""

from flask import Blueprint, jsonify

from controllers import sistema_controller
from middlewares.admin_auth import require_admin

system_bp = Blueprint("system", __name__)


@system_bp.get("/")
def index():
    return jsonify(
        {
            "mensagem": "Bem-vindo à API da Loja",
            "versao": "1.0.0",
            "endpoints": {
                "produtos": "/produtos",
                "usuarios": "/usuarios",
                "pedidos": "/pedidos",
                "login": "/login",
                "relatorios": "/relatorios/vendas",
                "health": "/health",
            },
        }
    )


@system_bp.get("/health")
def health_check():
    return jsonify(sistema_controller.health()), 200


@system_bp.post("/admin/reset-db")
@require_admin
def reset_database():
    sistema_controller.resetar_banco()
    return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200
