'use strict';

const crypto = require('node:crypto');
const { promisify } = require('node:util');

const scrypt = promisify(crypto.scrypt);

const KEY_LENGTH = 64;
const SALT_BYTES = 16;
const SCHEME = 'scrypt';

class PasswordHasher {
  async hash(plainPassword) {
    const salt = crypto.randomBytes(SALT_BYTES);
    const derived = await scrypt(String(plainPassword), salt, KEY_LENGTH);
    return `${SCHEME}$${salt.toString('hex')}$${derived.toString('hex')}`;
  }

  async compare(plainPassword, storedHash) {
    const [scheme, saltHex, hashHex] = String(storedHash ?? '').split('$');
    if (scheme !== SCHEME || !saltHex || !hashHex) return false;

    const expected = Buffer.from(hashHex, 'hex');
    const derived = await scrypt(String(plainPassword), Buffer.from(saltHex, 'hex'), expected.length);
    return crypto.timingSafeEqual(derived, expected);
  }
}

module.exports = { PasswordHasher };
