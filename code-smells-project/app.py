"""Composition root: monta a aplicação e sobe o servidor. Nada além disso."""

import logging

from flask import Flask
from flask_cors import CORS

from config import settings
from controllers import PedidoController, RelatorioController
from middlewares import register_error_handlers
from models import database
from routes import criar_pedido_bp, produto_bp, system_bp, usuario_bp
from services import Notificador, PedidoService, RelatorioService


def create_app(config=None):
    config = config or settings

    logging.basicConfig(
        level=logging.DEBUG if config.DEBUG else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )

    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["DEBUG"] = config.DEBUG
    CORS(app, origins=config.CORS_ORIGINS)

    # Conexão com escopo de requisição.
    app.teardown_appcontext(database.close_db)

    # Schema e seed uma única vez, no boot.
    conexao = database.conectar(config.DATABASE_PATH)
    try:
        database.inicializar(conexao)
    finally:
        conexao.close()

    # Dependências concretas, injetadas nos controllers.
    notificador = Notificador()
    pedido_controller = PedidoController(PedidoService(notificador))
    relatorio_controller = RelatorioController(RelatorioService())

    app.register_blueprint(system_bp)
    app.register_blueprint(produto_bp)
    app.register_blueprint(usuario_bp)
    app.register_blueprint(criar_pedido_bp(pedido_controller, relatorio_controller))

    # Error handler por último, para capturar tudo.
    register_error_handlers(app)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
