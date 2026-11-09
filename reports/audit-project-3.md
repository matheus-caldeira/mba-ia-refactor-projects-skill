================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python 3.12 + Flask 3.0.0 (Flask-SQLAlchemy 3.1.1 / SQLAlchemy 2.x, flask-cors 4.0.0, marshmallow 3.20.1 declarado e não usado)
Files:   15 analyzed | ~1158 lines of code (routes/task_routes.py 299, routes/report_routes.py 223, routes/user_routes.py 211, utils/helpers.py 116, seed.py 99, ...)
Date:    2026-11-09

> Saída da Fase 2 da skill `refactor-arch`, gerada sobre o código **original** do
> projeto (commit base do repositório, antes da Fase 3). Todas as referências
> `arquivo:linha` apontam para esse estado — para conferir, use
> `git show 6d1ce62:task-manager-api/<arquivo>`.

## Summary
CRITICAL: 5 | HIGH: 2 | MEDIUM: 4 | LOW: 3

## Findings

### #1 [CRITICAL] Senhas com MD5 sem salt
- **Anti-pattern:** AP-03 — Senha em texto puro ou hash fraco (também AP-09: `hashlib.md5` para senha)
- **File:** `models/user.py:27-32`, `seed.py:19, 26, 33`
- **Description:** `set_password` e `check_password` usam `hashlib.md5(pwd).hexdigest()`,
  sem salt nem fator de custo. O seed cria usuários com `'1234'`, `'abcd'`, `'pass'`.
- **Impact:** MD5 é quebrado e rápido: senhas curtas saem de rainbow table em segundos
  (`81dc9bdb52d04dc20036dbd8313ed055` é o MD5 público de `1234`). Senhas iguais geram
  hashes iguais.
- **Recommendation:** `werkzeug.security.generate_password_hash`/`check_password_hash`
  (já disponível com o Flask, KDF com salt); hashes MD5 antigos tratados como inválidos
  (playbook P-03).

```python
def set_password(self, pwd):

    self.password = hashlib.md5(pwd.encode()).hexdigest()
```

### #2 [CRITICAL] Hash da senha devolvido pela API
- **Anti-pattern:** AP-03 — Senha em texto puro ou hash fraco (vazamento na serialização)
- **File:** `models/user.py:16-25` (campo na linha 21); consumido em `routes/user_routes.py:33, 85, 129, 209`
- **Description:** `User.to_dict()` inclui `password`, e é usado por `GET /users/<id>`,
  `POST /users`, `PUT /users/<id>` e `POST /login`.
- **Impact:** Qualquer cliente obtém o hash MD5 de qualquer usuário (baseline:
  `GET /users/1` devolveu `"password": "81dc9bdb..."`) — com #1, equivale a vazar a
  senha em claro.
- **Recommendation:** Serialização por lista de permissão sem o campo de senha.

### #3 [CRITICAL] Credenciais SMTP hardcoded
- **Anti-pattern:** AP-02 — Credenciais e segredos hardcoded
- **File:** `services/notification_service.py:7-10`
- **Description:** Host, porta, usuário (`taskmanager@gmail.com`) e senha (`senha123`)
  literais no construtor do serviço.
- **Impact:** A credencial de e-mail está no repositório: permite enviar mensagens em
  nome da aplicação (phishing) e precisa ser rotacionada.
- **Recommendation:** Ler SMTP da configuração por ambiente; envio desligado quando não
  configurado (playbook P-02).

```python
self.email_user = 'taskmanager@gmail.com'
self.email_password = 'senha123'
```

### #4 [CRITICAL] SECRET_KEY hardcoded e debug ligado em 0.0.0.0
- **Anti-pattern:** AP-02 — Credenciais hardcoded / AP-06 — Debug ativo
- **File:** `app.py:11-13`, `app.py:34`
- **Description:** `SECRET_KEY = 'super-secret-key-123'` e URI do banco literais;
  `app.run(debug=True, host='0.0.0.0', port=5000)`. `python-dotenv` está no
  `requirements.txt` mas nunca é usado.
- **Impact:** Console do Werkzeug exposto na rede (execução remota de código); a chave
  de assinatura é pública.
- **Recommendation:** `config/settings.py` lendo env (com `load_dotenv`), segredo
  obrigatório em produção, debug desligado e bind local por padrão (playbook P-02/P-06).

### #5 [CRITICAL] Autenticação falsa e nenhuma rota protegida
- **Anti-pattern:** AP-05 — Endpoint administrativo sem autenticação
- **File:** `routes/user_routes.py:207-211` (token), `routes/user_routes.py:52, 71-72` (role livre no cadastro), `routes/user_routes.py:92-132` (PUT de qualquer usuário, inclusive `role`, `active` e senha), `routes/user_routes.py:134-151` (DELETE), `routes/task_routes.py:156-238` (PUT/DELETE de qualquer task)
- **Description:** O "token" de login é `'fake-jwt-token-' + str(user.id)` — sem
  assinatura nem expiração — e nenhuma rota o verifica (grep por
  `before_request|login_required|Authorization` = 0). `POST /users` aceita `role`
  arbitrário.
- **Impact:** Qualquer pessoa se cadastra como `admin`, forja o token de qualquer
  usuário trocando o número, troca a senha ou o papel de qualquer usuário via
  `PUT /users/<id>` (sem senha atual), altera ou apaga tasks alheias e exclui usuários
  (com todas as suas tasks) via `DELETE /users/<id>` sem credencial. Também não há
  escopo de leitura: `GET /tasks`, `/tasks/search`, `/tasks/stats`, `/tasks/<id>` e as
  contagens de `GET /categories` expõem as tasks de todos os usuários. O `seed.py`
  cria o admin `joao@email.com` com senha literal (`seed.py:16-21`).
- **Recommendation:** Token assinado e com expiração (`itsdangerous`, já dependência
  do Flask), `require_auth` em todas as rotas exceto login, cadastro e health; checagem
  de dono no controller (próprio usuário ou admin/manager) **também nas leituras**
  (listagem, busca, estatísticas e contagens com escopo do ator); somente admin define
  `role`/`active`; troca da própria senha exige a senha atual (playbook P-05); admin
  criado só com credenciais do ambiente e `seed.py` restrito a desenvolvimento (P-02).

```python
return jsonify({
    'message': 'Login realizado com sucesso',
    'user': user.to_dict(),
    'token': 'fake-jwt-token-' + str(user.id)
}), 200
```

### #6 [HIGH] Rotas fazem o papel de controller e de repositório
- **Anti-pattern:** AP-08 — Regra de negócio dentro do controller/rota
- **File:** `routes/task_routes.py:85-154` (`create_task`, 70 linhas), `routes/task_routes.py:156-223`, `routes/report_routes.py:12-101`, `routes/user_routes.py:42-90`
- **Description:** Os handlers validam, consultam o ORM (`Task.query`, `db.session`),
  aplicam regra, serializam e fazem commit. `services/` existe, mas
  `NotificationService` nunca é instanciado (grep de uso = 0) e `utils/helpers.py`
  (`process_task_data`, `validate_email`, constantes) não é importado por ninguém além
  de dois símbolos sem uso.
- **Impact:** A separação em pastas é só aparente: nenhuma regra pode ser testada sem
  HTTP e banco; a camada de serviço existente é código morto.
- **Recommendation:** Controllers por recurso (casos de uso), repositories para acesso
  a dados, rotas reduzidas a mapeamento HTTP e serviços injetados pelo factory
  (playbook P-04/P-08).

### #7 [HIGH] Regra de "task atrasada" duplicada em 6 lugares, ignorando `Task.is_overdue()`
- **Anti-pattern:** AP-08 — Regra de negócio fora do model
- **File:** `routes/task_routes.py:30-39, 71-80, 283-287`, `routes/user_routes.py:171-180`, `routes/report_routes.py:34-36, 132-135`; método órfão em `models/task.py:50-60`
- **Description:** A regra (vencida e status diferente de done/cancelled) é recopiada em
  cada handler enquanto o model já a implementa e nunca é chamado.
- **Impact:** Mudar a regra exige editar 6 pontos; esquecer um gera divergência
  silenciosa entre listagem, estatística e relatório.
- **Recommendation:** Usar `task.is_overdue()` em todos os pontos e filtrar candidatas
  no banco.

### #8 [MEDIUM] Queries N+1 em listagens e relatórios
- **Anti-pattern:** AP-10 — Query N+1
- **File:** `routes/task_routes.py:41-57`, `routes/user_routes.py:22`, `routes/report_routes.py:55-56`, `routes/report_routes.py:163`
- **Description:** `GET /tasks` faz `User.query.get` e `Category.query.get` por task;
  `GET /users` acessa `u.tasks` (lazy) por usuário; o resumo consulta tasks por usuário;
  `GET /categories` conta tasks por categoria. Nenhuma listagem é paginada.
- **Impact:** `GET /tasks` com 500 tasks = 1.001 queries; o custo cresce linearmente
  com a base em todas as listagens.
- **Recommendation:** `joinedload` para user/category, contagens com `GROUP BY` numa
  única query (playbook P-10).

### #9 [MEDIUM] APIs deprecated: `datetime.utcnow()` e `Query.get()`
- **Anti-pattern:** AP-09 — APIs deprecated / obsoletas
- **File:** `datetime.utcnow`: `models/task.py:15, 16, 52`, `models/user.py:14`, `models/category.py:11`, `routes/task_routes.py:31, 72, 215, 285`, `routes/report_routes.py:35, 42, 45, 71, 133`, `routes/user_routes.py:172`, `services/notification_service.py:35`, `utils/helpers.py:38`, `seed.py:66-74`; `Query.get`: `routes/task_routes.py:42, 51, 67, 117, 122, 158, 188, 195, 227`, `routes/user_routes.py:29, 94, 136, 155`, `routes/report_routes.py:105, 192, 213`
- **Description:** `datetime.utcnow()` é deprecated desde o Python 3.12 (ambiente
  detectado) e `Model.query.get()` é API legada no SQLAlchemy 2.x usado pelo
  Flask-SQLAlchemy 3.1.
- **Impact:** `DeprecationWarning`/`LegacyAPIWarning` hoje e quebra em versões
  futuras; `utcnow()` devolve datetime naive, fonte comum de erro de fuso.
- **Recommendation:** `datetime.now(timezone.utc)` (normalizado para naive UTC enquanto
  as colunas forem naive) e `db.session.get(Model, id)` / `select()` (playbook P-09).

### #10 [MEDIUM] `except:` nu descartando a causa do erro
- **Anti-pattern:** AP-12 — Tratamento de erro engolido ou inconsistente
- **File:** `routes/task_routes.py:62, 137, 204, 236`, `routes/user_routes.py:130, 149`, `routes/report_routes.py:186, 207, 221`, `utils/helpers.py:46, 49, 88`
- **Description:** 12 blocos `except:` sem classe nem log; a maior parte devolve
  `'Erro interno'`/`'Erro ao ...'` com 500. Outros caminhos (ex.: `priority` string em
  `task_routes.py:113`) não têm tratamento e caem no 500 padrão do Flask em HTML.
- **Impact:** Bugs viram 500 silenciosos sem stack trace; `except:` nu captura até
  `KeyboardInterrupt`; o formato de erro varia entre JSON e HTML.
- **Recommendation:** Erros de domínio tipados e handler central que faz rollback,
  loga a exceção e responde JSON consistente (playbook P-12).

### #11 [MEDIUM] Validação duplicada, divergente ou ausente — com helpers prontos e não usados
- **Anti-pattern:** AP-11 — Validação de entrada ausente ou duplicada
- **File:** `routes/task_routes.py:110, 177`, `models/task.py:39`, `utils/helpers.py:75, 110` (status); `routes/user_routes.py:61, 106`, `utils/helpers.py:21` (regex de e-mail); `routes/user_routes.py:71, 120`, `utils/helpers.py:111` (roles); `routes/report_routes.py:180, 196-202` (categoria)
- **Description:** A mesma lista de status/roles e o mesmo regex aparecem em 3-5
  lugares; `is_valid_color` (helpers.py:52) existe e `color` é gravado sem validação;
  `update_category` acessa `data` sem checar `None`; `priority` não tem checagem de tipo.
  `marshmallow` está declarado e não é usado.
- **Impact:** As cópias divergem com o tempo; payload sem JSON em `PUT /categories/<id>`
  gera 500; `color` de qualquer tamanho estoura o contrato da coluna `String(7)`.
- **Recommendation:** Constantes únicas no model, validação centralizada no controller
  (ou schema) e reutilização do validador de cor (playbook P-11).

### #12 [LOW] Imports mortos em quase todos os módulos
- **Anti-pattern:** AP-14 — Legibilidade
- **File:** `app.py:7` (`os`, `sys`, `json`), `routes/task_routes.py:7` (`json`, `os`, `sys`, `time`), `routes/user_routes.py:6` (`hashlib`, `json`), `routes/report_routes.py:7-8` (`format_date`, `calculate_percentage`, `json`), `models/task.py:3` (`json`), `utils/helpers.py:3-7`
- **Description:** Símbolos importados sem nenhum uso no arquivo (conferido por grep).
- **Impact:** Esconde as dependências reais; `hashlib` numa camada de rotas sugere que
  ela manipula senhas.
- **Recommendation:** Remover; apagar `utils/helpers.py` se nada dele for reaproveitado.

### #13 [LOW] Magic numbers de regra espalhados
- **Anti-pattern:** AP-14 — Legibilidade
- **File:** `routes/task_routes.py:96, 99, 113, 167, 169, 182`, `routes/user_routes.py:64, 115`, `routes/report_routes.py:45, 129`
- **Description:** `3`/`200` (título), `1`/`5` (prioridade), `4` (senha), `7` (dias) e
  `priority <= 2` ("alta prioridade") como literais — enquanto `MIN_TITLE_LENGTH`,
  `MAX_TITLE_LENGTH`, `MIN_PASSWORD_LENGTH` existem em `utils/helpers.py:112-114` sem uso.
- **Impact:** Regras de negócio invisíveis e fáceis de divergir entre criação e
  atualização.
- **Recommendation:** Constantes nomeadas junto do model/controller que as usa
  (playbook P-14).

### #14 [LOW] `print` como log
- **Anti-pattern:** AP-14 — Legibilidade
- **File:** `routes/task_routes.py:149, 153, 219, 234`, `routes/user_routes.py:83, 89, 147`, `services/notification_service.py:21, 24`, `utils/helpers.py:39, 41`
- **Description:** Eventos e erros registrados com `print`.
- **Impact:** Sem nível, timestamp ou stack trace; nada chega a um agregador de logs.
- **Recommendation:** `logging` com logger por módulo.

## Deprecated APIs
| API em uso | Arquivo:linha | Substituir por |
|---|---|---|
| `datetime.utcnow()` | `models/task.py:15, 16, 52`, `models/user.py:14`, `models/category.py:11`, rotas (ver #9) | `datetime.now(timezone.utc)` |
| `Model.query.get(id)` | `routes/task_routes.py:42`, `routes/user_routes.py:29`, `routes/report_routes.py:105` e mais 13 (ver #9) | `db.session.get(Model, id)` |
| `hashlib.md5` para senha | `models/user.py:29, 32` | `generate_password_hash` (scrypt/pbkdf2 com salt) |

## Categories Not Applicable
- AP-01 SQL Injection — todo acesso passa pelo ORM com parâmetros; não há SQL textual.
- AP-04 God Class — já existe divisão por arquivo/recurso; o maior arquivo (299 linhas)
  concentra uma camada (rotas de task), e o problema real está registrado em #6.
- AP-07 Estado global mutável — `db = SQLAlchemy()` é o padrão da extensão; a lista
  `notifications` do serviço seria estado em memória, mas o serviço nunca é instanciado.
- AP-13 Integridade referencial — FKs declaradas em `models/task.py:13-14`; o
  `DELETE /users/<id>` remove as tasks antes do usuário na mesma transação
  (`routes/user_routes.py:140-146`). Ressalva: `DELETE /categories/<id>` não trata as
  tasks da categoria (SQLite não aplica FK sem `PRAGMA foreign_keys`), anotado para a
  Fase 3.

## Architecture Assessment
**Current:** Parcialmente estruturada — existem `models/`, `routes/`, `services/` e
`utils/`, mas as rotas acessam o ORM diretamente e concentram toda a regra; `services/`
e `utils/` são praticamente código morto.
**Target:** MVC preservando o que funciona: `config/` (settings por env), `models/`
(ORM + regras da entidade), `repositories/` (consultas), `controllers/` (casos de uso),
`routes/` (Blueprints = views, só HTTP), `services/` (auth e notificação injetados),
`middlewares/` (auth, error handler) e `app.py` com application factory.
**Main structural gap:** Não há camada de controller: a regra mora nas rotas, enquanto
o model (`is_overdue`) e o serviço existentes não são usados.

================================
Total: 14 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
