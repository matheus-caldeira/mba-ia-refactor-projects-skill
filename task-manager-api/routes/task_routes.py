"""Fronteira HTTP das tasks: mapeia rota -> controller. Sem regra de negócio."""

from flask import Blueprint, current_app, jsonify, request

task_bp = Blueprint('tasks', __name__)


def _controller():
    return current_app.extensions['task_controller']


@task_bp.route('/tasks', methods=['GET'])
def get_tasks():
    return jsonify(_controller().list()), 200


@task_bp.route('/tasks/search', methods=['GET'])
def search_tasks():
    return jsonify(
        _controller().search(
            query=request.args.get('q', ''),
            status=request.args.get('status', ''),
            priority=request.args.get('priority', ''),
            user_id=request.args.get('user_id', ''),
        )
    ), 200


@task_bp.route('/tasks/stats', methods=['GET'])
def task_stats():
    return jsonify(_controller().stats()), 200


@task_bp.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    return jsonify(_controller().get(task_id)), 200


@task_bp.route('/tasks', methods=['POST'])
def create_task():
    return jsonify(_controller().create(request.get_json(silent=True))), 201


@task_bp.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    return jsonify(_controller().update(task_id, request.get_json(silent=True))), 200


@task_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    return jsonify(_controller().delete(task_id)), 200
