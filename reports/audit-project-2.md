================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript (Node.js) + Express 4.18.2 (resolvido 4.22.1)
Files:   3 analyzed | ~180 lines of code
Date:    2026-11-12

## Summary
CRITICAL: 5 | HIGH: 2 | MEDIUM: 5 | LOW: 1

## Findings

### #1 [CRITICAL] Nenhuma autenticação: relatório financeiro e exclusão de usuários públicos
- **Anti-pattern:** AP-05 — Endpoint administrativo sem autenticação / IDOR
- **File:** `src/AppManager.js:80, 131-137`, `src/app.js:6,12`
- **Description:** Não existe nenhuma camada de autenticação ou autorização (grep por
  `authenticate|authorization|jwt|passport|session|token|req.headers` em `src/` retorna
  zero; o único middleware é `express.json()` em `app.js:6`). `GET /api/admin/financial-report`
  devolve receita por curso e o nome de cada aluno com o valor pago; `DELETE /api/users/:id`
  apaga qualquer usuário pelo id do path, sem verificar quem pede. `app.listen(config.port)`
  (`app.js:12`) escuta em todas as interfaces.
- **Impact:** Qualquer pessoa na rede obtém o faturamento e a lista de alunos pagantes com
  `curl /api/admin/financial-report`, e apaga todos os usuários iterando
  `curl -X DELETE /api/users/1..N`.
- **Recommendation:** Middleware de autenticação (token assinado com segredo vindo do
  ambiente) aplicado às rotas administrativas e de usuário; `financial-report` exige papel
  admin; `DELETE /api/users/:id` exige admin ou o próprio usuário (403 caso contrário).
  Matriz alvo: `POST /api/checkout` público · `GET /api/admin/financial-report` admin ·
  `DELETE /api/users/:id` admin ou próprio.

```javascript
app.get('/api/admin/financial-report', (req, res) => {
...
app.delete('/api/users/:id', (req, res) => {
    let id = req.params.id;
    this.db.run("DELETE FROM users WHERE id = ?", [id], (err) => {
```

### #2 [CRITICAL] Credenciais e chave de gateway de pagamento hardcoded
- **Anti-pattern:** AP-02 — Credenciais e segredos hardcoded
- **File:** `src/utils.js:1-7`
- **Description:** O objeto `config` contém como literais a senha do banco
  (`dbPass: "senha_super_secreta_prod_123"`), o usuário `admin_master`, a chave do gateway
  de pagamento de produção (`pk_live_1234567890abcdef`) e o usuário SMTP. Nada é lido de
  variável de ambiente; nem a porta.
- **Impact:** Qualquer pessoa com acesso ao repositório tem a chave live do gateway e a
  senha "de produção" do banco. Como estão versionadas, devem ser consideradas comprometidas.
- **Recommendation:** Módulo de configuração lendo `process.env` (`PORT`,
  `PAYMENT_GATEWAY_KEY`, ...), `.env.example` sem valores reais, boot falhando em produção
  sem os segredos obrigatórios; **rotacionar** a chave e a senha expostas. Remover
  `dbUser/dbPass/smtpUser`, que nem são usados.

```javascript
const config = {
    dbUser: "admin_master",
    dbPass: "senha_super_secreta_prod_123",
    paymentGatewayKey: "pk_live_1234567890abcdef",
```

### #3 [CRITICAL] "Hash" de senha caseiro reversível, senha em texto puro no seed e senha padrão fixa
- **Anti-pattern:** AP-03 — Senha em texto puro ou hash fraco
- **File:** `src/utils.js:17-23`, `src/AppManager.js:18, 68`
- **Description:** `badCrypto` codifica a senha em base64, pega os 2 primeiros caracteres e
  os repete — o "hash" depende apenas do **primeiro caractere e meio** da senha (ex.:
  `"senhaforte"` e `"se123"` geram o mesmo valor `c2c2c2c2c2`). Nenhum algoritmo forte é
  usado (grep `bcrypt|argon2|scrypt|pbkdf2|crypto.` retorna zero). O seed grava a senha
  `'123'` em texto puro; o checkout sem `pwd` cria a conta com a senha fixa `"123456"`.
- **Impact:** Quem obtiver a tabela `users` recupera o prefixo de toda senha instantaneamente,
  e o espaço de colisão é de ~4 mil valores — força bruta trivial. Contas criadas sem `pwd`
  têm senha conhecida por qualquer leitor do código.
- **Recommendation:** Substituir por `crypto.scrypt` (nativo do Node) com salt aleatório por
  usuário e comparação com `timingSafeEqual`; seed com hash; sem senha padrão — senha ausente
  gera senha aleatória (conta sem senha conhecida).

```javascript
function badCrypto(pwd) {
    let hash = "";
    for(let i = 0; i < 10000; i++) {
        hash += Buffer.from(pwd).toString('base64').substring(0, 2);
    }
    return hash.substring(0, 10);
```

### #4 [CRITICAL] Número do cartão e chave do gateway impressos em log
- **Anti-pattern:** AP-06 — Exposição de configuração / dados sensíveis
- **File:** `src/AppManager.js:45`
- **Description:** A cada checkout, o número completo do cartão (`cc`) e a
  `paymentGatewayKey` são escritos no stdout.
- **Impact:** Todo coletor de log (arquivo, agregador, terminal compartilhado) passa a
  armazenar PAN completo e a chave live do gateway — violação direta de PCI-DSS e vazamento
  ativo do segredo, mesmo depois de movê-lo para env var.
- **Recommendation:** Nunca logar o cartão nem a chave; se necessário, logar só os 4 últimos
  dígitos mascarados.

```javascript
console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`);
```

### #5 [CRITICAL] God Class `AppManager`: conexão, DDL, seed, rotas e regra de negócio juntos
- **Anti-pattern:** AP-04 — God Class / God Method
- **File:** `src/AppManager.js:4-139`
- **Description:** A classe de nome genérico cria a conexão SQLite (`:7`), executa o DDL e o
  seed (`:10-23`), registra as três rotas HTTP (`:25-138`), decide aprovação de pagamento
  (`:46`), cria usuário, matrícula, pagamento e auditoria (`:50-72`) e agrega o relatório
  financeiro (`:80-129`) — cinco entidades (users, courses, enrollments, payments,
  audit_logs) e quatro camadas no mesmo arquivo. O handler de checkout tem 50 linhas com 7
  níveis de aninhamento.
- **Impact:** Impossível testar a regra de checkout sem subir HTTP e banco; qualquer mudança
  em uma entidade arrisca as outras rotas; não há ponto para injetar um banco de teste.
- **Recommendation:** Separar em `config/`, `database/` (conexão + schema/seed), `models/`
  (um por entidade), `services/` (checkout, relatório), `controllers/`, `routes/` e
  `middlewares/`; `app.js` vira composition root.

```javascript
class AppManager {
    constructor() {
        this.db = new sqlite3.Database(':memory:');
    }
    initDb() {
```

### #6 [HIGH] Regra de negócio de checkout dentro do handler HTTP
- **Anti-pattern:** AP-08 — Regra de negócio dentro do controller/rota
- **File:** `src/AppManager.js:28-78`
- **Description:** O handler de `POST /api/checkout` decide aprovação do pagamento
  (`cc.startsWith("4")`, `:46`), cria o usuário quando o e-mail não existe (`:66-72`), grava
  matrícula, pagamento e auditoria (`:50-57`) e alimenta cache (`:59`) — tudo misturado à
  tradução HTTP. Para e-mail já existente, a senha enviada é ignorada e a compra é atribuída
  àquela conta.
- **Impact:** A regra de aprovação e o fluxo de matrícula não podem ser reutilizados nem
  testados isoladamente; trocar o gateway exige reescrever a rota.
- **Recommendation:** `CheckoutService.checkout(dados)` com um `PaymentGateway` injetado; o
  controller só valida o contrato, chama o serviço e mapeia o resultado para status HTTP.

### #7 [HIGH] Estado global mutável de módulo, sem limite, e exports mortos
- **Anti-pattern:** AP-07 — Estado global mutável compartilhado
- **File:** `src/utils.js:9-15, 25`, `src/AppManager.js:2, 59`
- **Description:** `globalCache` é um objeto de módulo que recebe uma chave
  `last_checkout_<userId>` por comprador e nunca é lido nem limpo; `totalRevenue` é um
  `let` exportado e importado em `AppManager.js:2` mas nunca usado. A conexão é criada dentro
  da classe, sem injeção.
- **Impact:** Crescimento de memória sem limite proporcional ao número de compradores; o
  estado compartilhado impede teste isolado e injeção de dublês.
- **Recommendation:** Remover o cache (não tem leitor) e `totalRevenue`; injetar a conexão
  de banco nos models via composition root.

### #8 [MEDIUM] Callbacks aninhados para I/O (callback hell) em vez de async/await
- **Anti-pattern:** AP-09 — APIs deprecated / obsoletas
- **File:** `src/AppManager.js:37-77, 83-128`
- **Description:** Todo acesso ao banco usa a API de callback do `sqlite3` aninhada até 6
  níveis; o checkout depende de `function(err)` para obter `this.lastID` e de `self = this`
  (`:26`) para alcançar a conexão.
- **Impact:** Controle de fluxo frágil — é essa estrutura que causa os erros engolidos (#11)
  e o contador manual de pendências do relatório (#9); torna transação e tratamento de erro
  centralizado inviáveis.
- **Recommendation:** Envolver o driver em funções `run/get/all` que retornam Promise e
  reescrever os fluxos com `async/await`.

### #9 [MEDIUM] Query N+1 no relatório financeiro
- **Anti-pattern:** AP-10 — Query N+1
- **File:** `src/AppManager.js:83-128`
- **Description:** Uma query para os cursos, uma por curso para as matrículas (`:92`) e duas
  por matrícula para usuário (`:104`) e pagamento (`:106`), coordenadas por contadores
  manuais `coursesPending/enrPending`.
- **Impact:** Com 10 cursos e 1000 matrículas, 2011 consultas por requisição; latência cresce
  linearmente com a base. A ordem dos cursos no JSON varia conforme a ordem de chegada dos
  callbacks.
- **Recommendation:** Uma query com `LEFT JOIN` courses→enrollments→users→payments ordenada
  por curso, agregada em memória.

### #10 [MEDIUM] Integridade referencial: exclusão deixa órfãos e checkout sem transação
- **Anti-pattern:** AP-13 — Integridade referencial não mantida
- **File:** `src/AppManager.js:12-16, 50-61, 131-137`
- **Description:** O DDL não declara nenhuma `FOREIGN KEY`. `DELETE /api/users/:id` apaga só
  o usuário — a própria resposta admite: "as matrículas e pagamentos ficaram sujos no
  banco". O checkout faz três `INSERT` encadeados (enrollment, payment, audit) sem transação
  (grep `BEGIN|COMMIT|transaction` retorna zero).
- **Impact:** Matrículas e pagamentos de usuário removido continuam somando receita no
  relatório como aluno "Unknown"; falha no INSERT de payment deixa matrícula sem pagamento
  (curso liberado sem cobrança registrada).
- **Recommendation:** FKs com `ON DELETE CASCADE` + `PRAGMA foreign_keys = ON` (ou exclusão
  explícita dos dependentes em transação) e checkout dentro de `BEGIN/COMMIT/ROLLBACK`.

### #11 [MEDIUM] Erros engolidos e respostas de erro inconsistentes
- **Anti-pattern:** AP-12 — Tratamento de erro engolido ou inconsistente
- **File:** `src/AppManager.js:38, 57, 92-93, 104-106, 133-135`
- **Description:** `err` é ignorado em `:57` (auditoria falha e o checkout responde sucesso),
  `:92` (com erro, `enrollments` é `undefined` e `enrollments.length` lança TypeError num
  callback — derruba o processo), `:104/:106` e `:133` (DELETE responde sucesso mesmo com
  erro ou id inexistente). Em `:38` erro de banco vira 404. Formatos misturam `res.send`
  texto puro e `res.json`.
- **Impact:** Um erro de banco no relatório mata o servidor inteiro; o cliente não distingue
  falha de sucesso no DELETE; operação recebe "Curso não encontrado" quando o banco caiu.
- **Recommendation:** Propagar erros para um error handler central do Express (500 com log,
  sem stack para o cliente); classes de erro de domínio (`NotFound`, `Validation`,
  `PaymentDenied`) mapeadas para 404/400; DELETE de id inexistente → 404.

### #12 [MEDIUM] Validação de entrada ausente no checkout e no id
- **Anti-pattern:** AP-11 — Validação de entrada ausente
- **File:** `src/AppManager.js:29-35, 132`
- **Description:** A única checagem é presença de `usr`, `eml`, `c_id`, `card` (`:35`). Não há
  validação de formato de e-mail, de `c_id` numérico, de `card` como string de dígitos (um
  `card` numérico faz `cc.startsWith` lançar TypeError — 500), nem do `:id` do DELETE.
- **Impact:** `{"card": 4111...}` (número em vez de string) derruba a requisição com 500;
  e-mails inválidos criam contas; ids não numéricos chegam ao banco.
- **Recommendation:** Validador do payload de checkout no controller (tipos e formatos),
  respondendo 400 com mensagem consistente; validar `:id` como inteiro positivo.

### #13 [LOW] Nomes opacos, magic numbers e código morto
- **Anti-pattern:** AP-14 — Legibilidade
- **File:** `src/AppManager.js:2, 26, 29-33, 46`, `src/utils.js:2, 5, 19, 25`
- **Description:** Variáveis `u`, `e`, `p`, `cid`, `cc` para dados de checkout; regra de
  aprovação com o literal `"4"`; laço de `10000` iterações sem significado; `self = this`;
  `totalRevenue`, `globalCache`, `dbUser`, `smtpUser` exportados/declarados sem uso; `let`
  onde o valor nunca muda.
- **Impact:** Custo de leitura em toda manutenção; a regra de aprovação fica escondida num
  literal.
- **Recommendation:** Renomear para `userName`, `email`, `password`, `courseId`, `cardNumber`
  (mantendo as chaves do payload `usr/eml/pwd/c_id/card`, que são contrato); constante
  nomeada para o prefixo aprovado; remover símbolos mortos; `const` por padrão.

## Deprecated APIs
| API em uso | Arquivo:linha | Substituir por |
|---|---|---|
| Callbacks aninhados do `sqlite3` para I/O | `src/AppManager.js:37-77, 83-128` | `async/await` sobre wrappers `util.promisify`/Promise |
| `let` para valores nunca reatribuídos | `src/AppManager.js:29-33, 81` | `const` |

Nenhuma das APIs pontuais do catálogo (`new Buffer`, `url.parse`, `body-parser`, `var`) foi
encontrada (grep retornou zero).

## Categories Not Applicable
- AP-01 SQL Injection — todas as queries usam placeholders `?` (ex.: `AppManager.js:37, 69,
  133`); grep de template literal e concatenação em SQL retornou zero. A única interpolação
  (`:57`) é no valor parametrizado, não no SQL.
- AP-06 Debug ativo — não há flag de debug nem `NODE_ENV` no código; o item registrado sob
  AP-06 (#4) é a exposição de segredo/cartão em log.

## Architecture Assessment
**Current:** Monolítica — `AppManager.js` concentra conexão, schema, seed, rotas, SQL e regra
de negócio; `utils.js` mistura config hardcoded, cache global e "criptografia".
**Target:** MVC com `config/` (env), `database/` (conexão Promise + schema/seed), `models/`
(User, Course, Enrollment, Payment, AuditLog), `services/` (Checkout, FinancialReport,
PaymentGateway, password), `controllers/`, `routes/` e `middlewares/` (auth, error handler).
**Main structural gap:** Não há fronteira entre HTTP e domínio — sem extrair a regra de
checkout e o acesso a dados do `AppManager`, nenhuma correção (transação, auth, erro
centralizado) tem onde morar.

================================
Total: 13 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
