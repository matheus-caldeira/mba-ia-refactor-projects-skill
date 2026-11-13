"""Erros de domínio tipados. As camadas internas lançam; o handler central traduz."""


class AppError(Exception):
    status_code = 500
    message = "Erro interno"

    def __init__(self, message=None):
        super().__init__(message or self.message)
        if message:
            self.message = message


class ValidationError(AppError):
    status_code, message = 400, "Dados inválidos"


class UnauthorizedError(AppError):
    status_code, message = 401, "Não autenticado"


class ForbiddenError(AppError):
    status_code, message = 403, "Acesso negado"


class NotFoundError(AppError):
    status_code, message = 404, "Recurso não encontrado"


class ConflictError(AppError):
    status_code, message = 409, "Conflito"
