'use strict';

const express = require('express');
const { asyncHandler } = require('../middlewares/async-handler');

/**
 * Rotas administrativas — todas atrás do middleware de autenticação (AP-05).
 */
function buildAdminRoutes({ adminController, requireAdminMiddleware }) {
  const router = express.Router();

  router.get(
    '/admin/financial-report',
    requireAdminMiddleware,
    asyncHandler(async (req, res) => {
      const report = await adminController.financialReport();
      res.status(200).json(report);
    })
  );

  return router;
}

module.exports = { buildAdminRoutes };
