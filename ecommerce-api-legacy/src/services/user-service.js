'use strict';

/**
 * Regras de usuário que cruzam persistencia e auditoria.
 *
 * A exclusão agora e transacional e apoiada nas FKs com ON DELETE CASCADE: as
 * matrículas e pagamentos dependentes são removidos junto, em vez de ficarem
 * órfãos no banco como no código original (AP-13).
 */
class UserService {
  constructor({ db, userModel, auditLogModel }) {
    this._db = db;
    this._users = userModel;
    this._auditLogs = auditLogModel;
  }

  /** @returns {{ deleted: boolean }} */
  async deleteUser(userId) {
    return this._db.transaction(async (tx) => {
      const changes = await this._users.deleteById(userId, tx);
      if (changes > 0) {
        await this._auditLogs.record(`Usuário ${userId} removido`, tx);
      }
      return { deleted: changes > 0 };
    });
  }
}

module.exports = { UserService };
