"""Composition root: carrega config, monta extensões, rotas e handlers."""
import logging

from flask import Flask
from flask_cors import CORS

from config import Settings
from database import db
from middlewares.error_handler import register_error_handlers
from routes.category_routes import category_bp
from routes.report_routes import report_bp
from routes.system_routes import system_bp
from routes.task_routes import task_bp
from routes.user_routes import user_bp

import models  # noqa: F401  (registra as entidades no metadata antes do create_all)


def create_app(settings=None):
    settings = settings or Settings.from_env()

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=settings.SECRET_KEY,
        SQLALCHEMY_DATABASE_URI=settings.DATABASE_URL,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        TOKEN_MAX_AGE=settings.TOKEN_MAX_AGE,
        SETTINGS=settings,
    )
    logging.basicConfig(level=logging.DEBUG if settings.DEBUG else logging.INFO)

    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    if origins:
        CORS(app, origins=origins)
    db.init_app(app)

    for blueprint in (system_bp, task_bp, user_bp, category_bp, report_bp):
        app.register_blueprint(blueprint)
    register_error_handlers(app)  # por último, para capturar tudo

    with app.app_context():
        db.create_all()
    return app


if __name__ == "__main__":
    settings = Settings.from_env()
    create_app(settings).run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
