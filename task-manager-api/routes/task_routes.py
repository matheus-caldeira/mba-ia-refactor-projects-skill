from flask import Blueprint, current_app, jsonify, request

from middlewares.auth import current_user, require_auth

task_bp = Blueprint('tasks', __name__)


def _controller():
    return current_app.extensions['task_controller']


@task_bp.route('/tasks', methods=['GET'])
@require_auth
def get_tasks():
    return jsonify(_controller().list()), 200


@task_bp.route('/tasks/search', methods=['GET'])
@require_auth
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
@require_auth
def task_stats():
    return jsonify(_controller().stats()), 200


@task_bp.route('/tasks/<int:task_id>', methods=['GET'])
@require_auth
def get_task(task_id):
    return jsonify(_controller().get(task_id)), 200


@task_bp.route('/tasks', methods=['POST'])
@require_auth
def create_task():
    data = request.get_json(silent=True)
    return jsonify(_controller().create(data, actor=current_user())), 201


@task_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@require_auth
def update_task(task_id):
    data = request.get_json(silent=True)
    return jsonify(_controller().update(task_id, data, actor=current_user())), 200


@task_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@require_auth
def delete_task(task_id):
    return jsonify(_controller().delete(task_id, actor=current_user())), 200
