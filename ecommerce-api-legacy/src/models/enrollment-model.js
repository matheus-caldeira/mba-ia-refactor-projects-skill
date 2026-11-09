'use strict';

/** Model de Enrollment. Aceita um executor (a transação) para participar do Unit of Work. */
class EnrollmentModel {
  constructor(db) {
    this._db = db;
  }

  static toPublicJSON(row) {
    if (!row) return null;
    return { id: row.id, user_id: row.user_id, course_id: row.course_id };
  }

  async create({ userId, courseId }, executor = this._db) {
    const { lastID } = await executor.run(
      'INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)',
      [userId, courseId]
    );
    return lastID;
  }
}

module.exports = { EnrollmentModel };
