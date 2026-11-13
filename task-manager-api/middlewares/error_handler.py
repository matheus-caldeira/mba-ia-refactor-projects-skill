"""Ponto único que converte exceção em resposta HTTP: {"error": "<mensagem>"}."""
import logging

from flask import jsonify
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from database import db
from errors import AppError

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        db.session.rollback()
        return jsonify({"error": err.message}), err.status_code

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(err):
        db.session.rollback()
        logger.warning("Violação de integridade: %s", err.orig)
        return jsonify({"error": "Conflito com dados existentes"}), 409

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        return jsonify({"error": err.description or err.name}), err.code

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        db.session.rollback()
        logger.exception("Erro não tratado")
        return jsonify({"error": "Erro interno"}), 500
