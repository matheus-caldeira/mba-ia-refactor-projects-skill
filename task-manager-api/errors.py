"""Erros de domínio tipados.

As camadas internas lançam estes erros; nenhuma delas conhece status code HTTP.
A tradução para resposta acontece em ``middlewares/error_handler.py``.
"""


class AppError(Exception):
    status_code = 500
    message = 'Erro interno'

    def __init__(self, message=None, details=None):
        super().__init__(message or self.message)
        if message:
            self.message = message
        self.details = details


class ValidationError(AppError):
    status_code = 400
    message = 'Dados inválidos'


class UnauthorizedError(AppError):
    status_code = 401
    message = 'Credenciais inválidas'


class ForbiddenError(AppError):
    status_code = 403
    message = 'Acesso negado'


class NotFoundError(AppError):
    status_code = 404
    message = 'Recurso não encontrado'


class ConflictError(AppError):
    status_code = 409
    message = 'Conflito'
