from flask import Blueprint, jsonify, request

from controllers import category_controller
from middlewares.auth import current_user, require_auth

category_bp = Blueprint("categories", __name__)


@category_bp.get("/categories")
@require_auth
def get_categories():
    return jsonify(category_controller.list_categories(current_user())), 200


@category_bp.post("/categories")
@require_auth
def create_category():
    return jsonify(category_controller.create_category(request.get_json(silent=True), current_user())), 201


@category_bp.put("/categories/<int:cat_id>")
@require_auth
def update_category(cat_id):
    return jsonify(category_controller.update_category(cat_id, request.get_json(silent=True), current_user())), 200


@category_bp.delete("/categories/<int:cat_id>")
@require_auth
def delete_category(cat_id):
    return jsonify(category_controller.delete_category(cat_id, current_user())), 200
