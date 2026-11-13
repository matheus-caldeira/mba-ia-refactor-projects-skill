const express = require('express');
const { Roles } = require('../domain/constants');
const { asyncHandler } = require('../middlewares/async-handler');
const { requireRole } = require('../middlewares/auth');

function adminRoutes({ reportController, authenticate }) {
    const router = express.Router();

    router.get('/api/admin/financial-report', authenticate, requireRole(Roles.ADMIN), asyncHandler(async (req, res) => {
        res.json(await reportController.financialReport());
    }));

    return router;
}

module.exports = { adminRoutes };
