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
middlewares/            # erros tipados, error handler central e auth administrativa
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

## Mudanças intencionais de contrato

- `POST /admin/query` (executor de SQL arbitrário) foi **removido** → 404.
- `POST /admin/reset-db` exige `Authorization: Bearer $ADMIN_TOKEN`; sem token
  configurado, ou com `APP_ENV=production`, responde 403.
- `GET /health` deixou de expor `secret_key`, `debug`, `db_path` e `ambiente`.
- `GET /usuarios` e `GET /usuarios/<id>` não devolvem mais o campo `senha`.
- Respostas de erro passaram a ter formato único `{"erro": ..., "sucesso": false}`.
- `PUT /produtos/<id>` aplica as mesmas validações da criação (nome e categoria).
- `POST /usuarios` com e-mail já cadastrado responde 409.
- Cancelar um pedido agora devolve o estoque dos itens.
