const SCHEMA = `
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'student' CHECK (role IN ('student', 'admin'))
);
CREATE TABLE IF NOT EXISTS courses (
    id     INTEGER PRIMARY KEY,
    title  TEXT NOT NULL,
    price  REAL NOT NULL CHECK (price >= 0),
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
    status        TEXT NOT NULL CHECK (status IN ('PAID', 'DENIED'))
);
CREATE TABLE IF NOT EXISTS audit_logs (
    id         INTEGER PRIMARY KEY,
    action     TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT (datetime('now'))
);
`;

function applySchema(db) {
    return db.exec(SCHEMA);
}

module.exports = { applySchema };
