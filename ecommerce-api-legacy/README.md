# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express, refatorada para MVC pela skill `refactor-arch`.

## Como rodar

```bash
npm install
cp .env.example .env   # preencha PAYMENT_GATEWAY_KEY e AUTH_SECRET (>= 32 caracteres)
npm start
```

A aplicação sobe em `http://127.0.0.1:3000` (`HOST`/`PORT` no `.env`). O banco SQLite é em
memória por padrão (`DB_PATH`) e recebe o seed no boot. Sem os segredos obrigatórios o boot falha.

## Autenticação

`POST /api/auth/login` com `{"email", "password"}` devolve um token; envie-o em
`Authorization: Bearer <token>`.

| Rota | Acesso |
|---|---|
| `POST /api/checkout` | público |
| `POST /api/auth/login` | público |
| `GET /api/admin/financial-report` | admin |
| `DELETE /api/users/:id` | admin, ou o próprio usuário |

A conta admin vem de `ADMIN_EMAIL`/`ADMIN_PASSWORD` (obrigatórios com `NODE_ENV=production`).
Em desenvolvimento, sem essas variáveis, usa `admin@lms.local` / `admin-dev-only` — **somente dev**.

## Estrutura

```
src/
├── app.js            # composition root (createApp + start)
├── config/           # settings lidos do ambiente
├── database/         # conexão (Promise + fila de transações), schema, seed
├── domain/           # erros tipados e constantes (papéis, status de pagamento)
├── models/           # acesso a dados por entidade, queries parametrizadas
├── services/         # checkout, relatório, gateway de pagamento, hash de senha, token
├── controllers/      # orquestram os casos de uso
├── validators/       # contrato de entrada HTTP
├── routes/           # mapeamento HTTP → controller (Express Routers)
└── middlewares/      # auth, error handler, async handler
```

Exemplos de requisições estão em `api.http`.
