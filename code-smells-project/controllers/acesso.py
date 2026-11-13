"""Regras de acesso por ator, compartilhadas pelos controllers."""
from errors import ForbiddenError
from models.usuario_model import TIPO_ADMIN


def eh_admin(ator):
    return ator is not None and ator["tipo"] == TIPO_ADMIN


def escopo_leitura(ator):
    """None = vê tudo (admin); senão, o id do próprio ator."""
    return None if eh_admin(ator) else ator["id"]


def exigir_dono_ou_admin(ator, usuario_id):
    if not eh_admin(ator) and ator["id"] != usuario_id:
        raise ForbiddenError("Acesso negado")
