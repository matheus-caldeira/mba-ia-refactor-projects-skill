const sqlite3 = require('sqlite3');

/**
 * Wrapper em Promise sobre o driver sqlite3 (callback).
 * Uma única conexão atende todas as requisições, então as transações são
 * serializadas numa fila: dois BEGIN intercalados na mesma conexão falhariam
 * ("cannot start a transaction within a transaction").
 * Toda escrita da aplicação passa por transaction().
 */
class Database {
    constructor(connection) {
        this.connection = connection;
        this.queue = Promise.resolve();
    }

    static open(filename) {
        return new Promise((resolve, reject) => {
            const connection = new sqlite3.Database(filename, (err) => {
                if (err) return reject(err);
                const db = new Database(connection);
                db.exec('PRAGMA foreign_keys = ON').then(() => resolve(db), reject);
            });
        });
    }

    run(sql, params = []) {
        return new Promise((resolve, reject) => {
            this.connection.run(sql, params, function onRun(err) {
                if (err) return reject(err);
                resolve({ lastID: this.lastID, changes: this.changes });
            });
        });
    }

    get(sql, params = []) {
        return new Promise((resolve, reject) => {
            this.connection.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
        });
    }

    all(sql, params = []) {
        return new Promise((resolve, reject) => {
            this.connection.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)));
        });
    }

    exec(sql) {
        return new Promise((resolve, reject) => {
            this.connection.exec(sql, (err) => (err ? reject(err) : resolve()));
        });
    }

    transaction(work) {
        const pending = this.queue.then(() => this.runTransaction(work));
        this.queue = pending.catch(() => undefined);
        return pending;
    }

    async runTransaction(work) {
        await this.run('BEGIN IMMEDIATE TRANSACTION');
        try {
            const result = await work(this);
            await this.run('COMMIT');
            return result;
        } catch (error) {
            await this.run('ROLLBACK');
            throw error;
        }
    }

    close() {
        return new Promise((resolve, reject) => {
            this.connection.close((err) => (err ? reject(err) : resolve()));
        });
    }
}

module.exports = { Database };
