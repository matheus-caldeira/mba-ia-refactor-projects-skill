# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`,
refatorada para MVC (auditoria em `../reports/audit-project-1.md`).

## Como rodar

```bash
python -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env          # preencha SECRET_KEY (obrigatória)
./venv/bin/python app.py
```

A aplicação sobe em `http://127.0.0.1:5000` (configurável por `HOST`/`PORT`). O banco
SQLite (`DB_PATH`, padrão `loja.db`) é criado no primeiro boot.

- `APP_ENV=development`: cria produtos e clientes de demonstração e, sem
  `ADMIN_EMAIL`/`ADMIN_PASSWORD`, o admin `admin@loja.com` / `admin123`
  (**somente desenvolvimento**).
- `APP_ENV=production` (padrão): sem dados de demonstração; `SECRET_KEY`,
  `ADMIN_EMAIL` e `ADMIN_PASSWORD` são obrigatórios e o boot falha sem eles.

Um `loja.db` criado pela versão antiga é incompatível (senhas em texto puro, sem FKs):
apague-o antes do primeiro boot.

## Autenticação

`POST /login` devolve `token`; envie-o como `Authorization: Bearer <token>`.

| Rota | Acesso |
|---|---|
| `GET /`, `GET /health`, `GET /produtos`, `GET /produtos/busca`, `GET /produtos/<id>` | público |
| `POST /usuarios`, `POST /login` | público |
| `GET /usuarios`, `GET /pedidos` | autenticado (cliente vê só os próprios registros, admin vê todos) |
| `GET /usuarios/<id>`, `GET /pedidos/usuario/<id>` | próprio usuário ou admin |
| `POST /pedidos` | autenticado; o dono é o usuário do token (admin pode informar `usuario_id`) |
| `POST/PUT/DELETE /produtos`, `PUT /pedidos/<id>/status`, `GET /relatorios/vendas` | admin |
| `POST /admin/reset-db` | admin, e só com `ENABLE_RESET_DB=true` fora de produção |

## Estrutura

```
app.py            composition root (create_app)
config.py         configuração lida do ambiente
database.py       conexão por requisição, transação, schema
seed.py           dados iniciais
errors.py         erros de domínio tipados
models/           acesso a dados parametrizado + invariantes, um por entidade
services/         fluxos que cruzam entidades (pedido, relatório, auth, notificação)
controllers/      orquestração dos casos de uso e regras de acesso
routes/           Blueprints (fronteira HTTP)
middlewares/      autenticação e error handler central
tests/            pytest
```

## Testes

```bash
./venv/bin/python -m pytest tests
```
