"""Fronteira HTTP dos usuários e do login. Sem regra de negócio."""

from flask import Blueprint, current_app, jsonify, request

from middlewares.auth import current_user, require_role

user_bp = Blueprint('users', __name__)


def _controller():
    return current_app.extensions['user_controller']


@user_bp.route('/users', methods=['GET'])
def get_users():
    return jsonify(_controller().list()), 200


@user_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    return jsonify(_controller().get(user_id)), 200


@user_bp.route('/users', methods=['POST'])
def create_user():
    data = request.get_json(silent=True)
    return jsonify(_controller().create(data, actor=current_user())), 201


@user_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    data = request.get_json(silent=True)
    return jsonify(_controller().update(user_id, data, actor=current_user())), 200


@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
@require_role('admin')
def delete_user(user_id):
    return jsonify(_controller().delete(user_id)), 200


@user_bp.route('/users/<int:user_id>/tasks', methods=['GET'])
def get_user_tasks(user_id):
    return jsonify(_controller().list_tasks(user_id)), 200


@user_bp.route('/login', methods=['POST'])
def login():
    return jsonify(_controller().login(request.get_json(silent=True))), 200
