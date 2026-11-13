const { UnauthorizedError, ForbiddenError } = require('../domain/errors');
const { asyncHandler } = require('./async-handler');

const BEARER_PREFIX = 'Bearer ';

/** Exige token válido de um usuário existente; expõe { id, role } em req.user. */
function authenticate({ tokenService, users }) {
    return asyncHandler(async (req, res, next) => {
        const header = req.get('Authorization') || '';
        if (!header.startsWith(BEARER_PREFIX)) throw new UnauthorizedError();

        const userId = tokenService.verify(header.slice(BEARER_PREFIX.length));
        const user = userId && await users.findById(userId);
        if (!user) throw new UnauthorizedError('Token inválido ou expirado');

        req.user = { id: user.id, role: user.role };
        next();
    });
}

function requireRole(role) {
    return (req, res, next) => next(req.user && req.user.role === role ? undefined : new ForbiddenError());
}

module.exports = { authenticate, requireRole };
