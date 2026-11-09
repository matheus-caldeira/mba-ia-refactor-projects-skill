'use strict';

const { buildSettings } = require('./config/settings');
const { createApp } = require('./app');

/**
 * Entry point do processo: le a configuração, monta a app e sobe o servidor.
 * Falha de configuração derruba o boot com mensagem clara, em vez de subir
 * a aplicação em estado inseguro.
 */
async function main() {
  const settings = buildSettings();
  const { app, db } = await createApp({ settings });

  const server = app.listen(settings.port, () => {
    console.log(`LMS API rodando na porta ${settings.port} (env: ${settings.nodeEnv})`);
  });

  const shutdown = async (signal) => {
    console.log(`\n[${signal}] encerrando...`);
    server.close(async () => {
      try {
        await db.close();
      } finally {
        process.exit(0);
      }
    });
  };

  process.on('SIGINT', () => shutdown('SIGINT'));
  process.on('SIGTERM', () => shutdown('SIGTERM'));
}

main().catch((error) => {
  console.error('Falha ao iniciar a aplicação:', error.message);
  process.exit(1);
});
