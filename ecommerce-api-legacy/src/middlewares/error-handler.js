const { AppError } = require('../domain/errors');

/** Handler único: erros de domínio viram seu status; o resto vira 500 sem detalhe interno. */
// eslint-disable-next-line no-unused-vars
function errorHandler(err, req, res, next) {
    if (err instanceof AppError) {
        return res.status(err.statusCode).json({ error: err.message });
    }
    if (err.type === 'entity.parse.failed') {
        return res.status(400).json({ error: 'JSON inválido' });
    }
    console.error(`[erro] ${req.method} ${req.originalUrl}`, err);
    return res.status(500).json({ error: 'Erro interno' });
}

module.exports = { errorHandler };
