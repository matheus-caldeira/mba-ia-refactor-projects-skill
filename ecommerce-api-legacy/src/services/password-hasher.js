const crypto = require('crypto');
const { promisify } = require('util');

const scrypt = promisify(crypto.scrypt);
const KEY_LENGTH = 64;
const SALT_BYTES = 16;

/** Hash de senha com scrypt (lento, com salt por usuário). Formato: scrypt$<salt>$<hash>. */
class PasswordHasher {
    async hash(password) {
        const salt = crypto.randomBytes(SALT_BYTES).toString('hex');
        const derived = await scrypt(password, salt, KEY_LENGTH);
        return `scrypt$${salt}$${derived.toString('hex')}`;
    }

    async verify(password, stored) {
        const [algorithm, salt, expectedHex] = String(stored || '').split('$');
        if (algorithm !== 'scrypt' || !salt || !expectedHex) return false;
        const expected = Buffer.from(expectedHex, 'hex');
        const derived = await scrypt(password, salt, expected.length);
        return crypto.timingSafeEqual(derived, expected);
    }

    /** Senha aleatória para contas criadas sem senha: ninguém a conhece. */
    randomPassword() {
        return crypto.randomBytes(24).toString('base64url');
    }
}

module.exports = { PasswordHasher };
