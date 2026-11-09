'use strict';

/**
 * Erros de domínio tipados (P-12).
 *
 * As camadas internas lancam estes erros; elas não sabem o que e status code.
 * A traducao para HTTP acontece em um único lugar: middlewares/error-handler.js.
 */

class AppError extends Error {
  constructor(message, statusCode = 500) {
    super(message);
    this.name = new.target.name;
    this.statusCode = statusCode;
    this.isOperational = true;
    Error.captureStackTrace?.(this, new.target);
  }
}

class ValidationError extends AppError {
  constructor(message = 'Dados inválidos') {
    super(message, 400);
  }
}

class UnauthorizedError extends AppError {
  constructor(message = 'Não autorizado') {
    super(message, 401);
  }
}

class ForbiddenError extends AppError {
  constructor(message = 'Acesso negado') {
    super(message, 403);
  }
}

class NotFoundError extends AppError {
  constructor(message = 'Recurso não encontrado') {
    super(message, 404);
  }
}

class PaymentDeclinedError extends AppError {
  constructor(message = 'Pagamento recusado') {
    super(message, 400);
  }
}

module.exports = {
  AppError,
  ValidationError,
  UnauthorizedError,
  ForbiddenError,
  NotFoundError,
  PaymentDeclinedError,
};
