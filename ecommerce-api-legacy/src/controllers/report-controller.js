class ReportController {
    constructor({ financialReportService }) {
        this.financialReportService = financialReportService;
    }

    financialReport() {
        return this.financialReportService.build();
    }
}

module.exports = { ReportController };
