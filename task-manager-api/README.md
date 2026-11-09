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

## Mudanças intencionais de contrato

- O hash de senha não aparece mais em nenhuma resposta (`GET/POST/PUT /users`, `/login`).
- `/login` devolve um token assinado com expiração (antes: `fake-jwt-token-<id>`).
- `DELETE /users/<id>` exige `Authorization: Bearer <token>` de um usuário `admin`
  (sem token → 401; outro papel → 403).
- `POST /users` com `role` diferente de `user`, e `PUT /users/<id>` alterando `role` ou
  `active`, exigem token de admin (403 caso contrário).
- `POST/PUT /categories` validam `color` (`#RRGGBB`), nome e descrição → 400.
- `DELETE /categories/<id>` desassocia as tasks da categoria (`category_id = null`).
- Erros inesperados respondem JSON `{"error": "Erro interno"}` com 500 (antes, alguns
  caminhos devolviam a página HTML padrão do Flask).
- `GET /health` informa `timestamp` em UTC.
