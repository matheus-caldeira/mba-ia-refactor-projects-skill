# code-smells-project

API de E-commerce em Python/Flask — **versão refatorada para MVC** pela skill
`refactor-arch` (Fase 3). O relatório de auditoria que guiou a refatoração está em
`../reports/audit-project-1.md`.

## Estrutura

```
app.py                  # composition root (application factory create_app)
config/settings.py      # configuração por variáveis de ambiente
models/                 # conexão por requisição, schema/seed e um model por entidade
controllers/            # casos de uso (produto, usuário, pedido/relatório, sistema)
services/               # regra que cruza entidades (pedido, relatório) e notificador
routes/                 # Blueprints: só mapeamento HTTP (camada View)
middlewares/            # erros tipados, error handler central e autenticação (token)
tests/                  # pytest: autorização 401/403, estoque concorrente, regressões
```

## Como rodar

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env            # opcional; ajuste os valores
set -a; . ./.env; set +a        # exporta as variáveis (ou exporte manualmente)
./venv/bin/python app.py
```

Sobe em `http://127.0.0.1:5000` por padrão (`HOST`/`PORT` configuráveis — no macOS a
porta 5000 costuma estar ocupada pelo AirPlay, use `PORT=5001`). O banco SQLite
(`loja.db`) é criado no primeiro boot com produtos e usuários de exemplo; as senhas do
seed são gravadas com hash.

## Testes

```bash
./venv/bin/pip install -r requirements-dev.txt
./venv/bin/python -m pytest -q
```

## Autenticação e autorização

`POST /login` devolve, além dos dados do usuário, um `token` assinado (expira em
`TOKEN_TTL_SECONDS`). Envie-o como `Authorization: Bearer <token>`.

| Acesso | Rotas |
|---|---|
| Público | `GET /`, `GET /health`, `GET /produtos`, `GET /produtos/busca`, `GET /produtos/<id>`, `POST /usuarios`, `POST /login` |
| Próprio usuário ou admin | `GET /usuarios/<id>`, `GET /pedidos/usuario/<id>`, `POST /pedidos` (o `usuario_id` do corpo tem de ser o do token) |
| Somente admin (`tipo = admin`) | `GET /usuarios`, `GET /pedidos`, `PUT /pedidos/<id>/status`, `GET /relatorios/vendas`, `POST/PUT/DELETE /produtos` |
| Admin **e** `ENABLE_RESET_DB=true` (nunca em produção) | `POST /admin/reset-db` |

Sem token → 401; token de outro usuário ou sem papel suficiente → 403.

### Contas criadas no primeiro boot

- **Admin:** `ADMIN_EMAIL` / `ADMIN_PASSWORD` (e `ADMIN_NAME`). Com `APP_ENV=production`
  são obrigatórias — o boot falha sem elas. Fora de produção o default é
  `admin@loja.com` / `admin123`, **somente para desenvolvimento**.
- **Clientes de exemplo** (`joao@email.com` / `123456`, `maria@email.com` / `senha123`):
  criados só fora de produção.

## Mudanças intencionais de contrato

- As rotas da tabela acima que não são públicas passaram a exigir token (no original
  tudo era aberto e o login não emitia credencial).
- `POST /admin/query` (executor de SQL arbitrário) foi **removido** → 404.
- `POST /admin/reset-db` exige admin **e** `ENABLE_RESET_DB=true` (desligado por
  padrão e sempre desligado em produção) → 403 caso contrário.
- Em produção não há mais conta admin com senha conhecida nem clientes de exemplo.
- A baixa de estoque é atômica (UPDATE condicional); quantidades repetidas do mesmo
  produto no pedido são somadas antes de validar.
- `GET /health` deixou de expor `secret_key`, `debug`, `db_path` e `ambiente`.
- `GET /usuarios` e `GET /usuarios/<id>` não devolvem mais o campo `senha`.
- Respostas de erro passaram a ter formato único `{"erro": ..., "sucesso": false}`.
- `PUT /produtos/<id>` aplica as mesmas validações da criação (nome e categoria).
- `POST /usuarios` com e-mail já cadastrado responde 409.
- Cancelar um pedido agora devolve o estoque dos itens.
