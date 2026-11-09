"""Fonte única de "agora" para os models.

``datetime.utcnow()`` está deprecado no Python 3.12. A substituição canônica é
``datetime.now(timezone.utc)``, que devolve um datetime **aware**. Porém as
colunas do banco (e as linhas já gravadas em ``tasks.db``) guardam datetimes
**naive** em UTC; comparar naive com aware levanta ``TypeError``.

Para trocar a API deprecada sem alterar comportamento nem o formato das
respostas (``str(datetime)`` sem sufixo de fuso), calculamos o instante com a
API moderna e removemos o tzinfo — o valor continua sendo UTC, apenas naive,
exatamente como antes.
"""

from datetime import datetime, timezone


def utcnow():
    """Instante atual em UTC, naive (compatível com as colunas existentes)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
