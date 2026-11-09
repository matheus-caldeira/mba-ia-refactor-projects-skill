'use strict';

/**
 * Model de User: entidade + acesso a dados (P-04).
 *
 * Recebe a conexão por construtor (injeção de dependência). Não conhece HTTP:
 * sem req, sem res, sem status code. Todas as queries parametrizadas.
 */
class UserModel {
  constructor(db) {
    this._db = db;
  }

  /**
   * Serializacao por LISTA DE PERMISSÃO, nunca espelho da tabela.
   * O campo `pass` jamais aparece aqui, mesmo que a linha o traga.
   */
  static toPublicJSON(row) {
    if (!row) return null;
    return { id: row.id, name: row.name, email: row.email };
  }

  findByEmail(email, executor = this._db) {
    return executor.get('SELECT id, name, email, pass FROM users WHERE email = ?', [email]);
  }

  findById(id, executor = this._db) {
    return executor.get('SELECT id, name, email FROM users WHERE id = ?', [id]);
  }

  async create({ name, email, passwordHash }, executor = this._db) {
    const { lastID } = await executor.run(
      'INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
      [name, email, passwordHash]
    );
    return lastID;
  }

  /**
   * Remove o usuário. As FKs com ON DELETE CASCADE cuidam de matrículas e
   * pagamentos dependentes — não ha mais órfãos (AP-13).
   * Retorna quantas linhas foram afetadas.
   */
  async deleteById(id, executor = this._db) {
    const { changes } = await executor.run('DELETE FROM users WHERE id = ?', [id]);
    return changes;
  }
}

module.exports = { UserModel };
