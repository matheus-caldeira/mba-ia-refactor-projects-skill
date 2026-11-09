"""Ponto único de leitura da configuração da aplicação.

Regra da Fase 3: nenhum segredo literal no código. Tudo vem de variável de
ambiente. Em desenvolvimento há fallback gerado em memória; em produção
(`APP_ENV=production`) a ausência de `SECRET_KEY` derruba o boot — é preferível
falhar a subir inseguro com um segredo previsível.
"""

import os
import secrets


DEV_ADMIN_EMAIL = "admin@loja.com"
DEV_ADMIN_PASSWORD = "admin123"


def _env_bool_from(env, nome, padrao="false"):
    return env.get(nome, padrao).strip().lower() in ("1", "true", "yes", "on")


class ConfigError(RuntimeError):
    """Erro de configuração detectado na inicialização."""


class Settings:
    def __init__(self, env=None):
        env = env if env is not None else os.environ

        self.APP_ENV = env.get("APP_ENV", "development").strip().lower()
        self.IS_PRODUCTION = self.APP_ENV == "production"

        self.HOST = env.get("HOST", "127.0.0.1")
        self.PORT = int(env.get("PORT", "5000"))
        self.DEBUG = _env_bool_from(env, "DEBUG") and not self.IS_PRODUCTION

        self.DATABASE_PATH = env.get("DATABASE_PATH", "loja.db")
        self.CORS_ORIGINS = env.get("CORS_ORIGINS", "*")

        self.SECRET_KEY = self._resolver_secret_key(env)

        self.TOKEN_TTL_SECONDS = int(env.get("TOKEN_TTL_SECONDS", "3600"))

        self.APP_VERSION = env.get("APP_VERSION", "1.0.0")

        self.ENABLE_RESET_DB = _env_bool_from(env, "ENABLE_RESET_DB") and not self.IS_PRODUCTION
        self.SEED_DEMO_USERS = not self.IS_PRODUCTION

        self.ADMIN_NAME = env.get("ADMIN_NAME", "Admin")
        self.ADMIN_EMAIL = self._credencial_admin(env, "ADMIN_EMAIL", DEV_ADMIN_EMAIL)
        self.ADMIN_PASSWORD = self._credencial_admin(env, "ADMIN_PASSWORD", DEV_ADMIN_PASSWORD)

    def _credencial_admin(self, env, nome, padrao_dev):
        valor = env.get(nome, "").strip()
        if valor:
            return valor
        if self.IS_PRODUCTION:
            raise ConfigError(
                f"Variável de ambiente obrigatória ausente: {nome}. "
                "Em produção a conta administradora só é criada com credenciais do ambiente."
            )
        return padrao_dev

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
