'use strict';

const sqlite3 = require('sqlite3');

/**
 * Conexão com o banco — SO conexão (P-04/P-07).
 *
 * A instância concreta e criada aqui e INJETADA nos models pelo composition root,
 * nunca instanciada dentro de uma classe de domínio. Isso permite trocar por um
 * banco de teste (`:memory:`) sem tocar na regra de negócio.
 *
 * Envolve a API de callbacks do sqlite3 em promises para permitir async/await e
 * transações legíveis, eliminando a pirâmide de callbacks do código original.
 */
class Database {
  constructor(sqliteDb) {
    this._db = sqliteDb;
    this._transactionQueue = Promise.resolve();
  }

  static open(path) {
    return new Promise((resolve, reject) => {
      const db = new sqlite3.Database(path, (err) => {
        if (err) return reject(err);
        resolve(new Database(db));
      });
    });
  }

  /** Executa uma escrita. Resolve com { lastID, changes }. */
  run(sql, params = []) {
    return new Promise((resolve, reject) => {
      this._db.run(sql, params, function runCallback(err) {
        if (err) return reject(err);
        resolve({ lastID: this.lastID, changes: this.changes });
      });
    });
  }

  /** Lê uma única linha (ou undefined). */
  get(sql, params = []) {
    return new Promise((resolve, reject) => {
      this._db.get(sql, params, (err, row) => {
        if (err) return reject(err);
        resolve(row);
      });
    });
  }

  /** Lê todas as linhas. */
  all(sql, params = []) {
    return new Promise((resolve, reject) => {
      this._db.all(sql, params, (err, rows) => {
        if (err) return reject(err);
        resolve(rows);
      });
    });
  }

  /** Executa um script com múltiplos statements. */
  exec(sql) {
    return new Promise((resolve, reject) => {
      this._db.exec(sql, (err) => {
        if (err) return reject(err);
        resolve();
      });
    });
  }

  /**
   * Unit of Work (P-07/AP-13): ou tudo acontece, ou nada.
   * Recebe uma função async e garante COMMIT no sucesso e ROLLBACK em qualquer erro.
   */
  transaction(work) {
    const pending = this._transactionQueue.then(() => this._runTransaction(work));
    this._transactionQueue = pending.catch(() => undefined);
    return pending;
  }

  async _runTransaction(work) {
    await this.run('BEGIN TRANSACTION');
    try {
      const result = await work(this);
      await this.run('COMMIT');
      return result;
    } catch (error) {
      try {
        await this.run('ROLLBACK');
      } catch {
        // Falha no rollback não deve mascarar o erro original.
      }
      throw error;
    }
  }

  close() {
    return new Promise((resolve, reject) => {
      this._db.close((err) => (err ? reject(err) : resolve()));
    });
  }
}

module.exports = { Database };
