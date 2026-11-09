'use strict';

const { AppError } = require('../errors/app-errors');

/**
 * Tratamento de erro CENTRALIZADO (P-12). Registrado por último, para capturar tudo.
 *
 * Substitui os `res.status(500).send("Erro DB")` espalhados e os callbacks que
 * ignoravam `err` silenciosamente.
 *
 * - Erro de domínio tipado  -> seu próprio status e mensagem.
 * - Qualquer outra exceção  -> 500 com mensagem genérica, sem detalhe interno,
 *                             e com o stack trace real registrado no servidor.
 */
function errorHandler(logger = console) {
  // eslint-disable-next-line no-unused-vars -- o 4o argumento identifica o handler de erro no Express
  return function handleError(err, req, res, next) {
    const isKnown = err instanceof AppError;
    const status = isKnown ? err.statusCode : 500;

    if (!isKnown || status >= 500) {
      logger.error(`[erro] ${req.method} ${req.originalUrl}`, err);
    }

    // O corpo de erro preserva o formato do código original: texto puro.
    res.status(status).send(isKnown ? err.message : 'Erro interno');
  };
}

/** 404 para rota inexistente, no mesmo formato do resto da API. */
function notFoundHandler(req, res) {
  res.status(404).send('Recurso não encontrado');
}

module.exports = { errorHandler, notFoundHandler };
