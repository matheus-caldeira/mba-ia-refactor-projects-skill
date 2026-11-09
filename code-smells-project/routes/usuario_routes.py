"""Fronteira HTTP de Usuário e login."""

from flask import Blueprint, jsonify, request

from controllers import usuario_controller

usuario_bp = Blueprint("usuarios", __name__)


@usuario_bp.get("/usuarios")
def listar_usuarios():
    return jsonify({"dados": usuario_controller.listar(), "sucesso": True}), 200


@usuario_bp.get("/usuarios/<int:id>")
def buscar_usuario(id):
    return jsonify({"dados": usuario_controller.buscar(id), "sucesso": True}), 200


@usuario_bp.post("/usuarios")
def criar_usuario():
    usuario_id = usuario_controller.criar(request.get_json(silent=True))
    return jsonify({"dados": {"id": usuario_id}, "sucesso": True}), 201


@usuario_bp.post("/login")
def login():
    usuario = usuario_controller.login(request.get_json(silent=True))
    return (
        jsonify({"dados": usuario, "sucesso": True, "mensagem": "Login OK"}),
        200,
    )
