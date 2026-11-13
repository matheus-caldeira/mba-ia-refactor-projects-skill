"""Helpers da fronteira HTTP: acesso às dependências e envelope de resposta."""
from flask import current_app, jsonify, request


def deps():
    return current_app.extensions["loja"]


def corpo_json():
    """Corpo JSON ou None (corpo ausente/malformado vira 400 no controller, não 500)."""
    return request.get_json(silent=True)


def ok(dados=None, status=200, **extras):
    resposta = {"sucesso": True}
    if dados is not None:
        resposta["dados"] = dados
    resposta.update(extras)
    return jsonify(resposta), status
