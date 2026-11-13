const express = require('express');
const { asyncHandler } = require('../middlewares/async-handler');
const { validateLogin } = require('../validators/request-validators');

function authRoutes({ authController }) {
    const router = express.Router();

    router.post('/api/auth/login', asyncHandler(async (req, res) => {
        res.json(await authController.login(validateLogin(req.body)));
    }));

    return router;
}

module.exports = { authRoutes };
