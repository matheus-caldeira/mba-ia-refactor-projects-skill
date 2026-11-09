"""Tratamento de erro centralizado: um único ponto converte exceção em HTTP."""

from flask import jsonify
from werkzeug.exceptions import HTTPException

from .errors import AppError


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def _app_error(err):
        corpo = {"erro": err.message, "sucesso": False}
        corpo.update(err.payload)
        return jsonify(corpo), err.status_code

    @app.errorhandler(HTTPException)
    def _http_error(err):
        return jsonify({"erro": err.description, "sucesso": False}), err.code

    @app.errorhandler(Exception)
    def _unexpected(err):
        # Stack trace fica no servidor; o cliente recebe mensagem genérica.
        app.logger.exception("Erro não tratado")
        return jsonify({"erro": "Erro interno", "sucesso": False}), 500
