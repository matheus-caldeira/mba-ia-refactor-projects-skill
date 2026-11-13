from datetime import datetime, timezone


def utcnow():
    """Instante atual em UTC, sem tzinfo.

    As colunas DateTime do SQLite guardam valores naive; manter o valor naive
    (porém calculado por API não deprecated) preserva o formato já gravado e
    permite comparar com o que vem do banco.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
