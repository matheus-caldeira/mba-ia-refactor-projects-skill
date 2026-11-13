const PUBLIC_COLUMNS = 'id, name, email, role';

class UserModel {
    constructor(db) {
        this.db = db;
    }

    findById(id) {
        return this.db.get(`SELECT ${PUBLIC_COLUMNS} FROM users WHERE id = ?`, [id]);
    }

    findByEmail(email) {
        return this.db.get(`SELECT ${PUBLIC_COLUMNS} FROM users WHERE email = ?`, [email]);
    }

    /** Único método que devolve o hash — usado só na verificação de credenciais. */
    findCredentialsByEmail(email) {
        return this.db.get('SELECT id, role, password_hash AS passwordHash FROM users WHERE email = ?', [email]);
    }

    async create({ name, email, passwordHash, role }) {
        const { lastID } = await this.db.run(
            'INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)',
            [name, email, passwordHash, role],
        );
        return lastID;
    }

    /** Matrículas e pagamentos do usuário saem junto (ON DELETE CASCADE). */
    async deleteById(id) {
        const { changes } = await this.db.run('DELETE FROM users WHERE id = ?', [id]);
        return changes > 0;
    }
}

module.exports = { UserModel };
