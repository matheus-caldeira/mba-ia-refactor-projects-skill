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
| Evidências das execuções | `docs/evidencias/` — saída final de cada sessão e log de validação |

O histórico do git segue a ordem do processo: criação e iterações da skill; depois, o
commit `0144531` devolve os três projetos ao código original mantendo só a skill, e a
skill é executada de verdade com `claude "/refactor-arch"` numa sessão por projeto —
um commit com o resultado de cada execução (relatório da Fase 2 + código da Fase 3).

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
| 7 | HIGH | Nenhuma rota identifica quem chama: dados e pedidos de qualquer usuário por id, pedido criado em nome de outro, catálogo e status alteráveis por qualquer um (`app.py:11-28`) | IDOR: enumerar `/pedidos/usuario/1..N` expõe o histórico de compras da base inteira. |
| 8 | MEDIUM | Estoque validado antes e separado da baixa (`models.py:144` vs `163-166`), sem transação | Pedidos simultâneos — ou o mesmo produto repetido no pedido — deixam o estoque negativo. |
| 9 | MEDIUM | N+1 nas listagens de pedidos (`models.py:188, 192, 220, 224`) | 1 + N + N×M queries por requisição. |
| 10 | MEDIUM | Validação duplicada e divergente entre criar/atualizar produto (`controllers.py:28-50` vs `72-90`); e-mail sem unicidade | O update aceita o que a criação recusa. |
| 11 | MEDIUM | 16 `except Exception` devolvendo `str(e)` ao cliente (`controllers.py`) | Vaza detalhes internos e achata 400/404/500 num só erro. |
| 12 | LOW | Magic numbers nas faixas de desconto (`models.py:256-262`) | Regra de preço invisível e fácil de quebrar. |
| 13 | LOW | Imports mortos (`models.py:2`, `database.py:2`) e serialização copiada em 7 funções | Ruído e correções que ficam pela metade. |

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
| 4 | CRITICAL | Token `fake-jwt-token-<id>` e nenhuma rota protegida; cadastro aceita `role: admin`; `PUT /users/<id>` troca senha e papel de qualquer usuário (`routes/user_routes.py:52, 71, 92-132, 210`) | Qualquer um vira admin, assume contas alheias e apaga usuários. |
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
| AP-05 | Endpoint sem autenticação/autorização, inclusive por objeto (IDOR) e campos privilegiados no payload | CRITICAL | Detecção por ausência e matriz rota × quem pode — P1, P2, P3 |
| AP-06 | Debug ativo e exposição de configuração | CRITICAL | `debug=True` + `0.0.0.0` = RCE no Werkzeug |
| AP-07 | Estado global mutável | HIGH | Conexão global (P1), driver instanciado na classe (P2) |
| AP-08 | Regra de negócio no controller/rota | HIGH | O anti-pattern central de MVC |
| AP-09 | **APIs deprecated** | HIGH/MEDIUM | Exigência do enunciado; tabelas Python e Node com o substituto exato |
| AP-10 | Query N+1 | MEDIUM | P1, P2 e P3 |
| AP-11 | Validação ausente ou duplicada | MEDIUM | Regras copiadas e divergentes |
| AP-12 | Erro engolido ou inconsistente | MEDIUM | `except` genérico, `err` ignorado |
| AP-13 | Integridade referencial, transação e corrida check-then-act | MEDIUM | Checkout sem transação, órfãos, estoque negativo |
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
   (`d3a3cf3ed782f6b071f2bcfe1217e317`) nas três cópias.

### Desafios encontrados e como resolvi

- **Projeto "parcialmente estruturado".** Pastas `models/`, `routes/`, `services/`
  sugerem que está tudo bem. O `project-analysis.md` manda abrir um arquivo de rota e
  checar se ele contém só mapeamento HTTP — foi assim que apareceu a regra de atraso
  copiada 6 vezes enquanto `Task.is_overdue()` existia sem uso.
- **Trocar API deprecated sem mudar comportamento.** `datetime.now(timezone.utc)`
  devolve datetime *aware*; as colunas guardam *naive*, e compará-los levanta
  `TypeError`. A solução é um módulo de relógio (`utils/clock.py` na execução final), que usa a API moderna e remove o
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
- **Iteração por revisão de segurança.** Uma revisão automática de segurança sobre a
  primeira rodada de refatorações achou o que a skill ainda não pedia: IDOR de leitura
  (listagens e buscas sem escopo do ator), seed com conta admin de senha conhecida e
  corrida check-then-act no estoque. Em vez de só corrigir o código, atualizei a skill:
  o AP-05 passou a cobrir autorização por objeto em escrita **e leitura** e campos
  privilegiados no payload, o AP-02 cobre seed privilegiado com senha conhecida, o AP-13
  cobre corrida check-then-act, o playbook mostra as correções e a Fase 3 exige
  verificar 401/403 de cada rota protegida e escrita concorrente.
- **Prova final: execução do zero.** Com a skill estabilizada, os três projetos voltaram
  ao código original (commit `0144531`) e a skill foi executada em sessões novas do
  Claude Code, uma por projeto, sem intervenção além do `y` da Fase 2. Os resultados
  abaixo são dessas execuções.

---

## C) Resultados

Tudo nesta seção vem das execuções reais de `/refactor-arch`, uma sessão do Claude Code
por projeto, partindo do código original. A saída final de cada sessão está em
[`docs/evidencias/fase3-saida-das-sessoes.md`](docs/evidencias/fase3-saida-das-sessoes.md).

### Fase 1 — análise

| | Projeto 1 | Projeto 2 | Projeto 3 |
|---|---|---|---|
| Linguagem | Python 3.12 | JavaScript (Node.js) | Python 3.12 |
| Framework | Flask 3.1.1 (+ flask-cors 5.0.1) | Express 4.18.2 | Flask 3.0.0 (+ Flask-SQLAlchemy 3.1.1) |
| Banco | SQLite via `sqlite3` cru | SQLite via `sqlite3` (callbacks) | SQLite via SQLAlchemy 2.x |
| Domínio | E-commerce: produtos, usuários, pedidos, relatório de vendas | LMS: cursos, checkout (matrícula + pagamento), relatório financeiro | Task Manager: tarefas, usuários com papéis, categorias, relatórios |
| Arquitetura | Monolítica, 4 arquivos por papel técnico sem fronteira | God Class `AppManager` | Parcialmente estruturada; rotas com ORM e regra, `services/`/`utils/` mortos |
| Arquivos analisados | 4 (~780 linhas) | 3 (~180 linhas) | 15 (~1158 linhas) |

### Resumo dos relatórios de auditoria (Fase 2)

| Projeto | CRITICAL | HIGH | MEDIUM | LOW | Total | APIs deprecated |
|---|---|---|---|---|---|---|
| 1 — [`code-smells-project`](reports/audit-project-1.md) | 5 | 3 | 4 | 1 | **13** | nenhuma encontrada (varredura registrada no relatório) |
| 2 — [`ecommerce-api-legacy`](reports/audit-project-2.md) | 5 | 2 | 5 | 1 | **13** | callbacks aninhados → `async/await` (#8) |
| 3 — [`task-manager-api`](reports/audit-project-3.md) | 4 | 2 | 4 | 1 | **11** | `Model.query.get()` (SQLAlchemy 2.x) e `datetime.utcnow()` (Python 3.12) (#7) |

Principais achados por projeto (todos com `arquivo:linha` do código original):

- **P1:** SQL Injection em todas as queries com parâmetro (login como admin com
  `admin@loja.com' --`), `/admin/query` executando SQL arbitrário sem autenticação,
  nenhuma autenticação/autorização (IDOR), senhas em texto puro devolvidas pela API,
  `SECRET_KEY` vazada no `/health` com debug ligado em `0.0.0.0`.
- **P2:** relatório financeiro e exclusão de usuários públicos, chave `pk_live` e senha do
  banco no código, "hash" caseiro reversível, cartão e chave do gateway no log, God
  Class `AppManager`.
- **P3:** token `fake-jwt-token-<id>` que nenhuma rota verifica (qualquer um vira admin),
  MD5 sem salt com o hash devolvido nas respostas, segredos SMTP e `SECRET_KEY` no
  código, debug do Werkzeug exposto, rotas fazendo papel de controller e repositório.

Os três relatórios terminam com `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]`,
e em todas as sessões nenhum arquivo do projeto foi alterado antes da resposta `y`.

### Antes / depois da estrutura

Contagens sem testes, `venv/`, `node_modules/` e a skill.

**Projeto 1** — 4 arquivos (780 linhas) → 30 arquivos (1.193 linhas) + 49 testes

```
ANTES              DEPOIS
app.py             app.py              composition root (create_app)
controllers.py     config.py           Settings lidas do ambiente (+ leitor de .env)
models.py          database.py         conexão por requisição, transaction(), schema com FK/UNIQUE/CHECK
database.py        seed.py             admin vindo da config; demonstração só fora de produção
                   errors.py           Validation/Unauthorized/Forbidden/NotFound/Conflict
                   models/             produto, usuario, pedido, sistema — SQL parametrizado
                   services/           pedido (checkout, cancelamento com estoque), relatório, auth, notificador
                   controllers/        produto, usuario, pedido, sistema + acesso.py (dono/admin/escopo)
                   routes/             Blueprints finos (camada View)
                   middlewares/        auth (require_auth/require_admin), error_handler
                   tests/              pytest
```

**Projeto 2** — 3 arquivos (180 linhas) → 29 arquivos (810 linhas)

```
ANTES                 DEPOIS
src/app.js            src/app.js            composition root: createApp() + start()
src/AppManager.js     src/config/           settings.js — env; segredos sem default
src/utils.js          src/database/         connection (Promise + fila de transações), schema (FK + CASCADE), seed
                      src/domain/           constants (Roles, PaymentStatus), errors
                      src/models/           user, course, enrollment, payment, audit-log
                      src/services/         checkout, financial-report, payment-gateway, password-hasher (scrypt), token
                      src/controllers/      checkout, report, user, auth
                      src/validators/       request-validators
                      src/routes/           Express Routers (camada View)
                      src/middlewares/      auth (authenticate/requireRole), error-handler, async-handler
```

**Projeto 3** — 15 arquivos (1.158 linhas) → 33 arquivos (1.487 linhas) + 46 testes

```
ANTES                                   DEPOIS
models/ routes/ services/ utils/        models/          entidade, regras e consultas (sem N+1)
app.py database.py seed.py              routes/          só HTTP → controller (+ category, system)
(rotas com ORM, validação e regra;      + config/        settings.py — tudo do ambiente
 services/ e utils/ sem uso)            + controllers/   task, user, category, report, auth + access.py
                                        + validators/    fonte única de validação
                                        + middlewares/   auth (token assinado) e error_handler
                                        + errors.py      erros tipados
                                        utils/clock.py   "agora" sem API deprecated
                                        removidos: services/notification_service.py, utils/helpers.py (código morto)
```

### Checklist de validação

`[x]` = verificado nas sessões de execução e conferido de novo na revisão (testes, boot
e roteiro de requisições em [`docs/evidencias/validacao-pos-refatoracao.log`](docs/evidencias/validacao-pos-refatoracao.log)).

| Item | P1 | P2 | P3 |
|---|:-:|:-:|:-:|
| **Fase 1** — linguagem detectada | [x] | [x] | [x] |
| Framework detectado | [x] | [x] | [x] |
| Domínio descrito corretamente | [x] | [x] | [x] |
| Nº de arquivos condiz com a realidade | [x] 4 | [x] 3 | [x] 15 |
| **Fase 2** — relatório segue o template | [x] | [x] | [x] |
| Cada finding com arquivo e linhas | [x] | [x] | [x] |
| Ordenados CRITICAL → LOW | [x] | [x] | [x] |
| Mínimo de 5 findings | [x] 13 | [x] 13 | [x] 11 |
| APIs deprecated (se aplicável) | [x] varredura sem ocorrência | [x] | [x] |
| Pausa e pede confirmação antes da Fase 3 | [x] | [x] | [x] |
| **Fase 3** — estrutura MVC | [x] | [x] | [x] |
| Config extraída (sem hardcoded) | [x] | [x] | [x] |
| Models criados para abstrair dados | [x] | [x] | [x] |
| Views/Routes separadas | [x] | [x] | [x] |
| Controllers concentram o fluxo | [x] | [x] | [x] |
| Error handling centralizado | [x] | [x] | [x] |
| Entry point claro | [x] | [x] | [x] |
| Aplicação inicia sem erros | [x] | [x] | [x] |
| Endpoints originais respondem | [x] 19/19 | [x] 3/3 (+ login novo, 22 casos) | [x] 22/22 |
| Achados resolvidos | 13/13 | 13/13 | 11/11 |
| Suíte automatizada | [x] 49 testes | — (validado com curl) | [x] 46 testes |

### Logs das aplicações rodando após a refatoração

Trecho de [`docs/evidencias/validacao-pos-refatoracao.log`](docs/evidencias/validacao-pos-refatoracao.log),
gerado por [`docs/evidencias/validar.sh`](docs/evidencias/validar.sh) sobre o código
refatorado (o corpo das respostas está truncado):

```
### Projeto 1 — code-smells-project (Python/Flask)
INFO __main__: Servidor em http://127.0.0.1:5191 (APP_ENV=development)
GET  /health                                     -> 200 | {"counts":{"pedidos":0,"produtos":10,"usuarios":3},"database":"connected","status":"ok",...
GET  /produtos                                   -> 200
GET  /produtos/busca?q=mouse                     -> 200
POST /login (SQL injection: admin@loja.com' --)  -> 401 | {"erro":"Email ou senha inválidos","sucesso":false}
GET  /usuarios (sem token)                       -> 401 | {"erro":"Token de acesso ausente","sucesso":false}
GET  /usuarios (admin)                           -> 200   (sem o campo "senha")
GET  /usuarios/1 (cliente joao)                  -> 403
POST /pedidos (cliente joao)                     -> 201 | {"dados":{"pedido_id":1,"total":89.9},...}
POST /pedidos (quantidade negativa)              -> 400 | {"erro":"Quantidade deve ser um inteiro maior que zero",...}
GET  /relatorios/vendas (admin)                  -> 200
POST /admin/query (removida)                     -> 404

### Projeto 2 — ecommerce-api-legacy (Node.js/Express)
LMS API rodando em http://127.0.0.1:3191
POST /api/checkout (cartão 4...)                 -> 200 | {"msg":"Sucesso","enrollment_id":2}
POST /api/checkout (cartão 5..., recusado)       -> 400 | {"error":"Pagamento recusado"}
POST /api/checkout (card numérico)               -> 400 | {"error":"Número de cartão inválido"}   (antes: derrubava o processo)
GET  /api/admin/financial-report (sem token)     -> 401 | {"error":"Não autenticado"}
GET  /api/admin/financial-report (admin)         -> 200 | [{"course":"Clean Architecture","revenue":997,...
DELETE /api/users/1 (sem token)                  -> 401

### Projeto 3 — task-manager-api (Python/Flask)
GET  /tasks (sem token)                          -> 401 | {"error":"Token de autenticação ausente"}
POST /login                                      -> 200 | {"token":"eyJ1aWQiOjJ9.avZVfg...", ...}   (antes: "fake-jwt-token-<id>")
GET  /tasks /tasks/1 /tasks/stats /tasks/search /users /users/1 /categories
     /reports/summary /reports/user/1 (admin)    -> 200 (todas)
GET  /reports/summary (user comum)               -> 403
POST /users com role=admin (anônimo)             -> 403
PUT  /users/1 role=user (user comum)             -> 403
ocorrências de "password" em GET /users/1        -> 0

pytest: code-smells-project 49 passed | task-manager-api 46 passed
```

Observação de ambiente: os projetos Python imprimem no boot
`ERROR:root:code for hash blake2b was not found`, ruído do `hashlib` do interpretador
pyenv local, não da aplicação; não afeta boot nem endpoints.

### Como a skill se comportou em stacks diferentes

- **Detecção pelo manifesto funcionou nos três**, e a distinção driver cru × ORM
  orientou a auditoria: SQL Injection e transação nos projetos com `sqlite3`; N+1 e
  APIs legadas do ORM no projeto SQLAlchemy.
- **Linha de base antes de mexer.** Nas três sessões a Fase 3 subiu o código original,
  registrou status e corpo de cada rota e só depois refatorou, comparando o antes e o
  depois. Foi assim que apareceram bugs do original além dos code smells: login como
  admin por SQL Injection, quantidade negativa aumentando o estoque e cancelamento que
  não devolvia estoque (P1), e `card` numérico derrubando o processo Node inteiro (P2).
- **A Fase 3 se adaptou ao ponto de partida.** P1 e P2 (monolíticos) ganharam todas as
  camadas; no P3 as pastas existentes foram mantidas, `controllers/`, `validators/` e
  `middlewares/` foram extraídos e o código morto de `services/` e `utils/` foi removido.
- **Mudanças de contrato explícitas.** Cada sessão listou o que mudou no contrato HTTP
  (rotas que passaram a exigir token, campos sensíveis removidos, 400 em vez de 500) —
  sempre por exigência de um achado da auditoria.
- **Ambiente real interfere.** No macOS a porta 5000 é do AirPlay; as sessões validaram
  em outras portas via `PORT`, que a refatoração passou a ler do ambiente.
- **Node exigiu cuidado extra com concorrência**: com uma única conexão e I/O
  assíncrono, transações explícitas se intercalam. A sessão do P2 criou uma fila de
  transações e validou 16 checkouts em paralelo — lição incorporada à skill numa
  iteração anterior.

### Limites desta entrega

- O P2 não ganhou suíte automatizada: a sessão validou com curl contra o servidor real
  (22 casos), mas não criou testes. Os projetos Python ganharam pytest.
- O P3 mantém `hashlib.md5` em `models/user.py:57` de propósito, só para reconhecer um
  hash legado e regravá-lo em scrypt no primeiro login; nenhuma senha nova usa MD5.
- Segredos que estavam no código original (`SECRET_KEY`, `pk_live`, senha SMTP)
  continuam no histórico do git e devem ser considerados comprometidos; a rotação é
  externa ao código.
- O envio real de e-mail do P3 não foi exercitado.

---

## D) Como Executar

### Pré-requisitos

- **Claude Code** instalado e autenticado (a skill segue a convenção `.claude/skills/`).
- **Python 3.12+** para os projetos 1 e 3, com `venv` **dentro da pasta do projeto**.
- **Node.js 20.12+** para o projeto 2 (usa `process.loadEnvFile`).
- Nenhuma chave de API externa: os três projetos usam SQLite.
- No macOS a porta 5000 costuma estar ocupada pelo Receptor AirPlay; use `PORT`.

### Executar a skill

Para reproduzir a execução sobre o código original:

```bash
git worktree add ../original 0144531     # código original + skill
cd ../original/code-smells-project   && claude "/refactor-arch ../reports/audit-project-1.md"
cd ../ecommerce-api-legacy           && claude "/refactor-arch ../reports/audit-project-2.md"
cd ../task-manager-api               && claude "/refactor-arch ../reports/audit-project-3.md"
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

### Validar a refatoração

Roteiro completo (sobe os três projetos, chama as rotas e derruba os servidores):

```bash
bash docs/evidencias/validar.sh "$PWD" "$(mktemp -d)"
```

Ou manualmente, por projeto (credenciais de exemplo valem só fora de produção):

**Projeto 1**

```bash
cd code-smells-project
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt pytest
./venv/bin/python -m pytest -q                                   # 49 passed
APP_ENV=development SECRET_KEY=$(openssl rand -hex 32) PORT=5001 ./venv/bin/python app.py
curl -s localhost:5001/health
TOKEN=$(curl -s -X POST localhost:5001/login -H 'Content-Type: application/json' \
     -d '{"email":"admin@loja.com","senha":"admin123"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
curl -s -o /dev/null -w '%{http_code}\n' localhost:5001/usuarios                        # 401
curl -s -H "Authorization: Bearer $TOKEN" localhost:5001/usuarios | grep -c '"senha"'    # 0
curl -s -o /dev/null -w '%{http_code}\n' -X POST localhost:5001/admin/query              # 404
```

**Projeto 2**

```bash
cd ecommerce-api-legacy && npm install
NODE_ENV=development PAYMENT_GATEWAY_KEY=pk_test_local AUTH_SECRET=$(openssl rand -hex 32) PORT=3000 npm start
curl -s -X POST localhost:3000/api/checkout -H 'Content-Type: application/json' \
  -d '{"usr":"Guilherme","eml":"gui@fullcycle.com.br","pwd":"senhaforte","c_id":2,"card":"4111222233334444"}'
curl -s -o /dev/null -w '%{http_code}\n' localhost:3000/api/admin/financial-report       # 401
TOKEN=$(curl -s -X POST localhost:3000/api/auth/login -H 'Content-Type: application/json' \
     -d '{"email":"admin@lms.local","password":"admin-dev-only"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
curl -s -H "Authorization: Bearer $TOKEN" localhost:3000/api/admin/financial-report      # 200
```

**Projeto 3**

```bash
cd task-manager-api
python3 -m venv venv && ./venv/bin/pip install -r requirements-dev.txt
./venv/bin/python -m pytest -q                                   # 46 passed
export SECRET_KEY=$(openssl rand -hex 32)
./venv/bin/python seed.py && PORT=5003 ./venv/bin/python app.py
curl -s -o /dev/null -w '%{http_code}\n' localhost:5003/tasks    # 401
TOKEN=$(curl -s -X POST localhost:5003/login -H 'Content-Type: application/json' \
     -d '{"email":"joao@email.com","password":"1234"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
curl -s -H "Authorization: Bearer $TOKEN" localhost:5003/tasks
curl -s -H "Authorization: Bearer $TOKEN" localhost:5003/users/1 | grep -c '"password"'   # 0
```

**Regressão dos anti-patterns** (cada comando deve retornar vazio):

```bash
grep -rnE "badCrypto|pk_live|senha_super_secreta" ecommerce-api-legacy/src
grep -rnE --exclude-dir={venv,.claude,tests} "datetime\.utcnow\(\)|\.query\.get\(|except *:" --include='*.py' task-manager-api
grep -rnE --exclude-dir={venv,.claude,tests} "minha-chave-super-secreta|super-secret-key-123|'senha123'" --include='*.py' code-smells-project task-manager-api
```
