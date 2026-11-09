'use strict';

/**
 * Encaminha rejeicoes de handlers async para o error handler central.
 *
 * Sem isto, uma promise rejeitada dentro de uma rota async no Express 4 não chega
 * ao middleware de erro e a requisição fica pendurada ate o timeout.
 */
function asyncHandler(handler) {
  return function wrapped(req, res, next) {
    Promise.resolve(handler(req, res, next)).catch(next);
  };
}

module.exports = { asyncHandler };
