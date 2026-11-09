"""Tratamento de erro centralizado: um único ponto converte exceção em resposta."""

import logging

from flask import jsonify
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

from database import db
from errors import AppError

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        payload = {'error': err.message}
        if err.details:
            payload['details'] = err.details
        return jsonify(payload), err.status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(err):
        # Mantém 404/405 do roteador do Flask em JSON, como o resto da API.
        return jsonify({'error': err.description}), err.code

    @app.errorhandler(SQLAlchemyError)
    def handle_db_error(err):
        db.session.rollback()
        logger.exception('Erro de banco de dados')
        return jsonify({'error': 'Erro interno'}), 500

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        db.session.rollback()
        logger.exception('Erro não tratado')
        return jsonify({'error': 'Erro interno'}), 500
