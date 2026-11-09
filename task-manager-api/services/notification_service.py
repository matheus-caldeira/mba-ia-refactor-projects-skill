"""Notificações por e-mail. Credenciais vêm da configuração injetada."""

import logging
import smtplib

from models.clock import utcnow

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, settings):
        """Recebe a configuração já resolvida — nada de segredo literal aqui."""
        self._settings = settings
        self.notifications = []

    def send_email(self, to, subject, body):
        if not self._settings.EMAIL_ENABLED:
            logger.info('E-mail desabilitado; notificação apenas registrada: %s', to)
            return False
        if not self._settings.SMTP_USER or not self._settings.SMTP_PASSWORD:
            logger.warning('Credenciais SMTP ausentes; e-mail não enviado para %s', to)
            return False
        try:
            server = smtplib.SMTP(self._settings.SMTP_HOST, self._settings.SMTP_PORT)
            try:
                if self._settings.SMTP_USE_TLS:
                    server.starttls()
                server.login(self._settings.SMTP_USER, self._settings.SMTP_PASSWORD)
                message = f'Subject: {subject}\n\n{body}'
                server.sendmail(self._settings.SMTP_USER, to, message)
            finally:
                server.quit()
            logger.info('E-mail enviado para %s', to)
            return True
        except Exception:
            logger.exception('Falha ao enviar e-mail para %s', to)
            return False

    def notify_task_assigned(self, user, task):
        subject = f'Nova task atribuída: {task.title}'
        body = (
            f'Olá {user.name},\n\n'
            f"A task '{task.title}' foi atribuída a você.\n\n"
            f'Prioridade: {task.priority}\nStatus: {task.status}'
        )
        self.send_email(user.email, subject, body)
        self.notifications.append(
            {
                'type': 'task_assigned',
                'user_id': user.id,
                'task_id': task.id,
                'timestamp': utcnow(),
            }
        )

    def notify_task_overdue(self, user, task):
        subject = f'Task atrasada: {task.title}'
        body = (
            f'Olá {user.name},\n\n'
            f"A task '{task.title}' está atrasada!\n\n"
            f'Data limite: {task.due_date}'
        )
        self.send_email(user.email, subject, body)

    def get_notifications(self, user_id):
        return [n for n in self.notifications if n['user_id'] == user_id]
