const { PaymentStatus, Roles } = require('../domain/constants');
const { NotFoundError, PaymentDeniedError } = require('../domain/errors');

/**
 * Fluxo de compra: valida o curso → cobra o cartão → (cria o aluno se não existir)
 * → matricula → registra pagamento → audita. Todas as escritas numa transação.
 */
class CheckoutService {
    constructor({ db, users, courses, enrollments, payments, auditLogs, paymentGateway, passwordHasher }) {
        Object.assign(this, { db, users, courses, enrollments, payments, auditLogs, paymentGateway, passwordHasher });
    }

    async checkout({ name, email, password, courseId, cardNumber }) {
        const course = await this.courses.findActiveById(courseId);
        if (!course) throw new NotFoundError('Curso não encontrado');

        const status = await this.paymentGateway.charge({ cardNumber, amount: course.price });
        if (status !== PaymentStatus.PAID) throw new PaymentDeniedError();

        // Hash calculado fora da transação para não segurar a fila de escrita.
        const preHashed = (await this.users.findByEmail(email)) ? null : await this.hashPassword(password);

        return this.db.transaction(async () => {
            const existing = await this.users.findByEmail(email);
            const userId = existing
                ? existing.id
                : await this.users.create({
                    name,
                    email,
                    passwordHash: preHashed ?? await this.hashPassword(password),
                    role: Roles.STUDENT,
                });

            const enrollmentId = await this.enrollments.create({ userId, courseId: course.id });
            await this.payments.create({ enrollmentId, amount: course.price, status });
            await this.auditLogs.record(`Checkout curso ${course.id} por ${userId}`);
            return { enrollmentId, userId };
        });
    }

    /** Sem senha informada, a conta recebe uma senha aleatória (nenhuma senha padrão conhecida). */
    hashPassword(password) {
        return this.passwordHasher.hash(password || this.passwordHasher.randomPassword());
    }
}

module.exports = { CheckoutService };
