'use strict';

/** Model de AuditLog. */
class AuditLogModel {
  constructor(db) {
    this._db = db;
  }

  async record(action, executor = this._db) {
    const { lastID } = await executor.run(
      "INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))",
      [action]
    );
    return lastID;
  }
}

module.exports = { AuditLogModel };
