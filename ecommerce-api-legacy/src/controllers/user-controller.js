const { Roles } = require('../domain/constants');
const { ForbiddenError, NotFoundError } = require('../domain/errors');

class UserController {
    constructor({ db, users }) {
        this.db = db;
        this.users = users;
    }

    /** Admin remove qualquer usuário; os demais, só a própria conta. */
    async delete(userId, actor) {
        if (actor.role !== Roles.ADMIN && actor.id !== userId) throw new ForbiddenError();

        const deleted = await this.db.transaction(() => this.users.deleteById(userId));
        if (!deleted) throw new NotFoundError('Usuário não encontrado');
        return 'Usuário deletado';
    }
}

module.exports = { UserController };
