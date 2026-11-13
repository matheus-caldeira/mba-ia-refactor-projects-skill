# task-manager-api

API de Task Manager em Python/Flask usada como entrada do desafio `refactor-arch`, já refatorada para MVC (relatório da auditoria em `../reports/audit-project-3.md`).

## Como rodar

```bash
python -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env          # preencha SECRET_KEY (obrigatória)
./venv/bin/python seed.py     # banco vazio; use --reset para recriar (recusado em produção)
./venv/bin/python app.py
```

A aplicação sobe em `http://127.0.0.1:5000` (host, porta e debug vêm do `.env`).

## Autenticação

`POST /login` devolve um token assinado; envie-o como `Authorization: Bearer <token>`.
Rotas públicas: `GET /`, `GET /health`, `POST /login` e `POST /users` (cadastro, sempre com papel `user`).

| Papel | Pode |
|---|---|
| `user` | ver e alterar só as próprias tasks, o próprio cadastro e o próprio relatório |
| `manager` | ver/gerenciar tasks e categorias da equipe, relatório geral |
| `admin` | tudo, inclusive gestão de usuários (papel, ativação, exclusão) |

Trocar a própria senha exige `current_password` no `PUT /users/<id>`.

**Contas de exemplo (somente desenvolvimento):** fora de produção o seed cria
`joao@email.com`/`1234` (admin), `maria@email.com`/`abcd` (user) e
`pedro@email.com`/`pass` (manager). Com `APP_ENV=production` o seed cria apenas o
admin definido por `SEED_ADMIN_EMAIL`/`SEED_ADMIN_PASSWORD` (obrigatórios).

## Estrutura

```
config/        settings lidos do ambiente
models/        entidades ORM, regras da entidade e consultas
validators/    validação de payload (fonte única por entidade)
controllers/   casos de uso e regras de acesso
routes/        blueprints: só mapeamento HTTP → controller
middlewares/   autenticação e tratamento de erro centralizado
app.py         composition root (create_app)
```

## Testes

```bash
./venv/bin/pip install -r requirements-dev.txt
./venv/bin/python -m pytest tests
```
