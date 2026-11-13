# Saída final da Fase 3 — sessões reais de `/refactor-arch`

Transcrição da mensagem final de cada sessão do Claude Code, aberta dentro da pasta do
projeto com o código original (commit `0144531`, idêntico ao boilerplate `6d1ce62`),
uma sessão por projeto, invocando a skill `/refactor-arch` e gravando o relatório em
`reports/audit-project-{1,2,3}.md`.

Em cada sessão: Fase 1 impressa → Fase 2 gravou o relatório em `reports/` e parou em
`Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]` → resposta `y` → Fase 3.
As saídas da Fase 2 são os próprios arquivos `reports/audit-project-{1,2,3}.md`.

---

## Projeto 1 — `code-smells-project`

Refatoração concluída. As 19 rotas originais continuam respondendo (uma foi removida de propósito, por segurança), os 13 achados foram resolvidos e os 49 testes novos passam. Nada foi commitado: as mudanças estão no working tree.

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
code-smells-project/
├── app.py                  # composition root (create_app)
├── config.py               # Settings lidas do ambiente + leitor de .env
├── database.py             # conexão por requisição, transaction(), schema com FK/UNIQUE/CHECK
├── seed.py                 # admin vindo da config; dados de demonstração só fora de produção
├── errors.py               # erros de domínio: Validation/Unauthorized/Forbidden/NotFound/Conflict
├── models/                 # produto, usuario, pedido, sistema: SQL parametrizado + invariantes
├── services/               # pedido_service (checkout, cancelamento com estoque), relatorio, auth, notificador
├── controllers/            # produto, usuario, pedido, sistema + acesso.py (dono/admin/escopo)
├── routes/                 # Blueprints finos (views)
├── middlewares/            # auth.py (require_auth/require_admin), error_handler.py
├── tests/                  # 49 testes pytest
├── .env.example  .gitignore  README.md  requirements.txt
(removidos: controllers.py, models.py)

## Findings Resolved
CRITICAL: 5/5 | HIGH: 3/3 | MEDIUM: 4/4 | LOW: 1/1

## Contract Changes
- POST /admin/query removida → 404 (executava SQL arbitrário)
- POST /admin/reset-db: exige admin e ENABLE_RESET_DB=true fora de produção; sem isso → 403
- Autenticação: POST /login passa a devolver "token"; as rotas protegidas exigem
  Authorization: Bearer (sem token → 401, sem permissão → 403), conforme a matriz do README
- GET /usuarios e GET /pedidos: cliente recebe só os próprios registros; admin recebe todos
- POST /pedidos: usuario_id é opcional e assume o usuário do token; outro id só para admin
- GET /usuarios*: o campo "senha" saiu da resposta
- GET /health: saíram secret_key, db_path, debug e ambiente
- Cancelar um pedido agora devolve o estoque (correção de bug); um pedido cancelado não muda mais de status → 409
- PUT /pedidos/<id>/status com pedido inexistente → 404 (antes respondia 200)
- DELETE /produtos/<id> de produto que tem pedidos → 409 (antes deixava itens órfãos)
- Entrada inválida → 400 em vez de 500. PUT /produtos agora valida categoria e tamanho
  do nome; quantidade ≤ 0 é rejeitada; e-mail duplicado → 409
- Erros sempre no formato {"erro", "sucesso": false}; erro 500 não expõe detalhes internos
- Servidor sobe em 127.0.0.1 e o debug só liga por env, nunca em produção

## Validation
  [ok] Application boots without errors (e falha de propósito sem SECRET_KEY ou sem admin em produção)
  [ok] All endpoints respond correctly (19/19 rotas verificadas contra a linha de base)
  [ok] Anti-pattern signals no longer present
  [ok] Autorização: 11 rotas → 401 sem token / com token forjado; 9 → 403 para cliente não dono e não admin
  [ok] Concorrência: 8 escritas paralelas → 8×201; 14 compras paralelas com estoque 10 → 10×201, 4×400, estoque final 0
  [ok] pytest: 49 passed

## Pending
nada pendente
================================
```

**Bugs do original confirmados na execução e corrigidos:**
- **Login como admin sem senha:** o e-mail `admin@loja.com' --` entrava. Agora responde 401.
- **Quantidade negativa:** `quantidade: -5` aumentava o estoque e gerava pedido com total negativo. Agora responde 400.
- **Estoque no cancelamento:** cancelar um pedido não devolvia o estoque (o Mouse ficava em 48). Agora volta para 50.

**O que fazer agora:**
- **Trocar a `SECRET_KEY` antiga.** A chave `minha-chave-super-secreta-123` continua no histórico do git e deve ser considerada comprometida. Basta gerar uma nova para o `.env`.
- **Apagar `loja.db` se existir um da versão antiga.** O schema mudou (senha agora é hash, há FKs e e-mail único) e um banco antigo não funciona com o código novo. Hoje não há nenhum no projeto.

**Para saber:**
- Todos os greps de regressão voltaram vazios, exceto o de SQL injection. Esse ainda casa em models que montam SQL juntando constantes do próprio módulo (lista fixa de colunas, placeholders `?` e a lista fixa de tabelas do reset). Conferi uma por uma e nenhum valor vindo do cliente entra nessas strings.
- A porta 5000 é usada pelo AirPlay no macOS, por isso validei em 5055 (original) e 5056 (refatorado). Para rodar localmente, defina `PORT` no `.env`.
- O erro de `blake2` que aparece no log vem do Python instalado pelo pyenv, não do projeto. Ele já aparecia no original e o hash de senha funciona normalmente.

O relatório da auditoria está em `reports/audit-project-1.md`.

---

## Projeto 2 — `ecommerce-api-legacy`

Refatorei o projeto para MVC, a aplicação refatorada subiu e respondeu em todas as rotas, e os 13 achados da auditoria foram corrigidos. Nada foi commitado.

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
ecommerce-api-legacy/
├── .env.example
├── api.http                      (atualizado com login + Bearer)
├── README.md                     (atualizado)
├── package.json                  (+ engines node >=20.12; sem novas dependências)
└── src/
    ├── app.js                    # composition root: createApp() + start()
    ├── config/settings.js        # env, segredos sem default, admin obrigatório em produção
    ├── database/
    │   ├── connection.js         # sqlite3 em Promise + fila de transações
    │   ├── schema.js             # DDL com FK + ON DELETE CASCADE, UNIQUE(email)
    │   └── seed.js               # idempotente, nenhuma senha literal
    ├── domain/
    │   ├── constants.js          # Roles, PaymentStatus
    │   └── errors.js             # AppError, Validation, PaymentDenied, Unauthorized, Forbidden, NotFound
    ├── models/                   # user, course, enrollment, payment, audit-log
    ├── services/                 # checkout, financial-report, payment-gateway, password-hasher (scrypt), token
    ├── controllers/              # checkout, report, user, auth
    ├── validators/request-validators.js
    ├── routes/                   # checkout, auth, admin, user (Express Routers)
    └── middlewares/              # auth (authenticate/requireRole), error-handler, async-handler
(AppManager.js e utils.js removidos)

## Findings Resolved
CRITICAL: 5/5 | HIGH: 2/2 | MEDIUM: 5/5 | LOW: 1/1

## Contract Changes
1. Rota nova: POST /api/auth/login {email, password} → {token, token_type, expires_in}.
2. GET /api/admin/financial-report agora exige token de admin (401 sem token, 403 para aluno).
3. DELETE /api/users/:id agora exige token de admin ou do próprio usuário (401/403).
   Id inexistente → 404; id não numérico → 400. A mensagem de sucesso agora é
   "Usuário deletado", e matrículas e pagamentos do usuário são removidos junto (cascade).
4. Erros agora vêm em JSON {"error": "..."}. Antes vinham em texto puro; as mensagens e os
   status existentes foram mantidos.
5. Checkout com validação mais rígida:
   - e-mail precisa ter formato válido;
   - c_id precisa ser inteiro positivo;
   - card precisa ser uma string de 12–19 dígitos (espaços e hífens são aceitos);
   - JSON malformado → 400.
   Antes, card numérico derrubava o servidor.
6. Checkout sem pwd cria a conta com senha aleatória (antes era "123456").
   Pagamento recusado não cria mais o usuário (antes criava).
7. Erro de banco ao buscar o curso → 500 (antes devolvia 404 "Curso não encontrado").
8. O relatório agora sai ordenado por id do curso (antes a ordem variava).
9. O servidor escuta em 127.0.0.1 por padrão (HOST configurável).

## Validation
  [ok] Application boots without errors
       - sem os segredos, o boot falha com mensagem clara;
       - em produção, sem ADMIN_*, também falha.
  [ok] All endpoints respond correctly (4/4 rotas verificadas: as 3 originais + login, em 22 casos)
       - comparadas com o baseline: os mesmos status e corpos de sucesso;
       - 401 sem token, 403 com aluno, token de usuário apagado → 401;
       - senhas antigas "123"/"123456" não autenticam;
       - 16 checkouts em paralelo (8 com o mesmo e-mail): todos 200, sem BEGIN aninhado.
  [ok] Anti-pattern signals no longer present
       - os greps da Fase 2 voltaram zerados, com dois falsos positivos conferidos no trecho;
       - não sobrou SQL em routes/controllers/services.

## Pending
- Não há suíte de testes no projeto. Validei com curl contra o servidor real, sem criar
  testes automatizados.
- A chave pk_live e a senha do banco ficam no histórico do Git. Elas precisam ser
  rotacionadas fora do código.
================================
```

- **Bug grave no original:** o baseline confirmou que um `card` numérico derrubava o processo inteiro, não só devolvia 500. Agora devolve 400.
- **Arquivos:** os scripts do antes/depois ficaram no diretório temporário da sessão (fora do repositório). O relatório da Fase 2 está em `reports/audit-project-2.md`.
- **Processos:** encerrei os servidores que subi; as portas 3000 e 3011 estão livres.
- **Git:** as mudanças estão no working tree, não commitadas. Os commits anteriores do repositório seguem um padrão; se quiser, eu commito usando esse mesmo padrão.

---

## Projeto 3 — `task-manager-api`

A refatoração do `task-manager-api` terminou e foi validada com a aplicação rodando de verdade. Os 11 achados do relatório foram corrigidos e as 22 rotas continuam respondendo com o mesmo status e o mesmo formato de antes, exceto pelas mudanças de contrato listadas abaixo. Nada foi commitado.

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
task-manager-api/
├── app.py                      # composition root: create_app()
├── database.py                 # instância do SQLAlchemy + commit() da unidade de trabalho
├── errors.py                   # ValidationError/Unauthorized/Forbidden/NotFound/Conflict
├── seed.py                     # admin pelo ambiente; contas de exemplo só fora de produção; --reset
├── config/settings.py          # tudo lido do ambiente, SECRET_KEY sem default
├── models/                     # task.py, user.py, category.py: entidade, regras e consultas
├── validators/                 # common, task, user, category: fonte única de validação
├── controllers/                # task, user, category, report, auth + access.py (política de acesso)
├── routes/                     # task, user, category, report, system: só HTTP → controller
├── middlewares/                # auth.py (token assinado) + error_handler.py
├── utils/clock.py              # utcnow() sem API deprecated
├── tests/                      # conftest.py + test_authorization.py (46 casos)
├── .env.example  requirements.txt  requirements-dev.txt
Removidos: services/notification_service.py, utils/helpers.py (código morto)

## Findings Resolved
CRITICAL: 4/4 | HIGH: 2/2 | MEDIUM: 4/4 | LOW: 1/1

## Contract Changes
1. Autenticação obrigatória: todas as rotas exigem `Authorization: Bearer <token>`,
   exceto GET /, GET /health, POST /login e POST /users.
2. O token do /login agora é assinado e expira (antes era "fake-jwt-token-<id>").
3. Escopo por papel: um `user` só vê e altera as próprias tasks, o próprio cadastro e
   o próprio relatório. As listas, buscas, estatísticas e os task_count das categorias
   devolvem só o que é dele. /reports/summary e a escrita de categorias são só para
   admin/manager; DELETE /users e alterar role/active são só para admin.
3a. Para um `user`, POST /tasks sem user_id agora cria a task para ele mesmo.
    Antes ficava sem responsável.
4. POST /users público cria sempre o papel `user`; outro papel sem token de admin → 403.
5. Trocar a própria senha exige `current_password`.
6. O campo `password` (hash) saiu de todas as respostas.
7. Entrada malformada (prioridade em texto, título que não é string, corpo ausente)
   agora devolve 400 em vez de 500. A cor da categoria é validada (#RRGGBB).
   O e-mail passou a exigir TLD.
8. Erros 404/405 do framework agora vêm em JSON {"error": ...}.
9. seed.py não apaga mais nada sem `--reset`, e em produção recusa o reset e as contas de exemplo.

## Validation
  [ok] Application boots without errors (flask run na 5099; seed com -W error::DeprecationWarning)
  [ok] All endpoints respond correctly (22/22 rotas verificadas; diff antes/depois de 26
       chamadas: única diferença é a remoção de `password`)
  [ok] Anti-pattern signals no longer present (sobrou só hashlib.md5 em models/user.py:57, ver Pending)
  [ok] Authorization: 46/46 testes — 401 sem token em 18 rotas, 403 em 15 casos de outro
       usuário (incluindo leituras), escopo de leitura, mass assignment, seed de produção
       sem senha conhecida
  [ok] Concorrência: 8 POST /tasks em paralelo → 8×201, 8 tasks persistidas
  [ok] N+1: GET /tasks faz 4 queries fixas (antes 1+2N); /reports/summary faz 10 fixas
  [ok] Servidor encerrado

## Pending
- O hashlib.md5 que sobrou em models/user.py:57 é proposital. Ele só compara o hash legado
  e o regrava em scrypt no primeiro login. Pode sair depois que todos os usuários tiverem
  logado uma vez.
- A SECRET_KEY e a senha SMTP antigas estão no histórico do git: considere-as comprometidas
  e troque (rotação é ação externa ao código).
- O schema continua sendo criado por db.create_all(), agora explícito no factory.
  Não há ferramenta de migrations no projeto.
================================
```

Fora do código:
- Criei um `.env` local no projeto para rodar a validação, com uma `SECRET_KEY` aleatória e a porta 5099, porque a 5000 está ocupada pelo AirPlay do macOS. O arquivo está no `.gitignore`.
- As remoções de `services/` e `utils/helpers.py` estão só no diretório, sem nada no stage.
- Os outros dois projetos do repositório têm alterações não commitadas que não são minhas; não mexi neles.

O relatório da Fase 2 está em `reports/audit-project-3.md`.
