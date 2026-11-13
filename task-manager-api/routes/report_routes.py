from flask import Blueprint, jsonify

from controllers import report_controller
from middlewares.auth import current_user, require_auth

report_bp = Blueprint("reports", __name__)


@report_bp.get("/reports/summary")
@require_auth
def summary_report():
    return jsonify(report_controller.summary_report(current_user())), 200


@report_bp.get("/reports/user/<int:user_id>")
@require_auth
def user_report(user_id):
    return jsonify(report_controller.user_report(user_id, current_user())), 200
