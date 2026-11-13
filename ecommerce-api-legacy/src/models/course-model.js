class CourseModel {
    constructor(db) {
        this.db = db;
    }

    findActiveById(id) {
        return this.db.get('SELECT id, title, price FROM courses WHERE id = ? AND active = 1', [id]);
    }

    async count() {
        const row = await this.db.get('SELECT COUNT(*) AS total FROM courses');
        return row.total;
    }

    async create({ title, price, active }) {
        const { lastID } = await this.db.run(
            'INSERT INTO courses (title, price, active) VALUES (?, ?, ?)',
            [title, price, active ? 1 : 0],
        );
        return lastID;
    }

    /** Uma linha por matrícula (ou uma linha com nulos para curso sem matrícula). */
    listWithEnrollments() {
        return this.db.all(`
            SELECT c.id AS courseId, c.title, e.id AS enrollmentId,
                   u.name AS studentName, p.amount, p.status
            FROM courses c
            LEFT JOIN enrollments e ON e.course_id = c.id
            LEFT JOIN users u       ON u.id = e.user_id
            LEFT JOIN payments p    ON p.enrollment_id = e.id
            ORDER BY c.id, e.id
        `);
    }
}

module.exports = { CourseModel };
