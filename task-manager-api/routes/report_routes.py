"""Fronteira HTTP de relatórios e categorias. Sem regra de negócio.

As rotas de categoria seguem no mesmo blueprint do original para preservar
exatamente os caminhos e métodos existentes.
"""

from flask import Blueprint, current_app, jsonify, request

report_bp = Blueprint('reports', __name__)


def _reports():
    return current_app.extensions['report_controller']


def _categories():
    return current_app.extensions['category_controller']


@report_bp.route('/reports/summary', methods=['GET'])
def summary_report():
    return jsonify(_reports().summary()), 200


@report_bp.route('/reports/user/<int:user_id>', methods=['GET'])
def user_report(user_id):
    return jsonify(_reports().user_report(user_id)), 200


@report_bp.route('/categories', methods=['GET'])
def get_categories():
    return jsonify(_categories().list()), 200


@report_bp.route('/categories', methods=['POST'])
def create_category():
    return jsonify(_categories().create(request.get_json(silent=True))), 201


@report_bp.route('/categories/<int:cat_id>', methods=['PUT'])
def update_category(cat_id):
    return jsonify(_categories().update(cat_id, request.get_json(silent=True))), 200


@report_bp.route('/categories/<int:cat_id>', methods=['DELETE'])
def delete_category(cat_id):
    return jsonify(_categories().delete(cat_id)), 200
