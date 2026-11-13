const express = require('express');
const { asyncHandler } = require('../middlewares/async-handler');
const { validateId } = require('../validators/request-validators');

function userRoutes({ userController, authenticate }) {
    const router = express.Router();

    router.delete('/api/users/:id', authenticate, asyncHandler(async (req, res) => {
        res.send(await userController.delete(validateId(req.params.id), req.user));
    }));

    return router;
}

module.exports = { userRoutes };
