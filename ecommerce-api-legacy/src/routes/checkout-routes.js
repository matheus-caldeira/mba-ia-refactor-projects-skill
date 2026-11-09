'use strict';

const express = require('express');
const { asyncHandler } = require('../middlewares/async-handler');
const { ValidationError } = require('../errors/app-errors');

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const CARD_NUMBER_PATTERN = /^\d{12,19}$/;

function parseCheckoutRequest(body) {
  const { usr, eml, pwd, c_id: rawCourseId, card } = body ?? {};

  if (!usr || !eml || !rawCourseId || !card) {
    throw new ValidationError('Bad Request');
  }

  const courseId = Number.parseInt(rawCourseId, 10);
  const cardNumber = String(card).replace(/[\s-]/g, '');

  if (typeof usr !== 'string' || typeof eml !== 'string' || !EMAIL_PATTERN.test(eml)) {
    throw new ValidationError('Dados do aluno inválidos');
  }
  if (!Number.isInteger(courseId) || courseId <= 0) {
    throw new ValidationError('Curso inválido');
  }
  if (!CARD_NUMBER_PATTERN.test(cardNumber)) {
    throw new ValidationError('Número de cartão inválido');
  }
  if (pwd !== undefined && typeof pwd !== 'string') {
    throw new ValidationError('Senha inválida');
  }

  return { name: usr, email: eml, password: pwd, courseId, cardNumber };
}

function buildCheckoutRoutes({ checkoutController }) {
  const router = express.Router();

  router.post(
    '/checkout',
    asyncHandler(async (req, res) => {
      const result = await checkoutController.create(parseCheckoutRequest(req.body));
      res.status(200).json(result);
    })
  );

  return router;
}

module.exports = { buildCheckoutRoutes };
