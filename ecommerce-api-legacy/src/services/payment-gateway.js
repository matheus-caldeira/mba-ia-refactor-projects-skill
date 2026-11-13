const { PaymentStatus } = require('../domain/constants');

// Regra da simulação do gateway: cartões iniciados por este prefixo são aprovados.
const APPROVED_CARD_PREFIX = '4';

/**
 * Gateway simulado. Nunca registra o número do cartão nem a chave em log.
 * Para um gateway real, implemente a mesma interface charge() e injete no app.
 */
class SimulatedPaymentGateway {
    constructor({ apiKey }) {
        this.apiKey = apiKey;
    }

    async charge({ cardNumber }) {
        return cardNumber.startsWith(APPROVED_CARD_PREFIX) ? PaymentStatus.PAID : PaymentStatus.DENIED;
    }
}

module.exports = { SimulatedPaymentGateway, APPROVED_CARD_PREFIX };
