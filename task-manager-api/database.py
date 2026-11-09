"""Instância única do SQLAlchemy, inicializada pelo application factory."""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
