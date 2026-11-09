from flask import current_app, has_app_context

from .settings import settings


def config_atual():
    if has_app_context():
        return current_app.extensions.get("settings", settings)
    return settings
