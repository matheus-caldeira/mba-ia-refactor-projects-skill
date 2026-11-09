'use strict';

/**
 * Ponto ÚNICO de leitura de configuração (P-02).
 *
 * Regras aplicadas:
 * - Nenhum segredo literal no código.
 * - Segredo sem default em produção: a app FALHA no boot em vez de subir insegura.
 * - Em desenvolvimento, um fallback explícito e obviamente falso e gerado, para
 *   permitir rodar local sem .env — nunca um valor que pareça de produção.
 * - Valores não sensíveis (porta, host) podem ter default razoável.
 */

function readOptional(name, fallback) {
  const value = process.env[name];
  return value === undefined || value === '' ? fallback : value;
}

/**
 * Segredo: obrigatório em produção, fallback de dev explicitamente marcado fora dela.
 */
function readSecret(name, { isProduction, devFallback }) {
  const value = process.env[name];
  if (value !== undefined && value !== '') return value;

  if (isProduction) {
    throw new Error(
      `Variável de ambiente obrigatória ausente: ${name}. ` +
        'Em produção segredos não possuem valor default.'
    );
  }
  return devFallback;
}

function buildSettings(env = process.env) {
  const nodeEnv = readOptional('NODE_ENV', 'development');
  const isProduction = nodeEnv === 'production';

  const port = Number.parseInt(readOptional('PORT', '3000'), 10);
  if (!Number.isInteger(port) || port <= 0 || port > 65535) {
    throw new Error(`PORT inválida: ${env.PORT}`);
  }

  return {
    nodeEnv,
    isProduction,
    port,
    database: {
      path: readOptional('DATABASE_PATH', ':memory:'),
    },
    payment: {
      gatewayKey: readSecret('PAYMENT_GATEWAY_KEY', {
        isProduction,
        devFallback: 'dev-nao-use-em-producao',
      }),
    },
    admin: {
      apiToken: readSecret('ADMIN_API_TOKEN', {
        isProduction,
        devFallback: 'dev-admin-token',
      }),
    },
  };
}

module.exports = { buildSettings };
