from flask import Blueprint, jsonify, request

from controllers import task_controller
from middlewares.auth import current_user, require_auth

task_bp = Blueprint("tasks", __name__)


@task_bp.get("/tasks")
@require_auth
def get_tasks():
    return jsonify(task_controller.list_tasks(current_user())), 200


@task_bp.get("/tasks/<int:task_id>")
@require_auth
def get_task(task_id):
    return jsonify(task_controller.get_task(task_id, current_user())), 200


@task_bp.post("/tasks")
@require_auth
def create_task():
    return jsonify(task_controller.create_task(request.get_json(silent=True), current_user())), 201


@task_bp.put("/tasks/<int:task_id>")
@require_auth
def update_task(task_id):
    return jsonify(task_controller.update_task(task_id, request.get_json(silent=True), current_user())), 200


@task_bp.delete("/tasks/<int:task_id>")
@require_auth
def delete_task(task_id):
    return jsonify(task_controller.delete_task(task_id, current_user())), 200


@task_bp.get("/tasks/search")
@require_auth
def search_tasks():
    return jsonify(task_controller.search_tasks(request.args, current_user())), 200


@task_bp.get("/tasks/stats")
@require_auth
def task_stats():
    return jsonify(task_controller.task_stats(current_user())), 200
