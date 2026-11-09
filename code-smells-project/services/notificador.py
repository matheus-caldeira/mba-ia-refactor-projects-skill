"""Notificador injetável: os canais são detalhe daqui, não do controller.

Substitui os `print("ENVIANDO EMAIL: ...")` que viviam no controller (AP-08).
Em teste, injeta-se um duplo e não é preciso capturar stdout.
"""

import logging

logger = logging.getLogger(__name__)


class Notificador:
    def pedido_criado(self, pedido_id, usuario_id):
        logger.info("Pedido %s criado para o usuário %s", pedido_id, usuario_id)

    def pedido_aprovado(self, pedido_id):
        logger.info("Pedido %s aprovado. Preparar envio.", pedido_id)

    def pedido_cancelado(self, pedido_id):
        logger.info("Pedido %s cancelado. Estoque devolvido.", pedido_id)
