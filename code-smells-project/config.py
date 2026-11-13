"""Configuração da aplicação: único ponto de leitura de variáveis de ambiente."""
import os

APP_VERSION = "1.0.0"
AMBIENTES_VALIDOS = ("development", "production")


class ConfigError(RuntimeError):
    """Configuração obrigatória ausente ou inválida — a aplicação não deve subir."""


def load_env_file(path=".env"):
    """Carrega KEY=VALUE de um arquivo .env local sem sobrescrever o ambiente real."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _flag(env, name, default="false"):
    return env.get(name, default).strip().lower() in ("1", "true", "yes")


class Settings:
    def __init__(self, env=None):
        env = os.environ if env is None else env

        self.APP_ENV = env.get("APP_ENV", "production").strip().lower()
        if self.APP_ENV not in AMBIENTES_VALIDOS:
            raise ConfigError(f"APP_ENV inválido: {self.APP_ENV!r} (use {AMBIENTES_VALIDOS})")
        self.IS_PRODUCTION = self.APP_ENV == "production"

        # Segredo sem default: a aplicação não sobe com uma chave conhecida.
        self.SECRET_KEY = env.get("SECRET_KEY", "")
        if not self.SECRET_KEY:
            raise ConfigError("Variável de ambiente obrigatória ausente: SECRET_KEY")

        self.DEBUG = _flag(env, "FLASK_DEBUG") and not self.IS_PRODUCTION
        self.HOST = env.get("HOST", "127.0.0.1")
        self.PORT = int(env.get("PORT", "5000"))
        self.DB_PATH = env.get("DB_PATH", "loja.db")
        self.TOKEN_MAX_AGE_SECONDS = int(env.get("TOKEN_MAX_AGE_SECONDS", "28800"))
        self.CORS_ORIGINS = env.get("CORS_ORIGINS", "*")
        self.APP_VERSION = APP_VERSION

        # Conta administradora: em produção só a partir do ambiente, nunca default.
        default_admin_email = None if self.IS_PRODUCTION else "admin@loja.com"
        default_admin_password = None if self.IS_PRODUCTION else "admin123"  # somente desenvolvimento
        self.ADMIN_EMAIL = env.get("ADMIN_EMAIL") or default_admin_email
        self.ADMIN_PASSWORD = env.get("ADMIN_PASSWORD") or default_admin_password
        if self.IS_PRODUCTION and not (self.ADMIN_EMAIL and self.ADMIN_PASSWORD):
            raise ConfigError("ADMIN_EMAIL e ADMIN_PASSWORD são obrigatórios em produção")

        # Dados de demonstração (produtos e clientes com senha conhecida) só fora de produção.
        self.SEED_DEMO_DATA = _flag(env, "SEED_DEMO_DATA", "true") and not self.IS_PRODUCTION
        # Operação destrutiva atrás de flag desligado por padrão e nunca em produção.
        self.ENABLE_RESET_DB = _flag(env, "ENABLE_RESET_DB") and not self.IS_PRODUCTION
