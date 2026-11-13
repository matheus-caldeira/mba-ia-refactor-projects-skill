const { UnauthorizedError } = require('../domain/errors');

class AuthController {
    constructor({ users, passwordHasher, tokenService }) {
        Object.assign(this, { users, passwordHasher, tokenService });
    }

    async login({ email, password }) {
        const credentials = await this.users.findCredentialsByEmail(email);
        const valid = credentials && await this.passwordHasher.verify(password, credentials.passwordHash);
        // Mensagem única: não revela se o e-mail existe.
        if (!valid) throw new UnauthorizedError('Credenciais inválidas');

        return { token: this.tokenService.issue(credentials.id), token_type: 'Bearer', expires_in: this.tokenService.ttlSeconds };
    }
}

module.exports = { AuthController };
