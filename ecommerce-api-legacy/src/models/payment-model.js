'use strict';

/** Status possíveis de um pagamento — no lugar de strings soltas pelo código. */
const PaymentStatus = Object.freeze({
  PAID: 'PAID',
  DENIED: 'DENIED',
});

/** Model de Payment. */
class PaymentModel {
  constructor(db) {
    this._db = db;
  }

  static toPublicJSON(row) {
    if (!row) return null;
    return {
      id: row.id,
      enrollment_id: row.enrollment_id,
      amount: row.amount,
      status: row.status,
    };
  }

  async create({ enrollmentId, amount, status }, executor = this._db) {
    const { lastID } = await executor.run(
      'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
      [enrollmentId, amount, status]
    );
    return lastID;
  }
}

module.exports = { PaymentModel, PaymentStatus };
