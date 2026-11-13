class AppError extends Error {
    constructor(message, statusCode = 500) {
        super(message);
        this.name = this.constructor.name;
        this.statusCode = statusCode;
    }
}

class ValidationError extends AppError {
    constructor(message = 'Dados inválidos') { super(message, 400); }
}

class PaymentDeniedError extends AppError {
    constructor(message = 'Pagamento recusado') { super(message, 400); }
}

class UnauthorizedError extends AppError {
    constructor(message = 'Não autenticado') { super(message, 401); }
}

class ForbiddenError extends AppError {
    constructor(message = 'Acesso negado') { super(message, 403); }
}

class NotFoundError extends AppError {
    constructor(message = 'Recurso não encontrado') { super(message, 404); }
}

module.exports = { AppError, ValidationError, PaymentDeniedError, UnauthorizedError, ForbiddenError, NotFoundError };
