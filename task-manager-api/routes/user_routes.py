from flask import Blueprint, jsonify, request

from controllers import auth_controller, user_controller
from middlewares.auth import current_user, optional_auth, require_auth

user_bp = Blueprint("users", __name__)


@user_bp.get("/users")
@require_auth
def get_users():
    return jsonify(user_controller.list_users(current_user())), 200


@user_bp.get("/users/<int:user_id>")
@require_auth
def get_user(user_id):
    return jsonify(user_controller.get_user(user_id, current_user())), 200


@user_bp.post("/users")
@optional_auth
def create_user():
    return jsonify(user_controller.create_user(request.get_json(silent=True), current_user())), 201


@user_bp.put("/users/<int:user_id>")
@require_auth
def update_user(user_id):
    return jsonify(user_controller.update_user(user_id, request.get_json(silent=True), current_user())), 200


@user_bp.delete("/users/<int:user_id>")
@require_auth
def delete_user(user_id):
    return jsonify(user_controller.delete_user(user_id, current_user())), 200


@user_bp.get("/users/<int:user_id>/tasks")
@require_auth
def get_user_tasks(user_id):
    return jsonify(user_controller.list_user_tasks(user_id, current_user())), 200


@user_bp.post("/login")
def login():
    return jsonify(auth_controller.login(request.get_json(silent=True))), 200
