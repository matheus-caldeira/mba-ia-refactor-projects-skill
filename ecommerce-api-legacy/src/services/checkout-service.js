'use strict';

const crypto = require('node:crypto');
const { NotFoundError, PaymentDeclinedError } = require('../errors/app-errors');
const { PaymentStatus } = require('../models/payment-model');

/**
 * Regra de negócio do checkout (P-08). Extraida por inteiro do handler HTTP.
 *
 * Não conhece Express: não recebe req/res, não devolve status code. Sinaliza
 * falhas de domínio lancando erros tipados, que o handler central traduz.
 *
 * Todas as dependências são injetadas pelo construtor — e isso que permite testar
 * o fluxo com dublês, sem subir servidor HTTP nem banco real.
 */
class CheckoutService {
  constructor({
    db,
    userModel,
    courseModel,
    enrollmentModel,
    paymentModel,
    auditLogModel,
    paymentGateway,
    passwordHasher,
  }) {
    this._db = db;
    this._users = userModel;
    this._courses = courseModel;
    this._enrollments = enrollmentModel;
    this._payments = paymentModel;
    this._auditLogs = auditLogModel;
    this._gateway = paymentGateway;
    this._hasher = passwordHasher;
  }

  static generateRandomPassword() {
    return crypto.randomBytes(24).toString('base64url');
  }

  /**
   * Executa o checkout completo: encontra/cria o usuário, autoriza o pagamento,
   * matrícula, registra o pagamento e audita.
   *
   * Todas as escritas acontecem dentro de UMA transação (AP-13): se qualquer
   * passo falhar, nada e persistido — no original, uma falha no insert de
   * pagamento deixava a matrícula gravada sem pagamento correspondente.
   *
   * @returns {{ enrollmentId: number }}
   */
  async execute({ name, email, password, courseId, cardNumber }) {
    const course = await this._courses.findActiveById(courseId);
    if (!course) {
      throw new NotFoundError('Curso não encontrado');
    }

    // A autorização ocorre ANTES da transação: e uma chamada externa, e manter
    // uma transação aberta durante I/O de rede seguraria locks do banco.
    const authorization = this._gateway.authorize({
      cardNumber,
      amount: course.price,
    });

    if (authorization.status === PaymentStatus.DENIED) {
      throw new PaymentDeclinedError('Pagamento recusado');
    }

    const existingUser = await this._users.findByEmail(email);
    const passwordHash = existingUser
      ? null
      : await this._hasher.hash(password || CheckoutService.generateRandomPassword());

    return this._db.transaction(async (tx) => {
      let userId;
      if (existingUser) {
        userId = existingUser.id;
      } else {
        userId = await this._users.create({ name, email, passwordHash }, tx);
      }

      const enrollmentId = await this._enrollments.create({ userId, courseId }, tx);

      await this._payments.create(
        {
          enrollmentId,
          amount: course.price,
          status: authorization.status,
        },
        tx
      );

      await this._auditLogs.record(`Checkout curso ${courseId} por ${userId}`, tx);

      return { enrollmentId };
    });
  }
}

module.exports = { CheckoutService };
