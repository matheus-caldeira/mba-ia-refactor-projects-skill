from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def commit():
    """Fecha a unidade de trabalho do caso de uso: tudo ou nada."""
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
