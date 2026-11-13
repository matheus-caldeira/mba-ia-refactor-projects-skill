const express = require('express');
const { loadSettings } = require('./config/settings');
const { Database } = require('./database/connection');
const { applySchema } = require('./database/schema');
const { seed } = require('./database/seed');
const { UserModel } = require('./models/user-model');
const { CourseModel } = require('./models/course-model');
const { EnrollmentModel } = require('./models/enrollment-model');
const { PaymentModel } = require('./models/payment-model');
const { AuditLogModel } = require('./models/audit-log-model');
const { PasswordHasher } = require('./services/password-hasher');
const { TokenService } = require('./services/token-service');
const { SimulatedPaymentGateway } = require('./services/payment-gateway');
const { CheckoutService } = require('./services/checkout-service');
const { FinancialReportService } = require('./services/financial-report-service');
const { CheckoutController } = require('./controllers/checkout-controller');
const { ReportController } = require('./controllers/report-controller');
const { UserController } = require('./controllers/user-controller');
const { AuthController } = require('./controllers/auth-controller');
const { authenticate } = require('./middlewares/auth');
const { errorHandler } = require('./middlewares/error-handler');
const { checkoutRoutes } = require('./routes/checkout-routes');
const { authRoutes } = require('./routes/auth-routes');
const { adminRoutes } = require('./routes/admin-routes');
const { userRoutes } = require('./routes/user-routes');

/** Composition root: monta dependências e rotas. Não sobe servidor (testável). */
async function createApp(settings) {
    const db = await Database.open(settings.dbPath);
    await applySchema(db);

    const users = new UserModel(db);
    const courses = new CourseModel(db);
    const enrollments = new EnrollmentModel(db);
    const payments = new PaymentModel(db);
    const auditLogs = new AuditLogModel(db);
    const passwordHasher = new PasswordHasher();
    const tokenService = new TokenService({ secret: settings.authSecret, ttlSeconds: settings.tokenTtlSeconds });
    const paymentGateway = new SimulatedPaymentGateway({ apiKey: settings.paymentGatewayKey });

    await seed(db, { users, courses, enrollments, payments, passwordHasher, admin: settings.admin });

    const checkoutService = new CheckoutService({ db, users, courses, enrollments, payments, auditLogs, paymentGateway, passwordHasher });
    const financialReportService = new FinancialReportService({ courses });

    const checkoutController = new CheckoutController({ checkoutService });
    const reportController = new ReportController({ financialReportService });
    const userController = new UserController({ db, users });
    const authController = new AuthController({ users, passwordHasher, tokenService });
    const requireAuth = authenticate({ tokenService, users });

    const app = express();
    app.disable('x-powered-by');
    app.use(express.json());
    app.use(checkoutRoutes({ checkoutController }));
    app.use(authRoutes({ authController }));
    app.use(adminRoutes({ reportController, authenticate: requireAuth }));
    app.use(userRoutes({ userController, authenticate: requireAuth }));
    app.use(errorHandler);

    return { app, db };
}

async function start() {
    const settings = loadSettings();
    const { app, db } = await createApp(settings);

    const server = app.listen(settings.port, settings.host, () => {
        console.log(`LMS API rodando em http://${settings.host}:${settings.port}`);
    });

    const shutdown = () => server.close(() => db.close().finally(() => process.exit(0)));
    process.on('SIGINT', shutdown);
    process.on('SIGTERM', shutdown);
}

if (require.main === module) {
    start().catch((error) => {
        console.error(`Falha ao iniciar: ${error.message}`);
        process.exit(1);
    });
}

module.exports = { createApp };
