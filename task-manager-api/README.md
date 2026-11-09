# task-manager-api

API de Task Manager em Python/Flask — **versão refatorada para MVC** pela skill
`refactor-arch` (Fase 3). O projeto já tinha `models/`, `routes/`, `services/` e
`utils/`, mas as rotas faziam o trabalho de controller e de repositório. O relatório
que guiou a refatoração está em `../reports/audit-project-3.md`.

## Estrutura

```
app.py                  # application factory (create_app) e composition root
config/settings.py      # configuração por variáveis de ambiente (.env via python-dotenv)
models/                 # entidades SQLAlchemy + regras da própria entidade (is_overdue)
repositories/           # consultas (select/joinedload/GROUP BY), sem N+1
controllers/            # casos de uso de tasks, usuários, categorias e relatórios
routes/                 # Blueprints: só mapeamento HTTP (camada View)
services/               # autenticação (token assinado) e notificação (SMTP por env)
middlewares/            # auth (require_auth/require_role) e error handler central
errors.py               # erros de domínio tipados
seed.py                 # dados de desenvolvimento (senha em SEED_PASSWORD)
tests/                  # pytest: matriz de autorização (401/403) por rota
```

`utils/helpers.py` foi removido: nenhuma função dele era usada; as constantes e
validações vivem agora nos models/controllers que as aplicam.

## Como rodar

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env              # opcional; o app carrega o .env automaticamente
SEED_PASSWORD=dev-password-123 ./venv/bin/python seed.py
./venv/bin/python app.py
```

Sobe em `http://127.0.0.1:5000` (`HOST`/`PORT` configuráveis). O banco SQLite fica em
`instance/tasks.db` e é criado no boot.

## Testes

```bash
./venv/bin/pip install -r requirements-dev.txt
./venv/bin/python -m pytest -q
```

## Autenticação e autorização

`POST /login` devolve um token assinado com expiração; envie-o como
`Authorization: Bearer <token>`.

| Acesso | Rotas |
|---|---|
| Público | `GET /`, `GET /health`, `POST /login`, `POST /users` (cadastro só com `role: user`) |
| Autenticado, **com escopo do ator** | `GET /tasks`, `GET /tasks/search`, `GET /tasks/stats`, `GET /categories` (o `task_count`) — usuário comum vê/conta só as próprias tasks; admin/manager veem tudo. `search?user_id=<outro>` por usuário comum → 403 |
| Autenticado | `POST /tasks` |
| Dono da task ou admin/manager | `GET /tasks/<id>`, `PUT /tasks/<id>`, `DELETE /tasks/<id>`; atribuir task a outro usuário |
| Próprio usuário ou admin/manager | `GET /users/<id>`, `GET /users/<id>/tasks`, `GET /reports/user/<id>` |
| Próprio usuário ou admin | `PUT /users/<id>` — `role`/`active` só admin; trocar a própria senha exige `current_password` |
| Admin/manager | `GET /users`, `GET /reports/summary`, `POST/PUT/DELETE /categories` |
| Admin | `DELETE /users/<id>` |

Sem token → 401; papel ou dono incorreto → 403.

`GET /tasks/stats` continua disponível a qualquer autenticado (como no original, que
não tinha restrição), mas para usuário comum as contagens cobrem só as tasks dele;
restringir a rota a admin/manager quebraria o uso legítimo do próprio painel.

### Contas

- **Admin de produção:** `ADMIN_EMAIL` / `ADMIN_PASSWORD` (e `ADMIN_NAME`) são
  obrigatórias com `APP_ENV=production` — o boot falha sem elas — e a conta é garantida
  no boot. Fora de produção são opcionais.
- **`seed.py`:** cria contas de exemplo com `SEED_PASSWORD` (default `dev-password-123`,
  **somente desenvolvimento**) e se recusa a rodar com `APP_ENV=production`.

## Mudanças intencionais de contrato

- As rotas não públicas da tabela acima passaram a exigir token (no original nenhuma
  rota verificava identidade). Com o token adequado, os 35 cenários do roteiro de
  validação respondem com os mesmos status do original.
- Listagem, busca, estatísticas e contagens por categoria passaram a ter escopo do
  ator para usuários comuns; `GET /tasks/<id>` de outro usuário → 403.
- O hash de senha não aparece mais em nenhuma resposta (`GET/POST/PUT /users`, `/login`).
- `/login` devolve um token assinado com expiração (antes: `fake-jwt-token-<id>`).
- `POST /users` com `role` diferente de `user` exige token de admin (403 caso contrário).
- `POST/PUT /categories` validam `color` (`#RRGGBB`), nome e descrição → 400.
- `DELETE /categories/<id>` desassocia as tasks da categoria (`category_id = null`).
- Erros inesperados respondem JSON `{"error": "Erro interno"}` com 500 (antes, alguns
  caminhos devolviam a página HTML padrão do Flask).
- `GET /health` informa `timestamp` em UTC.
