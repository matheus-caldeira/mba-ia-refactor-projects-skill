"""Ponto único de leitura da configuração — tudo vem de variável de ambiente.

Regras aplicadas (P-02 do playbook):
- segredo nunca tem valor literal no código;
- em produção (``APP_ENV=production``) um segredo ausente **falha no boot**;
- fora de produção há fallback efêmero gerado em memória, que não é segredo
  versionado: muda a cada processo e serve apenas para o Flask assinar sessões
  durante o desenvolvimento;
- valores não sensíveis (host, porta, URL do banco) têm default razoável.
"""

import os
import secrets

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _as_bool(value, default=False):
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


class MissingConfigError(RuntimeError):
    """Erro de boot: variável de ambiente obrigatória ausente."""


class Settings:
    """Configuração da aplicação, resolvida uma vez na inicialização."""

    def __init__(self, env=None):
        env = env if env is not None else os.environ

        self.ENV = env.get('APP_ENV', 'development').strip().lower()
        self.IS_PRODUCTION = self.ENV == 'production'

        self.SECRET_KEY = self._secret(env, 'SECRET_KEY')

        default_db = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'tasks.db')
        self.SQLALCHEMY_DATABASE_URI = env.get('DATABASE_URL', default_db)
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False

        self.DEBUG = _as_bool(env.get('FLASK_DEBUG'), default=False)
        if self.IS_PRODUCTION:
            self.DEBUG = False

        self.HOST = env.get('HOST', '127.0.0.1')
        self.PORT = int(env.get('PORT', '5000'))

        # CORS: em produção exige lista explícita de origens permitidas.
        origins = env.get('CORS_ORIGINS', '').strip()
        if origins:
            self.CORS_ORIGINS = [o.strip() for o in origins.split(',') if o.strip()]
        else:
            self.CORS_ORIGINS = [] if self.IS_PRODUCTION else ['*']

        # Token de sessão emitido pelo /login.
        self.TOKEN_TTL_SECONDS = int(env.get('TOKEN_TTL_SECONDS', '3600'))

        # SMTP — sem nenhum valor literal de credencial no código.
        self.SMTP_HOST = env.get('SMTP_HOST', 'localhost')
        self.SMTP_PORT = int(env.get('SMTP_PORT', '587'))
        self.SMTP_USER = env.get('SMTP_USER', '')
        self.SMTP_PASSWORD = env.get('SMTP_PASSWORD', '')
        self.SMTP_USE_TLS = _as_bool(env.get('SMTP_USE_TLS'), default=True)
        # Sem credencial configurada o notificador não tenta enviar e-mail:
        # registra a notificação e loga, em vez de falhar silenciosamente.
        self.EMAIL_ENABLED = _as_bool(env.get('EMAIL_ENABLED'), default=False)

    def _secret(self, env, name):
        value = env.get(name)
        if value:
            return value
        if self.IS_PRODUCTION:
            raise MissingConfigError(
                f'Variável de ambiente obrigatória ausente em produção: {name}'
            )
        # Fallback de desenvolvimento: efêmero, gerado em memória, nunca versionado.
        return secrets.token_urlsafe(32)

    def as_flask_config(self):
        return {
            'SECRET_KEY': self.SECRET_KEY,
            'SQLALCHEMY_DATABASE_URI': self.SQLALCHEMY_DATABASE_URI,
            'SQLALCHEMY_TRACK_MODIFICATIONS': self.SQLALCHEMY_TRACK_MODIFICATIONS,
            'DEBUG': self.DEBUG,
        }


def load_settings(env=None):
    return Settings(env)
