"""Notificações de pedido. Hoje registram em log; um canal real (e-mail/SMS/push) entra aqui."""
import logging

logger = logging.getLogger(__name__)


class Notificador:
    def pedido_criado(self, pedido_id, usuario_id):
        logger.info("Notificação [email/sms/push]: pedido %s criado para usuário %s", pedido_id, usuario_id)

    def status_alterado(self, pedido_id, novo_status):
        logger.info("Notificação: pedido %s mudou para '%s'", pedido_id, novo_status)
