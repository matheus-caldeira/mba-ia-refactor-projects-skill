'use strict';

const express = require('express');

const { Database } = require('./database/connection');
const { runMigrations } = require('./database/migrations');
const { runSeed } = require('./database/seed');

const { UserModel } = require('./models/user-model');
const { CourseModel } = require('./models/course-model');
const { EnrollmentModel } = require('./models/enrollment-model');
const { PaymentModel } = require('./models/payment-model');
const { AuditLogModel } = require('./models/audit-log-model');

const { PaymentGateway } = require('./gateways/payment-gateway');
const { PasswordHasher } = require('./security/password-hasher');

const { CheckoutService } = require('./services/checkout-service');
const { FinancialReportService } = require('./services/financial-report-service');
const { UserService } = require('./services/user-service');

const { CheckoutController } = require('./controllers/checkout-controller');
const { AdminController } = require('./controllers/admin-controller');
const { UserController } = require('./controllers/user-controller');

const { buildCheckoutRoutes } = require('./routes/checkout-routes');
const { buildAdminRoutes } = require('./routes/admin-routes');
const { buildUserRoutes } = require('./routes/user-routes');

const { requireAdmin } = require('./middlewares/admin-auth');
const { errorHandler, notFoundHandler } = require('./middlewares/error-handler');

/**
 * Composition root (application factory).
 *
 * Este arquivo apenas MONTA a aplicação: carrega config, instância as dependências
 * concretas, injeta nos serviços/controllers e registra rotas e middlewares.
 * Nenhuma rota declarada inline, nenhuma regra de negócio, nenhum SQL, nenhum segredo.
 *
 * Devolver o `app` sem escutar porta permite criar a aplicação em teste com
 * configuração própria, sem subir servidor real.
 */
async function createApp({ settings, logger = console }) {
  const db = await Database.open(settings.database.path);
  await db.run('PRAGMA foreign_keys = ON');
  await runMigrations(db);

  // Dependências concretas
  const passwordHasher = new PasswordHasher();
  const paymentGateway = new PaymentGateway({
    apiKey: settings.payment.gatewayKey,
    logger,
  });

  await runSeed(db, passwordHasher);

  // Models
  const userModel = new UserModel(db);
  const courseModel = new CourseModel(db);
  const enrollmentModel = new EnrollmentModel(db);
  const paymentModel = new PaymentModel(db);
  const auditLogModel = new AuditLogModel(db);

  // Services
  const checkoutService = new CheckoutService({
    db,
    userModel,
    courseModel,
    enrollmentModel,
    paymentModel,
    auditLogModel,
    paymentGateway,
    passwordHasher,
  });
  const financialReportService = new FinancialReportService({ db });
  const userService = new UserService({ db, userModel, auditLogModel });

  // Controllers
  const checkoutController = new CheckoutController({ checkoutService });
  const adminController = new AdminController({ financialReportService });
  const userController = new UserController({ userService });

  // Aplicacao
  const app = express();
  app.use(express.json());

  const requireAdminMiddleware = requireAdmin({ adminToken: settings.admin.apiToken });

  app.use('/api', buildCheckoutRoutes({ checkoutController }));
  app.use('/api', buildAdminRoutes({ adminController, requireAdminMiddleware }));
  app.use('/api', buildUserRoutes({ userController, requireAdminMiddleware }));

  // Error handling por último, para capturar tudo.
  app.use(notFoundHandler);
  app.use(errorHandler(logger));

  return { app, db };
}

module.exports = { createApp };
