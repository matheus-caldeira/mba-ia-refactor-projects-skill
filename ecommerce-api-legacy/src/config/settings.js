const fs = require('fs');
const path = require('path');

const ENV_FILE = path.resolve(__dirname, '../../.env');
if (fs.existsSync(ENV_FILE)) process.loadEnvFile(ENV_FILE);

class ConfigError extends Error {}

function required(name) {
    const value = process.env[name];
    if (!value) throw new ConfigError(`Variável de ambiente obrigatória ausente: ${name}`);
    return value;
}

function loadSettings(env = process.env) {
    const isProduction = env.NODE_ENV === 'production';

    const authSecret = required('AUTH_SECRET');
    if (authSecret.length < 32) throw new ConfigError('AUTH_SECRET deve ter ao menos 32 caracteres');

    // Conta administradora: em produção só com credenciais do ambiente (boot falha sem elas).
    // Os defaults abaixo valem SOMENTE para desenvolvimento local.
    const adminEmail = env.ADMIN_EMAIL || (isProduction ? null : 'admin@lms.local');
    const adminPassword = env.ADMIN_PASSWORD || (isProduction ? null : 'admin-dev-only');
    if (!adminEmail || !adminPassword) {
        throw new ConfigError('ADMIN_EMAIL e ADMIN_PASSWORD são obrigatórios em produção');
    }

    return Object.freeze({
        isProduction,
        port: parseInt(env.PORT || '3000', 10),
        host: env.HOST || '127.0.0.1',
        dbPath: env.DB_PATH || ':memory:',
        paymentGatewayKey: required('PAYMENT_GATEWAY_KEY'),
        authSecret,
        tokenTtlSeconds: parseInt(env.TOKEN_TTL_SECONDS || '3600', 10),
        admin: Object.freeze({ name: env.ADMIN_NAME || 'Administrador', email: adminEmail, password: adminPassword }),
    });
}

module.exports = { loadSettings, ConfigError };
