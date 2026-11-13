const crypto = require('crypto');

/** Token de acesso assinado com HMAC-SHA256: base64url(payload).base64url(assinatura). */
class TokenService {
    constructor({ secret, ttlSeconds }) {
        this.secret = secret;
        this.ttlSeconds = ttlSeconds;
    }

    issue(userId) {
        const payload = Buffer.from(JSON.stringify({
            sub: userId,
            exp: Math.floor(Date.now() / 1000) + this.ttlSeconds,
        })).toString('base64url');
        return `${payload}.${this.sign(payload)}`;
    }

    /** Retorna o id do usuário, ou null se o token for inválido/expirado. */
    verify(token) {
        const [payload, signature] = String(token || '').split('.');
        if (!payload || !signature) return null;

        const expected = Buffer.from(this.sign(payload));
        const received = Buffer.from(signature);
        if (expected.length !== received.length || !crypto.timingSafeEqual(expected, received)) return null;

        try {
            const { sub, exp } = JSON.parse(Buffer.from(payload, 'base64url').toString('utf8'));
            if (!Number.isInteger(sub) || typeof exp !== 'number' || exp < Date.now() / 1000) return null;
            return sub;
        } catch {
            return null;
        }
    }

    sign(payload) {
        return crypto.createHmac('sha256', this.secret).update(payload).digest('base64url');
    }
}

module.exports = { TokenService };
