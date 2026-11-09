# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express — **versão refatorada para MVC**
pela skill `refactor-arch` (Fase 3). O relatório de auditoria que guiou a refatoração
está em `../reports/audit-project-2.md`.

## Estrutura

```
src/server.js           # entry point: lê config, monta a app, sobe o servidor
src/app.js              # composition root (createApp): instancia e injeta dependências
src/config/settings.js  # configuração por variáveis de ambiente (fail-fast em produção)
src/database/           # conexão com Promises + transação, migrations (com FKs) e seed
src/models/             # um model por entidade, queries parametrizadas
src/services/           # checkout (transacional), relatório financeiro, usuários
src/controllers/        # controllers finos
src/routes/             # Routers do Express: só contrato HTTP (camada View)
src/middlewares/        # auth administrativa, async handler, error handler central
src/gateways/           # gateway de pagamento injetável (não loga PAN nem chave)
src/security/           # hash de senha com scrypt (node:crypto)
src/errors/             # erros de domínio tipados
test/                   # node:test — 401/403, contrato do checkout, concorrência
```

## Como rodar

```bash
npm install
cp .env.example .env    # opcional; o app lê variáveis de ambiente
PORT=3000 ADMIN_API_TOKEN=dev-admin-token npm start
```

Sobe em `http://localhost:3000`. O banco SQLite é em memória (`DATABASE_PATH=:memory:`)
e recebe o seed a cada boot. Em `NODE_ENV=production` o boot **falha** se
`PAYMENT_GATEWAY_KEY` ou `ADMIN_API_TOKEN` estiverem ausentes. Exemplos de requisição
em `api.http`.

## Testes

```bash
npm test        # node --test, sem dependências extras
```

## Mudanças intencionais de contrato

- `GET /api/admin/financial-report` e `DELETE /api/users/:id` exigem
  `Authorization: Bearer $ADMIN_API_TOKEN` (sem token → 401). Se `ADMIN_API_TOKEN`
  não estiver configurado, as duas rotas ficam desabilitadas (403) — não há token
  default.
- `DELETE /api/users/:id` remove em cascata matrículas e pagamentos do usuário,
  responde 404 para id inexistente e não deixa mais alunos `Unknown` no relatório.
- `POST /api/checkout` valida formato de e-mail, `c_id` inteiro e número de cartão
  (12 a 19 dígitos) → 400 com mensagem específica.
- Sem `pwd`, a conta criada no checkout recebe senha aleatória (antes: `123456`).
- O log de pagamento mostra só os 4 últimos dígitos do cartão e nunca a chave.
