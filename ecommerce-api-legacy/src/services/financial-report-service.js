const { PaymentStatus } = require('../domain/constants');

const UNKNOWN_STUDENT = 'Unknown';

/** Receita por curso e o que cada aluno pagou — uma única consulta, agregada em memória. */
class FinancialReportService {
    constructor({ courses }) {
        this.courses = courses;
    }

    async build() {
        const rows = await this.courses.listWithEnrollments();
        const byCourse = new Map();

        for (const row of rows) {
            if (!byCourse.has(row.courseId)) {
                byCourse.set(row.courseId, { course: row.title, revenue: 0, students: [] });
            }
            if (row.enrollmentId === null) continue;

            const entry = byCourse.get(row.courseId);
            if (row.status === PaymentStatus.PAID) entry.revenue += row.amount;
            entry.students.push({
                student: row.studentName ?? UNKNOWN_STUDENT,
                paid: row.amount ?? 0,
            });
        }

        return [...byCourse.values()];
    }
}

module.exports = { FinancialReportService };
