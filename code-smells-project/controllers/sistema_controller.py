import logging

from database import transaction
from errors import ForbiddenError

logger = logging.getLogger(__name__)


class SistemaController:
    def __init__(self, get_conn, sistema, produtos, usuarios, pedidos, settings):
        self._conn = get_conn
        self._sistema = sistema
        self._produtos = produtos
        self._usuarios = usuarios
        self._pedidos = pedidos
        self._settings = settings

    def health(self):
        """Só o que diz se o serviço está vivo; nada de segredo, caminho ou flags."""
        self._sistema.ping()
        return {
            "status": "ok",
            "database": "connected",
            "counts": {
                "produtos": self._produtos.contar(),
                "usuarios": self._usuarios.contar(),
                "pedidos": self._pedidos.contar(),
            },
            "versao": self._settings.APP_VERSION,
        }

    def reset_db(self, ator):
        if not self._settings.ENABLE_RESET_DB:
            raise ForbiddenError("Operação desabilitada neste ambiente")
        with transaction(self._conn()):
            self._sistema.apagar_tudo()
        logger.warning("Banco de dados resetado pelo usuário %s", ator["id"])
