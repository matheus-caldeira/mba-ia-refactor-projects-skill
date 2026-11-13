================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python 3.12 + Flask 3.0.0 (Flask-SQLAlchemy 3.1.1 / SQLAlchemy 2.1.8)
Files:   15 analyzed | ~1158 lines of code
Date:    2026-11-12

## Summary
CRITICAL: 4 | HIGH: 2 | MEDIUM: 4 | LOW: 1

## Findings

### #1 [CRITICAL] Nenhuma autenticação/autorização: token falso, IDOR em todas as rotas e papel escolhido pelo próprio cliente
- **Anti-pattern:** AP-05 — Endpoint sem autenticação / IDOR / mass assignment
- **File:** `routes/user_routes.py:207-211, 52, 71-78, 119-125`, `routes/task_routes.py:11-299`, `routes/report_routes.py:12-223`, `app.py:15`
- **Description:** O grep por `before_request|login_required|authenticate|Authorization|jwt|session[` retorna zero mecanismos de autenticação; a única ocorrência é o token literal `'fake-jwt-token-' + str(user.id)` devolvido pelo `/login`, que nenhuma rota verifica. Todas as 22 rotas são públicas. `POST /users` aceita `role` do corpo (linha 52, só valida que está na lista) e `PUT /users/<id>` aceita `role` e `active` (linhas 119-125) sem qualquer checagem de quem pede. Leituras também não têm escopo: `GET /tasks`, `/tasks/search`, `/tasks/stats`, `/users`, `/users/<id>`, `/reports/summary` e `/reports/user/<id>` devolvem dados de todos os usuários. `CORS(app)` libera qualquer origem.

  Matriz rota × quem pode hoje: **todas = público anônimo**, inclusive `DELETE /users/<id>`, `PUT /users/<id>` (role), `DELETE /categories/<id>`.
- **Impact:** Qualquer pessoa na rede cria uma conta admin com `POST /users {"role":"admin",...}`, promove a si mesma com `PUT /users/<id> {"role":"admin"}`, desativa outros usuários (`{"active": false}` bloqueia o login deles), apaga usuários junto com todas as tasks deles e lê o relatório de produtividade de toda a equipe. O "token" é previsível (`fake-jwt-token-1` = admin).
- **Recommendation:** Emitir token assinado (HMAC com `SECRET_KEY` vindo do ambiente, ex.: `itsdangerous`, já dependência do Flask) no `/login` e criar decorators `require_auth`/`require_role` aplicados em todas as rotas exceto `/`, `/health`, `/login` e `POST /users` (cadastro). Cadastro público sempre cria `role=user`; `role`/`active` só alteráveis por admin. Leituras recebem o ator e aplicam escopo `user_id = ator` para quem não é admin/manager; acesso a recurso de outro usuário → 403.

```python
    return jsonify({
        'message': 'Login realizado com sucesso',
        'user': user.to_dict(),
        'token': 'fake-jwt-token-' + str(user.id)
    }), 200
```

### #2 [CRITICAL] Senha com MD5 sem salt e hash devolvido nas respostas da API
- **Anti-pattern:** AP-03 — Senha em texto puro ou hash fraco
- **File:** `models/user.py:21, 27-32`; vazamento via `routes/user_routes.py:33, 85, 129, 209`
- **Description:** `set_password` grava `hashlib.md5(pwd.encode()).hexdigest()` e `check_password` compara MD5 cru. O grep por `bcrypt|argon2|scrypt|pbkdf2|generate_password_hash` retorna zero. `User.to_dict()` inclui `'password': self.password`, e esse dict é devolvido por `GET /users/<id>`, `POST /users`, `PUT /users/<id>` e `POST /login`.
- **Impact:** `GET /users/1` (público, ver #1) entrega o hash MD5 do admin; MD5 sem salt de senha curta (o seed usa `1234`) é revertido instantaneamente por rainbow table. Na prática, é senha em texto puro exposta por HTTP.
- **Recommendation:** Trocar por `werkzeug.security.generate_password_hash`/`check_password_hash` (scrypt/pbkdf2 com salt, já instalado com o Flask), com upgrade transparente do hash MD5 legado no próximo login bem-sucedido. Remover `password` do `to_dict()`. Exigir senha atual na troca feita pelo próprio usuário.

```python
    def set_password(self, pwd):

        self.password = hashlib.md5(pwd.encode()).hexdigest()

    def check_password(self, pwd):
        return self.password == hashlib.md5(pwd.encode()).hexdigest()
```

### #3 [CRITICAL] Segredos hardcoded e contas privilegiadas do seed com senha conhecida
- **Anti-pattern:** AP-02 — Credenciais e segredos hardcoded
- **File:** `app.py:11, 13`, `services/notification_service.py:7-10`, `seed.py:11-14, 16-35`
- **Description:** `SECRET_KEY = 'super-secret-key-123'` e a URI do banco fixos em `app.py`; credenciais SMTP (`taskmanager@gmail.com` / `senha123`) literais no `NotificationService`. O seed cria o admin `joao@email.com` com senha `1234` e o manager `pedro@email.com` com `pass`, e começa apagando todas as tasks, usuários e categorias sem nenhuma guarda.
- **Impact:** Quem lê o repositório (o fork é público) conhece a chave de assinatura de sessão/token e entra como admin com `joao@email.com`/`1234` — o que anula qualquer controle de acesso que venha a ser criado. Rodar `seed.py` por engano num ambiente real apaga todos os dados. Os valores versionados devem ser considerados comprometidos (rotacionar a senha SMTP).
- **Recommendation:** Módulo `config/` lendo `SECRET_KEY`, `DATABASE_URL`, `SMTP_*` do ambiente (`python-dotenv` já está no manifesto), `.env.example` sem valores reais e boot que falha sem `SECRET_KEY` em produção. Seed cria o admin só com `SEED_ADMIN_EMAIL`/`SEED_ADMIN_PASSWORD` do ambiente; contas de exemplo com senha conhecida apenas fora de produção; reset destrutivo atrás de flag explícito.

```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'super-secret-key-123'
```

### #4 [CRITICAL] Debug do Werkzeug ligado com bind em todas as interfaces
- **Anti-pattern:** AP-06 — Debug ativo e exposição de configuração
- **File:** `app.py:33-34`
- **Description:** `app.run(debug=True, host='0.0.0.0', port=5000)` com valor literal, não controlado por ambiente.
- **Impact:** Qualquer exceção não tratada (ex.: `POST /tasks {"title":"abc","priority":"alta"}` gera `TypeError` em `task_routes.py:113`, ver #9) devolve a página de debug com traceback, caminhos e código-fonte, e o console interativo do Werkzeug — protegido apenas por PIN derivável de dados da máquina — fica alcançável por toda a rede: execução remota de Python.
- **Recommendation:** `debug` e `host` vindos de `FLASK_DEBUG`/`HOST` com padrão seguro (`False`, `127.0.0.1`), e handler de erro central (#10) devolvendo JSON genérico.

```python
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

### #5 [HIGH] Rotas fazem o trabalho de controller, service e repository
- **Anti-pattern:** AP-08 — Regra de negócio dentro do controller/rota
- **File:** `routes/task_routes.py:11-63, 85-154, 156-223, 273-299`, `routes/report_routes.py:12-101, 103-155, 157-223`, `routes/user_routes.py:42-90, 134-151`
- **Description:** Os handlers acessam o ORM diretamente (`Task.query...` em todas as rotas), validam, decidem regra de domínio e serializam à mão. A regra "task atrasada" (prazo vencido e status ≠ done/cancelled) está reescrita 6 vezes (`task_routes.py:30-39, 71-80, 283-287`, `user_routes.py:171-180`, `report_routes.py:33-43, 132-135`) enquanto `Task.is_overdue()` (`models/task.py:50-60`) nunca é chamado. `get_tasks` (52 linhas) e `summary_report` (89 linhas, 13 consultas) são métodos-deus. A cascata "apagar usuário apaga as tasks dele" vive no handler (`user_routes.py:140-142`). O CRUD de categorias mora em `report_routes.py`, junto com relatórios. A serialização de task é refeita à mão em `task_routes.py:17-28` e `user_routes.py:162-169` com formatos diferentes do `Task.to_dict()`.
- **Impact:** Mudar a regra de atraso exige editar 6 lugares (e já divergem: `GET /users/<id>/tasks` omite `user_id`, `updated_at` e `tags`). Nada é testável sem subir HTTP + banco. `services/` e `utils/` existem mas não são usados pelas rotas, dando falsa impressão de camadas.
- **Recommendation:** Criar `controllers/` (task, user, category, report) com a regra; models expõem `is_overdue()`, `to_dict()` e consultas nomeadas; rotas viram só mapeamento HTTP → controller. Categorias ganham blueprint próprio. Uma única serialização por entidade.

### #6 [HIGH] Código morto em services/ e utils/ duplicando o que as rotas reimplementam
- **Anti-pattern:** AP-08 — Regra de negócio dentro do controller/rota (camada de serviço não usada)
- **File:** `services/notification_service.py:1-48`, `utils/helpers.py:9-116`, `models/task.py:38-48`, `models/user.py:34-38`
- **Description:** O grep por `NotificationService` encontra apenas a definição — a classe nunca é instanciada. De `utils/helpers.py` só `format_date` e `calculate_percentage` são importados (`report_routes.py:7`) e nenhum dos dois é chamado; `process_task_data`, `validate_email`, `parse_date`, `is_valid_color` e as constantes `VALID_STATUSES`, `VALID_ROLES`, `MIN_PASSWORD_LENGTH`... são mortos. `Task.validate_status/validate_priority` e `User.is_admin` também não têm chamador.
- **Impact:** Duas implementações de cada regra (a morta e a inline) já divergem: `parse_date` aceita `DD/MM/YYYY`, as rotas só `YYYY-MM-DD`; o service traz credenciais reais (#3) para um código que nem roda. Quem mantém altera a cópia errada.
- **Recommendation:** Passar a usar as funções de validação/constantes a partir dos controllers (fonte única) e remover o restante. `NotificationService` sem chamador e com SMTP síncrono vai embora (ou fica só se ligado a um evento real com config do ambiente).

### #7 [MEDIUM] APIs deprecated do SQLAlchemy 2.x e do Python 3.12
- **Anti-pattern:** AP-09 — APIs deprecated / obsoletas
- **File:** `Model.query.get()` em 16 pontos (`routes/task_routes.py:42, 51, 67, 117, 122, 158, 188, 195, 227`, `routes/user_routes.py:29, 94, 136, 155`, `routes/report_routes.py:105, 192, 213`); `datetime.utcnow()` em 22 pontos (`models/*.py:11-16, 52`, rotas, `seed.py`, `services/`, `utils/`)
- **Description:** O ambiente resolve SQLAlchemy 2.1.8, onde `Query.get()` é legado (emite `LegacyAPIWarning`); o Python 3.12 depreca `datetime.utcnow()`. O MD5 de senha está tratado em #2.
- **Impact:** Avisos a cada requisição hoje e quebra quando a API legada for removida; `utcnow()` devolve datetime naive, fácil de comparar errado com datas aware.
- **Recommendation:** `db.session.get(Model, id)` e um helper `utcnow()` único em `datetime.now(timezone.utc)` (gravado naive-UTC para manter o formato atual das colunas SQLite).

### #8 [MEDIUM] Consultas N+1 nas listagens e relatórios
- **Anti-pattern:** AP-10 — Query N+1
- **File:** `routes/task_routes.py:41-57`, `routes/user_routes.py:22`, `routes/report_routes.py:53-56, 159-163, 15-28`
- **Description:** `GET /tasks` faz `User.query.get` e `Category.query.get` por task; `GET /users` dispara o lazy load `len(u.tasks)` por usuário; `summary_report` faz `Task.query.filter_by(user_id=u.id).all()` por usuário mais 12 `count()` separados; `GET /categories` faz um `count()` por categoria.
- **Impact:** Com 500 tasks, `GET /tasks` executa 1001 consultas; o custo cresce linearmente com a base em todo dashboard.
- **Recommendation:** `selectinload`/`joinedload` para usuário e categoria; contagens com `GROUP BY` (`func.count` agrupado por status, prioridade, user_id e category_id) em uma consulta cada.

### #9 [MEDIUM] Validação de entrada ausente, sem tipo e triplicada
- **Anti-pattern:** AP-11 — Validação de entrada ausente ou duplicada
- **File:** `routes/task_routes.py:96-114, 166-184, 260-264`, `routes/user_routes.py:61, 106`, `utils/helpers.py:21`, `routes/report_routes.py:173-180, 196-202`
- **Description:** Nenhuma checagem de tipo: `priority < 1` com `"alta"` lança `TypeError` (linhas 113, 182); `len(data['title'])` com número lança `TypeError` (167); `/tasks/search?priority=x` faz `int('x')` sem tratamento (261). `PUT /categories/<id>` sem corpo JSON faz `'name' in None` (197). `color` de categoria não é validado apesar de `is_valid_color` existir. O regex de e-mail aparece 3 vezes e a lista de status 4 (`models/task.py:39`, `utils/helpers.py:75`, `task_routes.py:110, 177`). `marshmallow` está no manifesto e não é usado.
- **Impact:** Entrada malformada vira 500 (com página de debug, #4) em vez de 400; regras copiadas divergem a cada manutenção.
- **Recommendation:** Validadores únicos (um por entidade) chamados pelos controllers, checando tipo e faixa, com erro de domínio que vira 400. Remover dependências não usadas do manifesto.

### #10 [MEDIUM] Erros engolidos por `except` genérico e logging por `print`
- **Anti-pattern:** AP-12 — Tratamento de erro engolido ou inconsistente
- **File:** `routes/task_routes.py:62, 137, 151, 204, 221, 236`, `routes/user_routes.py:87, 130, 149`, `routes/report_routes.py:186, 207, 221`, `services/notification_service.py:23`, `utils/helpers.py:46, 49, 88`
- **Description:** 16 blocos `except:`/`except Exception` descartam a exceção; `get_tasks` embrulha toda a rota em `try/except: return 500` sem log. Não há `errorhandler` registrado. Logs são `print(...)` (`task_routes.py:149, 153, 219, 234`, `user_routes.py:83, 89, 147`). Corrida check-then-act no e-mail único (`user_routes.py:67-69` → `commit`) cai no `except` como 500 em vez de 409.
- **Impact:** Bug de programação aparece como "Erro interno" sem nenhum rastro; o formato do erro varia por rota e o cliente não tem contrato.
- **Recommendation:** Exceções de domínio (`ValidationError`, `NotFound`, `Conflict`, `Forbidden`) e handlers centrais registrados no app que devolvem `{"error": msg}` com o status certo e registram via `logging` o 500 inesperado; `IntegrityError` → 409.

### #11 [LOW] Imports mortos, magic numbers e schema criado no import
- **Anti-pattern:** AP-14 — Legibilidade
- **File:** `app.py:7, 30-31`, `routes/task_routes.py:7`, `routes/user_routes.py:5-6`, `routes/report_routes.py:7-8`, `models/task.py:3`, `utils/helpers.py:3-7`, `routes/report_routes.py:84-88, 129`, `models/user.py:34-38`
- **Description:** `import os, sys, json, datetime` (só `datetime` usado), `import json, os, sys, time` (nenhum usado), `hashlib, json` sem uso em `user_routes.py`, `json`, `format_date`, `calculate_percentage` sem uso em `report_routes.py`. Prioridade 1–5, padrão 3, título 3–200, senha ≥ 4 e o mapa `1=critical…5=minimal` como literais soltos; `t.priority <= 2` como "alta prioridade". `if ...: return True else: return False`. `db.create_all()` roda como efeito colateral do import de `app.py`.
- **Impact:** Custo de leitura e dependências reais escondidas; importar o módulo (ex.: em teste) já mexe no banco.
- **Recommendation:** Remover imports sem uso, centralizar constantes de domínio, `create_app()` (factory) fazendo `create_all()` explicitamente.

## Deprecated APIs
| API em uso | Arquivo:linha | Substituir por |
|---|---|---|
| `Model.query.get(id)` | `routes/task_routes.py:42, 51, 67, 117, 122, 158, 188, 195, 227`; `routes/user_routes.py:29, 94, 136, 155`; `routes/report_routes.py:105, 192, 213` | `db.session.get(Model, id)` |
| `datetime.utcnow()` | `models/task.py:15-16, 52`; `models/user.py:14`; `models/category.py:11`; `routes/task_routes.py:31, 72, 215, 285`; `routes/user_routes.py:172`; `routes/report_routes.py:35, 42, 45, 71, 133`; `seed.py:66-74`; `services/notification_service.py:35`; `utils/helpers.py:38` | `datetime.now(timezone.utc)` |
| `hashlib.md5` (senha) | `models/user.py:29, 32` | `werkzeug.security.generate_password_hash` (scrypt) / bcrypt |

## Categories Not Applicable
- AP-01 SQL Injection — todo acesso passa pelo ORM; grep por `execute(`/`text(` retorna zero e o `LIKE` de `/tasks/search` (`task_routes.py:252-253`) é parametrizado pelo SQLAlchemy.
- AP-04 God Class — nenhum arquivo passa de 300 linhas e a camada de model é separada; a mistura de responsabilidades nos handlers (incluindo os métodos-deus `get_tasks` e `summary_report`) está registrada em #5.
- AP-07 Estado global mutável — a sessão do Flask-SQLAlchemy é por requisição; a única lista mutável (`NotificationService.notifications`) é de instância de uma classe nunca instanciada (#6).
- AP-13 Integridade referencial — `tasks.user_id`/`category_id` têm FK declarada; `DELETE /categories/<id>` deixa o SQLAlchemy anular o FK das tasks (backref sem cascade) e `DELETE /users/<id>` apaga as tasks no mesmo commit; `users.email` tem `unique=True` no banco (a corrida check-then-act do e-mail aparece em #10 como erro mal tratado).

## Architecture Assessment
**Current:** Parcialmente estruturada — models com ORM e blueprints por recurso existem, mas as rotas acessam o ORM direto e concentram validação, regra e serialização; `services/` e `utils/` estão mortos.
**Target:** MVC com `config/` (settings do ambiente), `models/` (ORM existente + regras de entidade como `is_overdue`), `controllers/` (task, user, category, report, auth), `routes/` (blueprints só com mapeamento HTTP), `middlewares/` (autenticação/papéis e error handlers) e `app.py` como factory.
**Main structural gap:** Ausência total de autenticação e autorização (#1) — sem identidade do ator não há como escopar nenhuma leitura ou escrita; a seguir, tirar a regra das rotas para controllers que recebam esse ator.

================================
Total: 11 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
