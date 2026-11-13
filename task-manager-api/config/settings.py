"""Configuração única da aplicação, lida de variáveis de ambiente.

Segredos não têm default: sem eles a aplicação não sobe.
"""
import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    pass


def _bool(value, default=False):
    if value is None or value == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    SECRET_KEY: str
    APP_ENV: str = "development"
    DATABASE_URL: str = "sqlite:///tasks.db"
    DEBUG: bool = False
    HOST: str = "127.0.0.1"
    PORT: int = 5000
    TOKEN_MAX_AGE: int = 8 * 60 * 60
    CORS_ORIGINS: str = "*"
    SEED_ADMIN_EMAIL: str | None = None
    SEED_ADMIN_PASSWORD: str | None = None

    @property
    def IS_PRODUCTION(self):
        return self.APP_ENV == "production"

    @classmethod
    def from_env(cls, env=None):
        if env is None:
            load_dotenv()
            env = os.environ

        secret = env.get("SECRET_KEY")
        if not secret:
            raise ConfigError("Variável de ambiente obrigatória ausente: SECRET_KEY")

        app_env = env.get("APP_ENV", "development")
        settings = cls(
            SECRET_KEY=secret,
            APP_ENV=app_env,
            DATABASE_URL=env.get("DATABASE_URL", "sqlite:///tasks.db"),
            DEBUG=_bool(env.get("FLASK_DEBUG")) and app_env != "production",
            HOST=env.get("HOST", "127.0.0.1"),
            PORT=int(env.get("PORT", "5000")),
            TOKEN_MAX_AGE=int(env.get("TOKEN_MAX_AGE", str(8 * 60 * 60))),
            CORS_ORIGINS=env.get("CORS_ORIGINS", "*"),
            SEED_ADMIN_EMAIL=env.get("SEED_ADMIN_EMAIL") or None,
            SEED_ADMIN_PASSWORD=env.get("SEED_ADMIN_PASSWORD") or None,
        )
        if settings.IS_PRODUCTION and len(secret) < 32:
            raise ConfigError("SECRET_KEY deve ter ao menos 32 caracteres em produção")
        return settings
