const { Roles, PaymentStatus } = require('../domain/constants');

/**
 * Dados iniciais. Roda só em banco vazio (idempotente para DB_PATH em arquivo).
 * Nenhuma conta do seed tem senha literal: o aluno de exemplo recebe senha
 * aleatória e o admin vem da configuração (obrigatória em produção).
 */
async function seed(db, { users, courses, enrollments, payments, passwordHasher, admin }) {
    await db.transaction(async () => {
        if ((await courses.count()) === 0) {
            const studentId = await users.create({
                name: 'Leonan',
                email: 'leonan@fullcycle.com.br',
                passwordHash: await passwordHasher.hash(passwordHasher.randomPassword()),
                role: Roles.STUDENT,
            });
            const cleanArchId = await courses.create({ title: 'Clean Architecture', price: 997.0, active: true });
            await courses.create({ title: 'Docker', price: 497.0, active: true });
            const enrollmentId = await enrollments.create({ userId: studentId, courseId: cleanArchId });
            await payments.create({ enrollmentId, amount: 997.0, status: PaymentStatus.PAID });
        }

        if (!(await users.findByEmail(admin.email))) {
            await users.create({
                name: admin.name,
                email: admin.email,
                passwordHash: await passwordHasher.hash(admin.password),
                role: Roles.ADMIN,
            });
        }
    });
}

module.exports = { seed };
