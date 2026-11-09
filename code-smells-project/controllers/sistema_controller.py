"""Casos de uso de sistema: health check e reset administrativo."""

import logging

from config import settings
from middlewares.errors import ForbiddenError
from models import database

logger = logging.getLogger(__name__)


def health():
    # Sem segredo, flag de debug, ambiente ou caminho de banco (AP-02/AP-06).
    return {
        "status": "ok",
        "database": "connected",
        "counts": database.contar_registros(),
        "versao": settings.APP_VERSION,
    }


def resetar_banco():
    if settings.IS_PRODUCTION:
        raise ForbiddenError("Operação administrativa desabilitada em produção")
    database.resetar()
    logger.warning("Banco de dados resetado via rota administrativa")
