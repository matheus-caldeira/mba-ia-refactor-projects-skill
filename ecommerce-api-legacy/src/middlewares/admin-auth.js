'use strict';

const crypto = require('node:crypto');
const { UnauthorizedError } = require('../errors/app-errors');

/**
 * Autenticacao das rotas administrativas (achado #3 / AP-05).
 *
 * No original, `GET /api/admin/financial-report` e `DELETE /api/users/:id` eram
 * públicos: qualquer um que alcancasse a porta lia o faturamento da empresa com
 * os dados dos alunos, ou apagava usuários.
 *
 * A checagem usa comparação em tempo constante para não vazar o token por
 * diferença de tempo de resposta.
 */
function timingSafeEquals(a, b) {
  const bufferA = Buffer.from(String(a));
  const bufferB = Buffer.from(String(b));
  if (bufferA.length !== bufferB.length) return false;
  return crypto.timingSafeEqual(bufferA, bufferB);
}

function extractToken(req) {
  const header = req.get('authorization');
  if (header && header.startsWith('Bearer ')) {
    return header.slice('Bearer '.length).trim();
  }
  return req.get('x-admin-token') ?? null;
}

function requireAdmin({ adminToken }) {
  return function authenticateAdmin(req, res, next) {
    const provided = extractToken(req);

    if (!provided || !timingSafeEquals(provided, adminToken)) {
      // Mensagem única: não distingue "token ausente" de "token errado".
      return next(new UnauthorizedError('Não autorizado'));
    }
    return next();
  };
}

module.exports = { requireAdmin };
