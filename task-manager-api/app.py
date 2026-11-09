"""Composition root: monta a aplicação e sobe o servidor. Nada além disso."""

import logging
import os

from flask import Flask, jsonify
from flask_cors import CORS

from config.settings import load_settings
from controllers.category_controller import CategoryController
from controllers.report_controller import ReportController
from controllers.task_controller import TaskController
from controllers.user_controller import UserController
from database import db
from middlewares.auth import load_current_user
from middlewares.error_handler import register_error_handlers
from models.clock import utcnow
from models.user import User
from repositories.category_repository import CategoryRepository
from repositories.task_repository import TaskRepository
from repositories.user_repository import UserRepository
from routes.report_routes import report_bp
from routes.task_routes import task_bp
from routes.user_routes import user_bp
from services.auth_service import AuthService
from services.notification_service import NotificationService


def create_app(settings=None):
    """Application factory — permite criar a app com configuração de teste."""
    settings = settings or load_settings()

    app = Flask(__name__)
    app.config.update(settings.as_flask_config())
    app.extensions['settings'] = settings

    logging.basicConfig(
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
        force=True,
    )

    CORS(app, origins=settings.CORS_ORIGINS)
    db.init_app(app)

    # Dependências concretas, instanciadas uma vez e injetadas.
    task_repo = TaskRepository()
    user_repo = UserRepository()
    category_repo = CategoryRepository()

    auth_service = AuthService(settings, user_repo)
    notification_service = NotificationService(settings)

    app.extensions['auth_service'] = auth_service
    app.extensions['notification_service'] = notification_service
    app.extensions['task_controller'] = TaskController(
        task_repo, user_repo, category_repo, notification_service
    )
    app.extensions['user_controller'] = UserController(
        user_repo, task_repo, auth_service
    )
    app.extensions['category_controller'] = CategoryController(category_repo, task_repo)
    app.extensions['report_controller'] = ReportController(
        task_repo, user_repo, category_repo
    )

    # Identifica o portador do token quando houver, sem bloquear rotas públicas.
    app.before_request(load_current_user)

    app.register_blueprint(task_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(report_bp)

    @app.route('/')
    def index():
        return jsonify({'message': 'Task Manager API', 'version': '1.0'}), 200

    @app.route('/health')
    def health():
        return jsonify({'status': 'ok', 'timestamp': str(utcnow())}), 200

    # Registrado por último, para capturar tudo.
    register_error_handlers(app)

    init_database(app)
    return app


def init_database(app):
    os.makedirs(app.instance_path, exist_ok=True)
    uri = app.config['SQLALCHEMY_DATABASE_URI']
    if uri.startswith('sqlite:///'):
        os.makedirs(os.path.dirname(uri[len('sqlite:///'):]), exist_ok=True)
    with app.app_context():
        db.create_all()
        ensure_admin(app.extensions['settings'])


def ensure_admin(settings):
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        return
    if User.query.filter_by(email=settings.ADMIN_EMAIL).first():
        return
    admin = User(name=settings.ADMIN_NAME, email=settings.ADMIN_EMAIL, role='admin')
    admin.set_password(settings.ADMIN_PASSWORD)
    db.session.add(admin)
    db.session.commit()


app = create_app()

if __name__ == '__main__':
    settings = app.extensions['settings']
    app.run(debug=settings.DEBUG, host=settings.HOST, port=settings.PORT)
