const { ValidationError } = require('../domain/errors');

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const CARD_PATTERN = /^\d{12,19}$/;
const CARD_SEPARATORS = /[\s-]/g;

function nonEmptyString(value) {
    return typeof value === 'string' && value.trim().length > 0;
}

function parsePositiveInt(value) {
    const number = typeof value === 'string' && /^\d+$/.test(value) ? Number(value) : value;
    return Number.isInteger(number) && number > 0 ? number : null;
}

/** Contrato HTTP: { usr, eml, pwd?, c_id, card }. Devolve os dados com nomes de domínio. */
function validateCheckout(body) {
    const { usr, eml, pwd, c_id: rawCourseId, card } = body || {};

    if (!nonEmptyString(usr) || !nonEmptyString(eml) || rawCourseId == null || card == null) {
        throw new ValidationError('Bad Request');
    }
    if (!EMAIL_PATTERN.test(eml.trim())) throw new ValidationError('E-mail inválido');

    const courseId = parsePositiveInt(rawCourseId);
    if (!courseId) throw new ValidationError('c_id deve ser um inteiro positivo');

    const cardNumber = typeof card === 'string' ? card.replace(CARD_SEPARATORS, '') : '';
    if (!CARD_PATTERN.test(cardNumber)) throw new ValidationError('Número de cartão inválido');

    if (pwd != null && typeof pwd !== 'string') throw new ValidationError('pwd deve ser texto');

    return { name: usr.trim(), email: eml.trim().toLowerCase(), password: pwd || null, courseId, cardNumber };
}

function validateLogin(body) {
    const { email, password } = body || {};
    if (!nonEmptyString(email) || !nonEmptyString(password)) {
        throw new ValidationError('email e password são obrigatórios');
    }
    return { email: email.trim().toLowerCase(), password };
}

function validateId(value) {
    const id = parsePositiveInt(value);
    if (!id) throw new ValidationError('id deve ser um inteiro positivo');
    return id;
}

module.exports = { validateCheckout, validateLogin, validateId };
