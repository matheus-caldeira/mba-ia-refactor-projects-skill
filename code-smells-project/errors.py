"""Erros de domínio tipados. As camadas internas lançam; só o error handler sabe de HTTP."""


class AppError(Exception):
    status_code = 500
    message = "Erro interno"

    def __init__(self, message=None):
        super().__init__(message or self.message)
        self.message = message or self.message


class ValidationError(AppError):
    status_code = 400
    message = "Dados inválidos"


class UnauthorizedError(AppError):
    status_code = 401
    message = "Não autorizado"


class ForbiddenError(AppError):
    status_code = 403
    message = "Acesso negado"


class NotFoundError(AppError):
    status_code = 404
    message = "Recurso não encontrado"


class ConflictError(AppError):
    status_code = 409
    message = "Conflito"
