# Skill de Auditoria e Refatoração Arquitetural — `refactor-arch`

Entrega do desafio **"Criação de Skills — Refatoração Arquitetural Automatizada"**.

`refactor-arch` é uma Custom Skill do **Claude Code** que audita um backend e o
refatora para o padrão MVC em três fases sequenciais — **Análise → Auditoria (com
pausa para confirmação) → Refatoração validada** — sem depender da stack. Ela foi
executada nos três projetos legados deste repositório: dois Python/Flask e um
Node.js/Express.

| Entregável | Onde está |
|---|---|
| Skill (SKILL.md + 5 arquivos de referência) | `<projeto>/.claude/skills/refactor-arch/` — cópia idêntica nos 3 projetos |
| Relatórios de auditoria (saída da Fase 2) | `reports/audit-project-{1,2,3}.md` |
| Código refatorado (saída da Fase 3) | `code-smells-project/`, `ecommerce-api-legacy/`, `task-manager-api/` |
| Código original (antes da Fase 3) | commit `6d1ce62` — base de todas as citações `arquivo:linha` dos relatórios |

O histórico do git segue a ordem do processo: skill + auditoria de cada projeto num
commit, a refatoração no commit seguinte, e as iterações da skill depois.

---

## A) Análise Manual

Feita lendo o código original de cada projeto, antes de escrever a skill. A
severidade segue a escala do enunciado (CRITICAL / HIGH / MEDIUM / LOW). As linhas
referem-se ao commit `6d1ce62`.

### Projeto 1 — `code-smells-project` (Python/Flask, API de e-commerce)

| # | Sev. | Problema | Por que é relevante |
|---|---|---|---|
| 1 | CRITICAL | SQL Injection: 19 queries montadas por concatenação (`models.py:28, 47-50, 109-111, 289-297`…) | O login é contornado com `{"email": "admin@loja.com' -- "}` — reproduzido: devolve 200 autenticado como Admin. Um `UNION SELECT` na busca exfiltra a tabela de usuários. |
| 2 | CRITICAL | `POST /admin/query` executa SQL arbitrário e `/admin/reset-db` apaga o banco, ambos sem autenticação (`app.py:47-78`) | Qualquer cliente lê as senhas (`SELECT email, senha FROM usuarios` funcionou no teste) ou destrói os dados. |
| 3 | CRITICAL | Senhas em texto puro, comparadas no SQL e devolvidas por `GET /usuarios` (`models.py:83, 99, 109-111, 126-129`) | Endpoint público entrega `admin@loja.com / admin123`. |
| 4 | CRITICAL | `SECRET_KEY` e `DEBUG=True` hardcoded, bind em `0.0.0.0`, e `/health` devolvendo a `secret_key` (`app.py:7-8, 88`; `controllers.py:285-289`) | Console do Werkzeug exposto na rede (RCE) e a chave de assinatura entregue por HTTP. |
| 5 | HIGH | Conexão SQLite global com `check_same_thread=False` (`database.py:4-12`) | Estado global mutável: requisições concorrentes compartilham a mesma transação; impede teste isolado. |
| 6 | HIGH | Regra de negócio no controller: notificações por `print` e "Devolver estoque" anunciado mas não implementado (`controllers.py:208-210, 247-250`) | Bug real: cancelar pedido nunca repõe estoque. |
| 7 | MEDIUM | N+1 nas listagens de pedidos (`models.py:188, 192, 220, 224`) | 1 + N + N×M queries por requisição. |
| 8 | MEDIUM | Validação duplicada e divergente entre criar/atualizar produto (`controllers.py:28-50` vs `72-90`); e-mail sem unicidade | O update aceita o que a criação recusa. |
| 9 | MEDIUM | 16 `except Exception` devolvendo `str(e)` ao cliente (`controllers.py`) | Vaza detalhes internos e achata 400/404/500 num só erro. |
| 10 | LOW | Magic numbers nas faixas de desconto (`models.py:256-262`) | Regra de preço invisível e fácil de quebrar. |
| 11 | LOW | Imports mortos (`models.py:2`, `database.py:2`) e serialização copiada em 7 funções | Ruído e correções que ficam pela metade. |

### Projeto 2 — `ecommerce-api-legacy` (Node.js/Express, LMS com checkout)

| # | Sev. | Problema | Por que é relevante |
|---|---|---|---|
| 1 | CRITICAL | Senha do banco e chave `pk_live_...` do gateway hardcoded (`src/utils.js:1-7`) | Quem lê o repositório cobra cartões com a conta da empresa; exige rotação. |
| 2 | CRITICAL | God Class `AppManager` com banco, schema, rotas, pagamento e relatório (`src/AppManager.js:4-141`) | Nada é testável isoladamente; raiz dos demais problemas. |
| 3 | CRITICAL | Relatório financeiro e `DELETE /api/users/:id` sem autenticação (`src/AppManager.js:80-137`) | Faturamento e dados de alunos expostos; exclusão aberta. |
| 4 | CRITICAL | "Hash" caseiro `badCrypto` (Base64 dos 2 primeiros caracteres) (`src/utils.js:17-23`) | Reversível, sem salt, com colisões. |
| 5 | CRITICAL | Número do cartão e chave do gateway no `console.log` (`src/AppManager.js:45`) | Violação de PCI-DSS. |
| 6 | HIGH | Regra de checkout inteira no handler HTTP, 5 níveis de callback (`src/AppManager.js:28-78`) | Não reutilizável nem testável sem HTTP. |
| 7 | MEDIUM | Checkout sem transação e DELETE que deixa órfãos (`src/AppManager.js:50-63, 131-137`) | Aluno matriculado sem pagamento; relatório passa a listar `Unknown`. |
| 8 | MEDIUM | N+1 no relatório financeiro (`src/AppManager.js:83-106`) | 1 + N + 2×M queries com contadores manuais. |
| 9 | MEDIUM | `err` ignorado em callbacks (`src/AppManager.js:92-106, 133`) | Uma falha de banco derruba o processo ou vira "sucesso". |
| 10 | LOW | Nomes opacos (`u`, `e`, `p`, `cid`, `cc`) e literal `"4"` decidindo o pagamento (`src/AppManager.js:29-46`) | Regra invisível. |
| 11 | LOW | Código morto: `totalRevenue`, `dbUser`, `smtpUser`, `globalCache` (`src/AppManager.js:2`; `src/utils.js:2-10`) | Sugere comportamento que não existe. |

### Projeto 3 — `task-manager-api` (Python/Flask, parcialmente estruturado)

| # | Sev. | Problema | Por que é relevante |
|---|---|---|---|
| 1 | CRITICAL | Senhas com MD5 sem salt (`models/user.py:27-32`) | Recuperáveis por rainbow table em segundos. |
| 2 | CRITICAL | `to_dict()` devolve o hash da senha em 4 endpoints (`models/user.py:21`) | Com MD5, equivale a vazar a senha. |
| 3 | CRITICAL | Credenciais SMTP hardcoded (`services/notification_service.py:7-10`) | Permite enviar e-mail em nome da aplicação. |
| 4 | CRITICAL | Token `fake-jwt-token-<id>` e nenhuma rota protegida; cadastro aceita `role: admin` (`routes/user_routes.py:52, 71, 210`) | Qualquer um vira admin e apaga usuários. |
| 5 | HIGH | Rotas fazem papel de controller e de repositório; `services/` e `utils/` não são usados (`routes/task_routes.py:85-154`…) | A separação em pastas é só aparente. |
| 6 | HIGH | Regra "atrasada" copiada em 6 lugares enquanto `Task.is_overdue()` nunca é chamado | Divergência silenciosa entre listagem e relatório. |
| 7 | MEDIUM | N+1 em `GET /tasks`, `/users`, `/categories` e no resumo | Medido: `GET /tasks` faz 17 queries com 10 tasks. |
| 8 | MEDIUM | APIs deprecated: `datetime.utcnow()` (Python 3.12) e `Query.get()` (SQLAlchemy 2.x) | Avisos hoje, quebra amanhã. |
| 9 | MEDIUM | 12 `except:` nus (`routes/task_routes.py:62`…) | Bugs viram 500 silenciosos. |
| 10 | LOW | Imports mortos (`import json, os, sys, time` em `routes/task_routes.py:7`…) | Esconde dependências reais. |
| 11 | LOW | Magic numbers (`3`, `200`, `1..5`, `priority <= 2`) com constantes equivalentes sem uso em `utils/helpers.py:112-114` | Regras espalhadas e divergentes. |

---

## B) Construção da Skill

### Decisões de design

- **SKILL.md é o procedimento; as referências são o conhecimento.** O `SKILL.md`
  descreve *o que fazer e em que ordem* (3 fases, formatos de saída, princípios
  inegociáveis) e manda carregar cada referência só na fase em que ela é usada:

  | Arquivo | Fase | Área de conhecimento exigida |
  |---|---|---|
  | `project-analysis.md` | 1 | Análise de projeto: linguagem, framework, banco, domínio, mapa da arquitetura |
  | `anti-patterns.md` | 2 | Catálogo de anti-patterns: 14 itens com sinais de detecção (grep) e severidade |
  | `report-template.md` | 2 | Template de relatório, com exemplo preenchido |
  | `architecture-guidelines.md` | 3 | Guidelines MVC: responsabilidades de Models, Views/Routes, Controllers, Services, Config, error handler e entry point |
  | `refactoring-playbook.md` | 3 | Playbook: 14 transformações com código antes/depois |

- **Fronteira dura entre auditar e modificar.** As Fases 1 e 2 são somente leitura;
  a única escrita permitida é o relatório. A Fase 2 termina imprimindo
  `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]` e espera um "sim"
  explícito.
- **Grep aponta candidatos; a leitura confirma.** Todo achado precisa de
  `arquivo:linha` lido de verdade. A *ausência* (ex.: nenhuma camada de autenticação)
  também é registrada, mas comprovada por busca.
- **Validação com execução real.** A Fase 3 só termina após subir a aplicação, chamar
  todas as rotas capturadas antes da refatoração, repetir os greps e — após a
  iteração descrita abaixo — testar escrita concorrente.
- **Destino do relatório configurável.** `/refactor-arch` salva em
  `reports/audit-<projeto>.md` na raiz do repositório git; `/refactor-arch
  <caminho>.md` salva no caminho indicado (usado para gerar `audit-project-N.md`).

### Anti-patterns do catálogo e por quê

| Código | Anti-pattern | Sev. | Motivação |
|---|---|---|---|
| AP-01 | SQL Injection por concatenação | CRITICAL | Bypass de login reproduzido no projeto 1 |
| AP-02 | Credenciais e segredos hardcoded | CRITICAL | Presente nos 3 projetos |
| AP-03 | Senha em texto puro ou hash fraco | CRITICAL | Texto puro (P1), caseiro (P2), MD5 (P3) |
| AP-04 | God Class / God Method | CRITICAL | `AppManager` (P2), `models.py` (P1) |
| AP-05 | Endpoint administrativo sem autenticação | CRITICAL | Detecção por ausência — P1, P2, P3 |
| AP-06 | Debug ativo e exposição de configuração | CRITICAL | `debug=True` + `0.0.0.0` = RCE no Werkzeug |
| AP-07 | Estado global mutável | HIGH | Conexão global (P1), driver instanciado na classe (P2) |
| AP-08 | Regra de negócio no controller/rota | HIGH | O anti-pattern central de MVC |
| AP-09 | **APIs deprecated** | HIGH/MEDIUM | Exigência do enunciado; tabelas Python e Node com o substituto exato |
| AP-10 | Query N+1 | MEDIUM | P1, P2 e P3 |
| AP-11 | Validação ausente ou duplicada | MEDIUM | Regras copiadas e divergentes |
| AP-12 | Erro engolido ou inconsistente | MEDIUM | `except` genérico, `err` ignorado |
| AP-13 | Integridade referencial / transação | MEDIUM | Checkout sem transação, órfãos |
| AP-14 | Legibilidade (nomes, magic numbers, imports mortos) | LOW | Garante detecção própria para o nível LOW |

### Como garanti o agnosticismo de tecnologia

1. **Stack detectada pelo manifesto**, nunca pelo nome das pastas (tabelas para
   Python, Node, Go, PHP, Java, Ruby e C#).
2. **Sinais de detecção pareados** em Python e JS/TS para cada anti-pattern, todos
   com `--exclude-dir` para `venv`, `node_modules` e a própria `.claude/`.
3. **Regras conceituais, sintaxe adaptável**: "cada camada conhece apenas a de baixo";
   em Flask as views são Blueprints, em Express são Routers.
4. **Adaptação ao ponto de partida**: a Fase 3 trata diferente um projeto monolítico
   (cria camadas) e um parcialmente estruturado (preserva o que funciona, extrai o que
   vaza, ativa o que está morto, apaga código morto).
5. **A mesma skill, byte a byte, nos 3 projetos** — `SKILL.md` com o mesmo MD5
   (`7ef3986a6652c6e0201402ba1c10d611`) nas três cópias.

### Desafios encontrados e como resolvi

- **Projeto "parcialmente estruturado".** Pastas `models/`, `routes/`, `services/`
  sugerem que está tudo bem. O `project-analysis.md` manda abrir um arquivo de rota e
  checar se ele contém só mapeamento HTTP — foi assim que apareceu a regra de atraso
  copiada 6 vezes enquanto `Task.is_overdue()` existia sem uso.
- **Trocar API deprecated sem mudar comportamento.** `datetime.now(timezone.utc)`
  devolve datetime *aware*; as colunas guardam *naive*, e compará-los levanta
  `TypeError`. A solução foi `models/clock.py`, que usa a API moderna e remove o
  `tzinfo`.
- **Greps que dão falso negativo ou falso positivo.** No zsh, `--include=*.py` sem
  aspas aborta com "no matches found" e parece "projeto limpo"; e a própria skill
  contém exemplos de código ruim. Todos os comandos usam aspas e excluem `.claude/`.
- **Regressão encontrada pela própria skill (iteração).** Rodei `/refactor-arch`
  sobre o projeto 2 *já refatorado*. A re-auditoria achou dois problemas
  introduzidos pela refatoração: (1) checkouts concorrentes respondiam **500**, porque
  a transação explícita sobre a conexão SQLite compartilhada gerava `BEGIN` aninhado
  (7 de 8 requisições paralelas falharam); (2) `ADMIN_API_TOKEN` tinha um valor
  default conhecido fora de produção. Corrigi os dois (fila de transações; rotas
  administrativas desabilitadas sem token) e incorporei a lição à skill: a Fase 3
  agora exige um teste de escrita concorrente, e o playbook P-13 mostra a
  serialização.
- **Preservar contrato x corrigir segurança.** Regra adotada: o contrato HTTP é
  mantido, exceto quando a auditoria exige o contrário (remover executor de SQL, parar
  de vazar campo sensível, exigir autenticação em operação destrutiva). Cada exceção
  está listada no README de cada projeto.

---

## C) Resultados

### Fase 1 — saída da análise

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python 3.12
Framework:     Flask 3.1.1
Dependencies:  flask-cors 5.0.1, sqlite3 (stdlib)
Domain:        E-commerce API (produtos, usuários, pedidos, relatório de vendas)
Architecture:  Monolítica — 4 arquivos com camadas só nominais; SQL, regra e formatação em models.py
Source files:  4 files analyzed (780 lines)
DB tables:     produtos, usuarios, pedidos, itens_pedido
================================

================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      JavaScript (Node.js, CommonJS)
Framework:     Express ^4.18.2
Dependencies:  sqlite3 ^5.1.6 (banco em memória)
Domain:        LMS — cursos online com checkout (matrícula + pagamento), relatório financeiro e auditoria
Architecture:  Monolítica — God Class AppManager com banco, rotas e regra
Source files:  3 files analyzed (180 lines)
DB tables:     users, courses, enrollments, payments, audit_logs
================================

================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python 3.12
Framework:     Flask 3.0.0
Dependencies:  Flask-SQLAlchemy 3.1.1, flask-cors 4.0.0, marshmallow 3.20.1 (não usado), python-dotenv (não usado)
Domain:        Task Manager — tarefas com prioridade, prazo e categoria, usuários com papéis e relatórios de produtividade
Architecture:  Parcialmente estruturada — models/routes/services/utils existem, mas as rotas acessam o ORM e concentram a regra
Source files:  15 files analyzed (1158 lines)
DB tables:     tasks, users, categories
================================
```

### Resumo dos relatórios de auditoria

| Projeto | Stack | CRITICAL | HIGH | MEDIUM | LOW | Total | APIs deprecated |
|---|---|---|---|---|---|---|---|
| 1 — `code-smells-project` | Python + Flask 3.1.1 | 5 | 2 | 4 | 4 | **15** | nenhuma encontrada (varredura registrada) |
| 2 — `ecommerce-api-legacy` | Node.js + Express 4.18 | 5 | 2 | 5 | 3 | **15** | callbacks aninhados → async/await |
| 3 — `task-manager-api` | Python + Flask 3.0.0 | 5 | 2 | 4 | 3 | **14** | `datetime.utcnow`, `Query.get`, `hashlib.md5` |

Os três relatórios terminam com `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]`.

### Antes / depois da estrutura

**Projeto 1** — 4 arquivos (780 linhas) → 25 arquivos (1.201 linhas)

```
ANTES                     DEPOIS
app.py                    app.py                     composition root (create_app)
controllers.py            config/settings.py         env vars; SECRET_KEY obrigatória em produção
models.py                 models/                    database (conexão por requisição), produto, usuario, pedido
database.py               controllers/               produto, usuario, pedido/relatório, sistema
                          services/                  pedido_service (transação, estoque), notificador
                          routes/                    Blueprints (camada View)
                          middlewares/               errors, error_handler, admin_auth
```

**Projeto 2** — 3 arquivos (180 linhas) → 26 arquivos (1.136 linhas)

```
ANTES                     DEPOIS
src/app.js                src/server.js              entry point
src/AppManager.js         src/app.js                 composition root (createApp)
src/utils.js              src/config/                settings (fail-fast em produção)
                          src/database/              conexão com Promises + transação, migrations (FKs), seed
                          src/models/                user, course, enrollment, payment, audit-log
                          src/services/              checkout, financial-report, user
                          src/controllers/           checkout, admin, user
                          src/routes/                Routers (camada View)
                          src/middlewares/           admin-auth, async-handler, error-handler
                          src/gateways/ src/security/ src/errors/
```

**Projeto 3** — 15 arquivos (1.158 linhas) → 30 arquivos (1.705 linhas)

```
ANTES                                  DEPOIS
models/ routes/ services/ utils/       + config/settings.py     configuração única
(rotas com ORM e regra,                + controllers/           task, user, category, report
 services/ e utils/ sem uso)           + repositories/          consultas sem N+1
                                       + middlewares/           auth (require_role) e error handler
                                       + models/clock.py        "agora" sem API deprecated
                                       + errors.py              erros tipados
                                       routes/ só mapeamento HTTP; utils/ removido
```

### Checklist de validação

`[x]` = verificado por execução ou leitura do código nesta entrega.

| Item | P1 | P2 | P3 |
|---|:-:|:-:|:-:|
| **Fase 1** — linguagem detectada | [x] | [x] | [x] |
| Framework detectado | [x] | [x] | [x] |
| Domínio descrito corretamente | [x] | [x] | [x] |
| Nº de arquivos condiz com a realidade | [x] 4 | [x] 3 | [x] 15 |
| **Fase 2** — relatório segue o template | [x] | [x] | [x] |
| Cada finding com arquivo e linhas | [x] | [x] | [x] |
| Ordenados CRITICAL → LOW | [x] | [x] | [x] |
| Mínimo de 5 findings | [x] 15 | [x] 15 | [x] 14 |
| APIs deprecated (se aplicável) | [x] varredura sem ocorrência | [x] | [x] |
| Pausa e pede confirmação antes da Fase 3 | [x] | [x] | [x] |
| **Fase 3** — estrutura MVC | [x] | [x] | [x] |
| Config extraída (sem hardcoded) | [x] | [x] | [x] |
| Models abstraem os dados | [x] | [x] | [x] |
| Views/Routes separadas | [x] | [x] | [x] |
| Controllers concentram o fluxo | [x] | [x] | [x] |
| Error handling centralizado | [x] | [x] | [x] |
| Entry point claro | [x] | [x] | [x] |
| Aplicação inicia sem erros | [x] | [x] | [x] |
| Endpoints originais respondem | [x] 33/33 | [x] 10/10 | [x] 35/35 |

### Logs das aplicações rodando após a refatoração

Cada projeto foi executado **antes** (código original) e **depois** com o mesmo
roteiro de requisições; a comparação é de status HTTP por chamada.

**Projeto 1** — `PORT=2533 ADMIN_TOKEN=dev-admin-token ./venv/bin/python app.py`

```
GET    /health                 -> 200 | {"counts":{"pedidos":0,"produtos":10,"usuarios":3},"database":"connected","status":"ok","versao":"1.0.0"}
GET    /produtos               -> 200 | {"dados":[{"ativo":1,"categoria":"informatica",...
POST   /produtos               -> 201 | {"dados":{"id":11},"mensagem":"Produto criado","sucesso":true}
GET    /usuarios               -> 200 | {"dados":[{"criado_em":"...","email":"admin@loja.com","id":1,"nome":"Admin","tipo":"admin"},...   (sem "senha")
POST   /login (admin123)       -> 200 | {"dados":{"email":"admin@loja.com","id":1,"nome":"Admin","tipo":"admin"},"mensagem":"Login OK","sucesso":true}
POST   /login (' -- )          -> 401 | {"erro":"Email ou senha inválidos","sucesso":false}        (antes: 200, bypass)
POST   /pedidos                -> 201 | {"dados":{"pedido_id":1,"total":6179.79},...}
GET    /relatorios/vendas      -> 200 | {"dados":{"desconto_aplicavel":308.99,"faturamento_bruto":6179.79,...}
POST   /admin/query            -> 404                                                           (antes: 200, SQL arbitrário)
POST   /admin/reset-db (token) -> 200 ; sem token -> 401
cancelar pedido de 3 notebooks: estoque 10 -> 7 -> 10                                           (antes: nunca devolvia)
8 POST /pedidos em paralelo  -> 201 x8
diff de status antes/depois: só /login com SQLi (200→401) e /admin/query (200→404)
```

**Projeto 2** — `PORT=2534 ADMIN_API_TOKEN=dev-admin-token npm start`

```
LMS API rodando na porta 2534 (env: development)
POST   /api/checkout (cartão 4...)       -> 200 | {"msg":"Sucesso","enrollment_id":2}
POST   /api/checkout (cartão 5...)       -> 400 | Pagamento recusado
POST   /api/checkout (sem campos)        -> 400 | Bad Request
GET    /api/admin/financial-report       -> 401 | Não autorizado
GET    /api/admin/financial-report + Bearer -> 200 | [{"course":"Clean Architecture","revenue":997,...},{"course":"Docker",...}]
DELETE /api/users/2 + Bearer             -> 200 | Usuário deletado, junto com suas matrículas e pagamentos.
[payment] autorização solicitada cartão=****4444 valor=497 ...      (antes: PAN completo e pk_live no log)
8 POST /api/checkout em paralelo         -> 200 x8   (antes da correção da iteração: 7 x 500)
NODE_ENV=production sem segredos         -> "Falha ao iniciar a aplicação: Variável de ambiente obrigatória ausente: PAYMENT_GATEWAY_KEY..."
```

**Projeto 3** — `SEED_PASSWORD=dev-password-123 ./venv/bin/python seed.py && PORT=2536 ./venv/bin/python app.py`

```
GET    /tasks                  -> 200 | [{"category_id":1,"category_name":"Backend",...,"overdue":true,...
GET    /tasks/stats            -> 200 | {"cancelled":1,"completion_rate":10.0,"done":1,"in_progress":2,"overdue":2,"pending":6,"total":10}
GET    /users/1                -> 200 | {...,"role":"admin","tasks":[...]}           (sem "password")
POST   /login                  -> 200 | {"message":"Login realizado com sucesso","token":"eyJ1c2VyX2lkIjoxLC...","user":{...}}
GET    /reports/summary        -> 200 | {"overdue":{"count":2,...
DELETE /users/3 sem token      -> 401 | {"error":"Token ausente"}
DELETE /users/3 token de user  -> 403 | {"error":"Acesso negado"}
DELETE /users/4 token de admin -> 200 | {"message":"Usuário deletado com sucesso"}
diff de status antes/depois (35 chamadas): nenhuma diferença
queries por requisição (antes -> depois): /tasks 17 -> 1, /users 4 -> 2, /categories 5 -> 2
```

Observação de ambiente: os projetos Python imprimem no boot
`ERROR:root:code for hash blake2b was not found`, ruído do `hashlib` do interpretador
pyenv local, não da aplicação; não afeta boot nem endpoints.

### Como a skill se comportou em stacks diferentes

- **Detecção pelo manifesto funcionou nos três**, e a distinção driver cru × ORM
  orientou a auditoria: SQL Injection e transação nos projetos com `sqlite3`; N+1 e
  APIs legadas do ORM no projeto SQLAlchemy.
- **A Fase 3 se adaptou ao ponto de partida.** P1 e P2 (monolíticos) ganharam todas as
  camadas; no P3 as pastas existentes foram mantidas, `controllers/` e `repositories/`
  foram extraídos, `is_overdue()` e o serviço de notificação passaram a ser usados e
  `utils/` (código morto) foi removido.
- **O nível MEDIUM/LOW é o mais fácil de perder** em projetos que "parecem
  organizados"; por isso a meta mínima de achados e o checklist de cobertura das 14
  categorias no fim do catálogo.
- **Node exigiu cuidado extra com concorrência**: com uma única conexão e I/O
  assíncrono, transações explícitas se intercalam — algo que não aparece nos projetos
  Flask (conexão/sessão por requisição). A skill agora testa isso.

### Limites desta entrega

- Os relatórios foram produzidos com o Claude Code seguindo o procedimento da skill
  sobre o código original. A invocação `/refactor-arch` foi exercitada
  diretamente na re-auditoria do projeto 2 refatorado (descrita acima). Não houve
  uma sessão interativa separada `claude "/refactor-arch"` respondendo `y` para cada
  projeto. As refatorações dos três projetos partiram de uma execução anterior da skill
  e foram revisadas, corrigidas e validadas nesta entrega.
- Não há suíte de testes automatizados nos projetos; a validação é o roteiro de
  requisições HTTP antes/depois descrito acima.
- O envio real de e-mail (SMTP) do projeto 3 não foi exercitado: sem `EMAIL_ENABLED`,
  o serviço apenas registra a notificação no log.

---

## D) Como Executar

### Pré-requisitos

- **Claude Code** instalado e autenticado (a skill segue a convenção `.claude/skills/`).
- **Python 3.12+** para os projetos 1 e 3, com `venv` **dentro da pasta do projeto**.
- **Node.js 18+** para o projeto 2.
- Nenhuma chave de API externa: os três projetos usam SQLite.

### Executar a skill

```bash
cd code-smells-project && claude "/refactor-arch ../reports/audit-project-1.md"
cd ../ecommerce-api-legacy && claude "/refactor-arch ../reports/audit-project-2.md"
cd ../task-manager-api && claude "/refactor-arch ../reports/audit-project-3.md"
```

Sem argumento (`claude "/refactor-arch"`), o relatório vai para
`reports/audit-<projeto>.md` na raiz do repositório. A Fase 1 imprime
`PHASE 1: PROJECT ANALYSIS`, a Fase 2 imprime e salva o relatório e **para** em
`Proceed with refactoring (Phase 3)? [y/n]`. Só após `y` a Fase 3 modifica arquivos.
Para usar em outro projeto, copie a pasta:

```bash
mkdir -p <outro-projeto>/.claude/skills
cp -r code-smells-project/.claude/skills/refactor-arch <outro-projeto>/.claude/skills/
```

> Os projetos aqui já estão refatorados; para reproduzir a auditoria sobre o código
> original, use `git worktree add ../original 6d1ce62` e execute a skill lá.

### Validar a refatoração

**Projeto 1**

```bash
cd code-smells-project
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
PORT=5001 ADMIN_TOKEN=dev-admin-token ./venv/bin/python app.py
curl -s localhost:5001/health
curl -s localhost:5001/usuarios | grep -c '"senha"'               # 0
curl -s -X POST localhost:5001/login -H 'Content-Type: application/json' \
     -d '{"email":"admin@loja.com","senha":"admin123"}'           # 200
curl -s -o /dev/null -w '%{http_code}\n' -X POST localhost:5001/login \
     -H 'Content-Type: application/json' -d "{\"email\":\"admin@loja.com' -- \",\"senha\":\"x\"}"   # 401
curl -s -o /dev/null -w '%{http_code}\n' -X POST localhost:5001/admin/query   # 404
```

**Projeto 2**

```bash
cd ecommerce-api-legacy && npm install
PORT=3000 ADMIN_API_TOKEN=dev-admin-token npm start
curl -s -X POST localhost:3000/api/checkout -H 'Content-Type: application/json' \
  -d '{"usr":"Guilherme","eml":"gui@fullcycle.com.br","pwd":"senhaforte","c_id":2,"card":"4111222233334444"}'
curl -s -o /dev/null -w '%{http_code}\n' localhost:3000/api/admin/financial-report          # 401
curl -s -H 'Authorization: Bearer dev-admin-token' localhost:3000/api/admin/financial-report  # 200
```

**Projeto 3**

```bash
cd task-manager-api
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
SEED_PASSWORD=dev-password-123 ./venv/bin/python seed.py
PORT=5003 ./venv/bin/python app.py
curl -s localhost:5003/tasks
curl -s localhost:5003/users/1 | grep -c '"password"'            # 0
curl -s -X POST localhost:5003/login -H 'Content-Type: application/json' \
     -d '{"email":"joao@email.com","password":"dev-password-123"}'   # 200 + token assinado
```

**Regressão dos anti-patterns** (cada comando deve retornar vazio):

```bash
grep -rnE --exclude-dir={venv,.claude} '(SELECT|INSERT|UPDATE|DELETE).*("[[:space:]]*\+|\+[[:space:]]*str\()' --include='*.py' code-smells-project
grep -rnE "badCrypto|pk_live|senha_super_secreta" ecommerce-api-legacy/src
grep -rnE --exclude-dir={venv,.claude} "datetime\.utcnow\(\)|\.query\.get\(|hashlib\.md5|except *:" --include='*.py' task-manager-api
```
