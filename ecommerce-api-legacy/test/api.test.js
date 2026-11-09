'use strict';

const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');

const { createApp } = require('../src/app');
const { buildSettings } = require('../src/config/settings');

const ADMIN_TOKEN = 'token-de-teste';
const silentLogger = { log() {}, error() {} };

async function startServer(env) {
  const previous = { ...process.env };
  Object.assign(process.env, { NODE_ENV: 'test', DATABASE_PATH: ':memory:' }, env);
  for (const [key, value] of Object.entries(env)) {
    if (value === undefined) delete process.env[key];
  }
  const settings = buildSettings();
  process.env = previous;

  const { app, db } = await createApp({ settings, logger: silentLogger });
  const server = await new Promise((resolve) => {
    const listening = app.listen(0, '127.0.0.1', () => resolve(listening));
  });
  const baseUrl = `http://127.0.0.1:${server.address().port}`;
  const stop = async () => {
    await new Promise((resolve) => server.close(resolve));
    await db.close();
  };
  return { baseUrl, stop };
}

function checkout(baseUrl, body) {
  return fetch(`${baseUrl}/api/checkout`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

const adminHeaders = { Authorization: `Bearer ${ADMIN_TOKEN}` };
let server;

before(async () => {
  server = await startServer({ ADMIN_API_TOKEN: ADMIN_TOKEN });
});

after(async () => {
  await server.stop();
});

test('rotas administrativas sem token respondem 401', async () => {
  const report = await fetch(`${server.baseUrl}/api/admin/financial-report`);
  assert.equal(report.status, 401);
  const removal = await fetch(`${server.baseUrl}/api/users/1`, { method: 'DELETE' });
  assert.equal(removal.status, 401);
});

test('token errado responde 401', async () => {
  const response = await fetch(`${server.baseUrl}/api/admin/financial-report`, {
    headers: { Authorization: 'Bearer outro-token' },
  });
  assert.equal(response.status, 401);
});

test('admin com token acessa o relatório financeiro', async () => {
  const response = await fetch(`${server.baseUrl}/api/admin/financial-report`, { headers: adminHeaders });
  assert.equal(response.status, 200);
  const report = await response.json();
  assert.equal(report[0].course, 'Clean Architecture');
});

test('checkout aprovado, recusado e inválido mantêm o contrato', async () => {
  const approved = await checkout(server.baseUrl, {
    usr: 'Guilherme', eml: 'gui@fullcycle.com.br', pwd: 'senhaforte', c_id: 2, card: '4111222233334444',
  });
  assert.equal(approved.status, 200);
  assert.equal((await approved.json()).msg, 'Sucesso');

  const denied = await checkout(server.baseUrl, {
    usr: 'João', eml: 'joao@teste.com', pwd: '123', c_id: 1, card: '5111222233334444',
  });
  assert.equal(denied.status, 400);
  assert.equal(await denied.text(), 'Pagamento recusado');

  const missing = await checkout(server.baseUrl, { usr: 'X' });
  assert.equal(missing.status, 400);
});

test('checkouts concorrentes não falham', async () => {
  const responses = await Promise.all(
    Array.from({ length: 8 }, (_, i) =>
      checkout(server.baseUrl, {
        usr: `U${i}`, eml: `u${i}@x.com`, pwd: 'segredo', c_id: 1, card: '4111222233334444',
      })
    )
  );
  assert.deepEqual(responses.map((r) => r.status), Array(8).fill(200));
});

test('exclusão de usuário exige admin e responde 404 para id inexistente', async () => {
  const missing = await fetch(`${server.baseUrl}/api/users/999`, { method: 'DELETE', headers: adminHeaders });
  assert.equal(missing.status, 404);
});

test('sem ADMIN_API_TOKEN configurado as rotas administrativas ficam desabilitadas (403)', async () => {
  const unconfigured = await startServer({ ADMIN_API_TOKEN: undefined });
  try {
    const response = await fetch(`${unconfigured.baseUrl}/api/admin/financial-report`, {
      headers: { Authorization: 'Bearer dev-admin-token' },
    });
    assert.equal(response.status, 403);
  } finally {
    await unconfigured.stop();
  }
});
