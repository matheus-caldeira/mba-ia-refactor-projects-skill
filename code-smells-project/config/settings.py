"""Ponto único de leitura da configuração da aplicação.

Regra da Fase 3: nenhum segredo literal no código. Tudo vem de variável de
ambiente. Em desenvolvimento há fallback gerado em memória; em produção
(`APP_ENV=production`) a ausência de `SECRET_KEY` derruba o boot — é preferível
falhar a subir inseguro com um segredo previsível.
"""

import os
import secrets


def _env_bool(nome, padrao="false"):
    return os.environ.get(nome, padrao).strip().lower() in ("1", "true", "yes", "on")


class ConfigError(RuntimeError):
    """Erro de configuração detectado na inicialização."""


class Settings:
    def __init__(self, env=None):
        env = env if env is not None else os.environ

        self.APP_ENV = env.get("APP_ENV", "development").strip().lower()
        self.IS_PRODUCTION = self.APP_ENV == "production"

        self.HOST = env.get("HOST", "127.0.0.1")
        self.PORT = int(env.get("PORT", "5000"))
        self.DEBUG = _env_bool("DEBUG") and not self.IS_PRODUCTION

        self.DATABASE_PATH = env.get("DATABASE_PATH", "loja.db")
        self.CORS_ORIGINS = env.get("CORS_ORIGINS", "*")

        self.SECRET_KEY = self._resolver_secret_key(env)

        # Token das rotas administrativas (/admin/*). Sem ele, elas ficam
        # desabilitadas — nunca abertas.
        self.ADMIN_TOKEN = env.get("ADMIN_TOKEN", "").strip()

        self.APP_VERSION = env.get("APP_VERSION", "1.0.0")

    def _resolver_secret_key(self, env):
        chave = env.get("SECRET_KEY", "").strip()
        if chave:
            return chave
        if self.IS_PRODUCTION:
            raise ConfigError(
                "Variável de ambiente obrigatória ausente: SECRET_KEY. "
                "Defina-a antes de subir a aplicação em produção."
            )
        # Fallback de desenvolvimento: aleatório por processo, nunca versionado.
        return secrets.token_hex(32)


settings = Settings()
