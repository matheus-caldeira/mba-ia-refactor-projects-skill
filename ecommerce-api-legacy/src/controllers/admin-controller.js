'use strict';

/** Controller do relatório administrativo. Apenas orquestra. */
class AdminController {
  constructor({ financialReportService }) {
    this._financialReportService = financialReportService;
  }

  financialReport() {
    return this._financialReportService.generate();
  }
}

module.exports = { AdminController };
