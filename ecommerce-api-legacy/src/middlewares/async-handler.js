/** Express 4 não encaminha rejeições de handlers async: este wrapper leva o erro ao error handler. */
const asyncHandler = (handler) => (req, res, next) => Promise.resolve(handler(req, res, next)).catch(next);

module.exports = { asyncHandler };
