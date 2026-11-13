"""Composition root: carrega config, monta dependências, registra rotas e sobe o servidor."""
import logging
from types import SimpleNamespace

from flask import Flask
from flask_cors import CORS

import database
from config import Settings, load_env_file
from controllers.pedido_controller import PedidoController
from controllers.produto_controller import ProdutoController
from controllers.sistema_controller import SistemaController
from controllers.usuario_controller import UsuarioController
from middlewares.error_handler import register_error_handlers
from models.pedido_model import PedidoModel
from models.produto_model import ProdutoModel
from models.sistema_model import SistemaModel
from models.usuario_model import UsuarioModel
from routes.pedido_routes import pedido_bp
from routes.produto_routes import produto_bp
from routes.sistema_routes import sistema_bp
from routes.usuario_routes import usuario_bp
from seed import seed
from services.auth_service import AuthService
from services.notificador import Notificador
from services.pedido_service import PedidoService
from services.relatorio_service import RelatorioService


def _montar_dependencias(settings):
    get_conn = database.get_db
    produtos, usuarios = ProdutoModel(get_conn), UsuarioModel(get_conn)
    pedidos, sistema = PedidoModel(get_conn), SistemaModel(get_conn)
    auth = AuthService(settings.SECRET_KEY, settings.TOKEN_MAX_AGE_SECONDS)
    pedido_service = PedidoService(get_conn, pedidos, produtos, usuarios, Notificador())
    return SimpleNamespace(
        settings=settings,
        auth=auth,
        usuarios=usuarios,
        produto_controller=ProdutoController(get_conn, produtos),
        usuario_controller=UsuarioController(usuarios, auth),
        pedido_controller=PedidoController(pedidos, pedido_service),
        relatorio_service=RelatorioService(pedidos),
        sistema_controller=SistemaController(get_conn, sistema, produtos, usuarios, pedidos, settings),
    )


def _inicializar_banco(settings):
    conn = database.connect(settings.DB_PATH)
    try:
        database.init_schema(conn)
        seed(conn, settings)
    finally:
        conn.close()


def create_app(settings=None):
    if settings is None:
        load_env_file()
        settings = Settings()

    app = Flask(__name__)
    app.config.update(SECRET_KEY=settings.SECRET_KEY, DEBUG=settings.DEBUG, DB_PATH=settings.DB_PATH)
    origens = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    CORS(app, origins=origens or "*")

    _inicializar_banco(settings)
    app.extensions["loja"] = _montar_dependencias(settings)
    app.teardown_appcontext(database.close_db)

    for blueprint in (sistema_bp, produto_bp, usuario_bp, pedido_bp):
        app.register_blueprint(blueprint)
    register_error_handlers(app)  # por último, para capturar tudo
    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        force=True)
    application = create_app()
    cfg = application.extensions["loja"].settings
    logging.getLogger(__name__).info("Servidor em http://%s:%s (APP_ENV=%s)", cfg.HOST, cfg.PORT, cfg.APP_ENV)
    application.run(host=cfg.HOST, port=cfg.PORT, debug=cfg.DEBUG)
