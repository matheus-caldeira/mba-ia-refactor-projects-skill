'use strict';

const { PaymentStatus } = require('../models/payment-model');

/**
 * Gateway de pagamento como dependência INJETADA (AP-07), não código solto dentro
 * do handler. Permite substituir por um dublê em teste sem tocar na regra.
 *
 * Correcoes de segurança em relação ao original (achado #5 / AP-06):
 * - O numero do cartão (PAN) NUNCA e logado — apenas os 4 últimos dígitos.
 * - A chave do gateway NUNCA e logada.
 *
 * A "autorização" continua sendo a mesma simulação do código original (cartão
 * iniciado em "4" e aprovado), para preservar o comportamento observavel dos
 * endpoints. Uma integração real com tokenização substituiria está classe sem
 * que nenhuma outra camada precise mudar.
 */
class PaymentGateway {
  constructor({ apiKey, logger = console }) {
    this._apiKey = apiKey;
    this._logger = logger;
  }

  static maskCardNumber(cardNumber) {
    const digits = String(cardNumber ?? '').replace(/\D/g, '');
    return digits.length <= 4 ? '****' : `****${digits.slice(-4)}`;
  }

  /**
   * @returns {{ status: string, transactionId: string }}
   */
  authorize({ cardNumber, amount }) {
    const masked = PaymentGateway.maskCardNumber(cardNumber);
    const transactionId = `txn_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;

    this._logger.log(
      `[payment] autorização solicitada cartão=${masked} valor=${amount} txn=${transactionId}`
    );

    const approved = String(cardNumber ?? '').startsWith('4');
    return {
      status: approved ? PaymentStatus.PAID : PaymentStatus.DENIED,
      transactionId,
    };
  }
}

module.exports = { PaymentGateway };
