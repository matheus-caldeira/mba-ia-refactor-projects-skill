'use strict';

const { PaymentStatus } = require('../models/payment-model');

/**
 * Relatório financeiro (P-10).
 *
 * O original fazia N+1 com callbacks aninhados e contadores manuais
 * (coursesPending/enrPending): uma query em courses, uma em enrollments por curso,
 * e duas por matrícula (users e payments). Alem de lento, qualquer erro em um
 * callback intermediário fazia a resposta nunca ser enviada e a requisição pendurar.
 *
 * Agora e UMA query com LEFT JOIN e a agregação acontece em memória.
 *
 * O formato de saída e idêntico ao original — inclusive a ordem dos cursos
 * (por courses.id), a ordem dos alunos (por enrollments.id), o aluno 'Unknown'
 * quando o usuário não existe mais, e `revenue` somando apenas pagamentos PAID.
 */
class FinancialReportService {
  constructor({ db }) {
    this._db = db;
  }

  async generate() {
    const rows = await this._db.all(`
      SELECT
        c.id            AS course_id,
        c.title         AS course_title,
        e.id            AS enrollment_id,
        u.name          AS student_name,
        p.amount        AS payment_amount,
        p.status        AS payment_status
      FROM courses c
      LEFT JOIN enrollments e ON e.course_id = c.id
      LEFT JOIN users u       ON u.id = e.user_id
      LEFT JOIN payments p    ON p.enrollment_id = e.id
      ORDER BY c.id, e.id
    `);

    const byCourse = new Map();

    for (const row of rows) {
      if (!byCourse.has(row.course_id)) {
        byCourse.set(row.course_id, {
          course: row.course_title,
          revenue: 0,
          students: [],
        });
      }

      // LEFT JOIN sem matrícula produz uma linha com enrollment_id nulo:
      // o curso aparece no relatório com lista de alunos vazia.
      if (row.enrollment_id === null) continue;

      const courseData = byCourse.get(row.course_id);

      if (row.payment_status === PaymentStatus.PAID) {
        courseData.revenue += row.payment_amount;
      }

      courseData.students.push({
        student: row.student_name ?? 'Unknown',
        paid: row.payment_amount ?? 0,
      });
    }

    return [...byCourse.values()];
  }
}

module.exports = { FinancialReportService };
