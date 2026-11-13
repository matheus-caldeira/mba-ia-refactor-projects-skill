class CheckoutController {
    constructor({ checkoutService }) {
        this.checkoutService = checkoutService;
    }

    async checkout(order) {
        const { enrollmentId } = await this.checkoutService.checkout(order);
        return { msg: 'Sucesso', enrollment_id: enrollmentId };
    }
}

module.exports = { CheckoutController };
