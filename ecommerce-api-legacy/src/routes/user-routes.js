'use strict';

const express = require('express');
const { asyncHandler } = require('../middlewares/async-handler');
const { ValidationError, NotFoundError } = require('../errors/app-errors');

/**
 * Rotas de usuário. A exclusão e operação privilegiada e destrutiva: passa a
 * exigir autenticação administrativa (AP-05).
 */
function buildUserRoutes({ userController, requireAdminMiddleware }) {
  const router = express.Router();

  router.delete(
    '/users/:id',
    requireAdminMiddleware,
    asyncHandler(async (req, res) => {
      const userId = Number.parseInt(req.params.id, 10);
      if (!Number.isInteger(userId) || userId <= 0) {
        throw new ValidationError('Id de usuário inválido');
      }

      const { deleted } = await userController.remove(userId);
      if (!deleted) {
        throw new NotFoundError('Usuário não encontrado');
      }

      res.status(200).send('Usuário deletado, junto com suas matrículas e pagamentos.');
    })
  );

  return router;
}

module.exports = { buildUserRoutes };
