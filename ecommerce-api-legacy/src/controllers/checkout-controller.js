'use strict';

/**
 * Controller magro (P-08): recebe dados já validados pela rota, chama o serviço e
 * devolve o resultado. Sem SQL, sem regra de domínio, sem efeito colateral direto.
 */
class CheckoutController {
  constructor({ checkoutService }) {
    this._checkoutService = checkoutService;
  }

  async create(input) {
    const { enrollmentId } = await this._checkoutService.execute(input);
    return { msg: 'Sucesso', enrollment_id: enrollmentId };
  }
}

module.exports = { CheckoutController };
