'use strict';

/**
 * SO o DDL (P-04). Separado da conexão e do seed.
 *
 * Diferença em relação ao schema original: as FOREIGN KEYs agora existem e usam
 * ON DELETE CASCADE, o que resolve a raiz do AP-13 — apagar um usuário deixava
 * matrículas e pagamentos órfãos no banco.
 */

const SCHEMA = `
  PRAGMA foreign_keys = ON;

  CREATE TABLE IF NOT EXISTS users (
    id    INTEGER PRIMARY KEY,
    name  TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    pass  TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS courses (
    id     INTEGER PRIMARY KEY,
    title  TEXT NOT NULL,
    price  REAL NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
  );

  CREATE TABLE IF NOT EXISTS enrollments (
    id        INTEGER PRIMARY KEY,
    user_id   INTEGER NOT NULL REFERENCES users(id)   ON DELETE CASCADE,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE
  );

  CREATE TABLE IF NOT EXISTS payments (
    id            INTEGER PRIMARY KEY,
    enrollment_id INTEGER NOT NULL REFERENCES enrollments(id) ON DELETE CASCADE,
    amount        REAL NOT NULL,
    status        TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS audit_logs (
    id         INTEGER PRIMARY KEY,
    action     TEXT NOT NULL,
    created_at DATETIME NOT NULL
  );
`;

async function runMigrations(db) {
  await db.exec(SCHEMA);
}

module.exports = { runMigrations };
