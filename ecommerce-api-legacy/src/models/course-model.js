'use strict';

/** Model de Course: entidade + acesso a dados. Sem HTTP, queries parametrizadas. */
class CourseModel {
  constructor(db) {
    this._db = db;
  }

  static toPublicJSON(row) {
    if (!row) return null;
    return { id: row.id, title: row.title, price: row.price, active: row.active === 1 };
  }

  findActiveById(id, executor = this._db) {
    return executor.get(
      'SELECT id, title, price, active FROM courses WHERE id = ? AND active = 1',
      [id]
    );
  }

  listAll(executor = this._db) {
    return executor.all('SELECT id, title, price, active FROM courses ORDER BY id');
  }
}

module.exports = { CourseModel };
