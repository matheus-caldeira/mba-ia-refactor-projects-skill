"""Orquestra os casos de uso de Usuário e autenticação."""

from middlewares.errors import (
    ConflictError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from models import usuario_model


def listar():
    return usuario_model.listar_todos()


def buscar(usuario_id):
    usuario = usuario_model.buscar_por_id(usuario_id)
    if usuario is None:
        raise NotFoundError("Usuário não encontrado")
    return usuario


def criar(dados):
    if not dados:
        raise ValidationError("Dados inválidos")

    nome = (dados.get("nome") or "").strip()
    email = (dados.get("email") or "").strip()
    senha = dados.get("senha") or ""

    if not nome or not email or not senha:
        raise ValidationError("Nome, email e senha são obrigatórios")
    if usuario_model.existe_email(email):
        raise ConflictError("E-mail já cadastrado")

    return usuario_model.criar(nome, email, senha)


def login(dados):
    if not dados:
        raise ValidationError("Dados inválidos")

    email = (dados.get("email") or "").strip()
    senha = dados.get("senha") or ""

    if not email or not senha:
        raise ValidationError("Email e senha são obrigatórios")

    usuario = usuario_model.verificar_credenciais(email, senha)
    if usuario is None:
        # Mensagem única: não revela se o e-mail existe.
        raise UnauthorizedError("Email ou senha inválidos")
    return usuario
