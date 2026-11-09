================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   Node.js (CommonJS) + Express ^4.18.2 (sqlite3 ^5.1.6, banco em memória)
Files:   3 analyzed | ~180 lines of code (src/AppManager.js 141, src/utils.js 25, src/app.js 14)
Date:    2026-11-09

> Saída da Fase 2 da skill `refactor-arch`, gerada sobre o código **original** do
> projeto (commit base do repositório, antes da Fase 3). Todas as referências
> `arquivo:linha` apontam para esse estado — para conferir, use
> `git show 6d1ce62:ecommerce-api-legacy/<arquivo>`.

## Summary
CRITICAL: 5 | HIGH: 2 | MEDIUM: 5 | LOW: 3

## Findings

### #1 [CRITICAL] Credenciais de produção e chave viva do gateway hardcoded
- **Anti-pattern:** AP-02 — Credenciais e segredos hardcoded
- **File:** `src/utils.js:1-7`
- **Description:** O objeto `config` versiona usuário e senha do banco
  (`senha_super_secreta_prod_123`), a chave do gateway de pagamento
  (`pk_live_1234567890abcdef`) e o usuário SMTP; a porta também é fixa.
- **Impact:** Quem lê o repositório (ou seu histórico) pode cobrar cartões com a conta
  da empresa e acessar o banco de produção. Remover a linha não basta: o segredo está
  no histórico do git.
- **Recommendation:** Módulo de configuração lendo variáveis de ambiente, segredo sem
  default em produção (falha no boot) e `.env.example` sem valores; **rotacionar** as
  chaves expostas (playbook P-02).

```javascript
const config = {
    dbUser: "admin_master",
    dbPass: "senha_super_secreta_prod_123",
    paymentGatewayKey: "pk_live_1234567890abcdef",
```

### #2 [CRITICAL] God Class `AppManager`: banco, schema, seed, rotas, pagamento e relatório no mesmo lugar
- **Anti-pattern:** AP-04 — God Class / God Method
- **File:** `src/AppManager.js:4-141`
- **Description:** A classe cria a conexão (7), define schema e seed (10-23), registra
  as três rotas (25-137), contém a regra de checkout e a "autorização" de pagamento
  (43-48), e monta o relatório financeiro (80-129). O nome genérico denuncia a
  responsabilidade indefinida.
- **Impact:** Impossível testar o checkout sem subir Express e SQLite juntos; qualquer
  mudança em um fluxo arrisca os outros. É a causa raiz dos achados #6 a #12.
- **Recommendation:** Separar em `config/`, `database/` (conexão, migrations, seed),
  `models/` por entidade, `services/` (checkout, relatório, usuário), `controllers/`,
  `routes/` (Routers) e `app.js` como composition root (playbook P-04).

### #3 [CRITICAL] Relatório financeiro e exclusão de usuário sem autenticação
- **Anti-pattern:** AP-05 — Endpoint administrativo sem autenticação
- **File:** `src/AppManager.js:80-129` (`GET /api/admin/financial-report`), `src/AppManager.js:131-137` (`DELETE /api/users/:id`)
- **Description:** Rotas administrativas registradas sem nenhum middleware; grep por
  `authorization|jwt|passport|session` no projeto retorna zero.
- **Impact:** Qualquer cliente lê o faturamento por curso com o nome de cada aluno
  (dado pessoal) e apaga usuários por id — reproduzido no baseline: `DELETE
  /api/users/2` sem credencial responde 200.
- **Recommendation:** Middleware de autenticação administrativa (token vindo do
  ambiente, comparação em tempo constante) aplicado às duas rotas (playbook P-05).

### #4 [CRITICAL] "Hash" de senha caseiro e reversível (`badCrypto`) e senha do seed em texto puro
- **Anti-pattern:** AP-03 — Senha em texto puro ou hash fraco
- **File:** `src/utils.js:17-23`, `src/AppManager.js:68`, `src/AppManager.js:18`
- **Description:** `badCrypto` repete 10.000 vezes os 2 primeiros caracteres do Base64
  da senha e devolve 10 caracteres — sem salt e determinístico. O usuário do seed é
  gravado com `pass = '123'` literal.
- **Impact:** Base64 é codificação, não hash: o resultado depende só dos primeiros
  caracteres da senha, então senhas diferentes colidem e o valor é trivialmente
  revertido por tabela. Vazou o banco, vazaram as senhas.
- **Recommendation:** KDF com salt (`crypto.scrypt` nativo do Node, ou bcrypt/argon2)
  para checkout e seed (playbook P-03).

```javascript
for(let i = 0; i < 10000; i++) {
    hash += Buffer.from(pwd).toString('base64').substring(0, 2);
}
return hash.substring(0, 10);
```

### #5 [CRITICAL] Número completo do cartão e chave do gateway escritos no log
- **Anti-pattern:** AP-02 — Credenciais e segredos hardcoded (exposição em log)
- **File:** `src/AppManager.js:45`
- **Description:** Cada checkout imprime o PAN completo e a chave do gateway
  (baseline: `Processando cartão 4111222233334444 na chave pk_live_...`).
- **Impact:** Violação direta de PCI-DSS: logs são agregados, retidos e lidos por
  muita gente; o número do cartão e a credencial do gateway ficam em claro em todos eles.
- **Recommendation:** Nunca logar PAN nem segredo; no máximo os 4 últimos dígitos
  mascarados, dentro de um gateway injetado.

```javascript
console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`);
```

### #6 [HIGH] Acoplamento direto ao driver e estado global mutável
- **Anti-pattern:** AP-07 — Estado global mutável compartilhado
- **File:** `src/AppManager.js:7`, `src/utils.js:9-15`, `src/AppManager.js:59`
- **Description:** O construtor instancia `new sqlite3.Database(':memory:')` — sem
  injeção, sem configuração; `globalCache` é um objeto de módulo que cresce a cada
  checkout (`logAndCache`) e nunca é lido nem limpo.
- **Impact:** Não há como apontar para outro banco por ambiente nem usar um duplo em
  teste; o cache global é vazamento de memória proporcional ao número de checkouts.
- **Recommendation:** Conexão criada no composition root e injetada nos models;
  eliminar o cache sem consumidor (playbook P-07).

### #7 [HIGH] Regra de negócio inteira dentro do handler HTTP de checkout
- **Anti-pattern:** AP-08 — Regra de negócio dentro do controller/rota
- **File:** `src/AppManager.js:28-78`
- **Description:** O handler de `POST /api/checkout` busca curso, decide aprovação do
  pagamento (46), cria usuário com senha default, matricula, registra pagamento e
  auditoria — 50 linhas e 5 níveis de callback dentro da rota.
- **Impact:** A regra de checkout não pode ser reutilizada nem testada sem HTTP; trocar
  a simulação de pagamento por um gateway real exige mexer no handler.
- **Recommendation:** `CheckoutService` com models, gateway e hasher injetados;
  controller fino e rota só com o contrato HTTP (playbook P-08).

### #8 [MEDIUM] Checkout sem transação e exclusão que deixa órfãos
- **Anti-pattern:** AP-13 — Integridade referencial não mantida
- **File:** `src/AppManager.js:50-63`, `src/AppManager.js:69`, `src/AppManager.js:131-137`, `src/AppManager.js:12-15`
- **Description:** Usuário, matrícula, pagamento e auditoria são gravados em
  callbacks encadeados sem `BEGIN/COMMIT/ROLLBACK`; o schema não tem FOREIGN KEY;
  `DELETE /api/users/:id` apaga só o usuário e a própria resposta admite que
  "as matrículas e pagamentos ficaram sujos no banco".
- **Impact:** Falha no INSERT de pagamento deixa aluno matriculado sem pagar. Após a
  exclusão, o relatório passa a listar o aluno como `Unknown` (reproduzido no baseline).
- **Recommendation:** Unit of Work com transação envolvendo as escritas do checkout;
  FKs com `ON DELETE CASCADE` e `PRAGMA foreign_keys = ON` (playbook P-13).

### #9 [MEDIUM] Query N+1 no relatório financeiro
- **Anti-pattern:** AP-10 — Query N+1
- **File:** `src/AppManager.js:83-106`
- **Description:** Uma query de cursos (83), uma de matrículas por curso (92) e duas
  por matrícula (104 usuário, 106 pagamento), sincronizadas por contadores manuais
  (`coursesPending`, `enrPending`).
- **Impact:** 1 + N + 2×M consultas por requisição; a resposta depende de contadores
  manuais e nunca é enviada se um callback intermediário falhar.
- **Recommendation:** Uma única query com `LEFT JOIN` (cursos → matrículas → usuários
  → pagamentos) e agregação em memória (playbook P-10).

### #10 [MEDIUM] Erros de banco ignorados em callbacks e respostas de erro inconsistentes
- **Anti-pattern:** AP-12 — Tratamento de erro engolido ou inconsistente
- **File:** `src/AppManager.js:92-93`, `src/AppManager.js:104-106`, `src/AppManager.js:57`, `src/AppManager.js:133-135`
- **Description:** O parâmetro `err` é recebido e nunca testado nessas linhas; em 93
  `enrollments.length` é acessado direto. Erros saem ora como texto (`"Erro DB"`), ora
  o fluxo segue como sucesso.
- **Impact:** Uma falha de banco no relatório lança `TypeError` dentro de um callback
  assíncrono, fora do Express, e derruba o processo; o DELETE responde 200 mesmo quando
  falha.
- **Recommendation:** Envolver o driver em promises, usar `async/await` com wrapper
  que encaminha rejeições, erros tipados e um middleware de erro único (playbook P-12).

### #11 [MEDIUM] Validação de entrada ausente no checkout e senha default pública
- **Anti-pattern:** AP-11 — Validação de entrada ausente ou duplicada
- **File:** `src/AppManager.js:35`, `src/AppManager.js:68`
- **Description:** O guard só checa presença de `usr`, `eml`, `c_id`, `card`; não há
  validação de formato (e-mail, número de cartão, id numérico) e `pwd` ausente vira
  `"123456"`.
- **Impact:** Contas reais são criadas com uma senha conhecida por qualquer um que leia
  o código; `card` não-string (ex.: número) derruba o handler em `cc.startsWith`.
- **Recommendation:** Validar o contrato na rota (tipos e formato) antes do serviço;
  manter o default por compatibilidade apenas se declarado, sempre com hash forte.

### #12 [MEDIUM] Pirâmide de callbacks no I/O (estilo de API legado)
- **Anti-pattern:** AP-09 — APIs deprecated / obsoletas
- **File:** `src/AppManager.js:37-77`, `src/AppManager.js:83-128`
- **Description:** Todo o I/O usa a API de callbacks do `sqlite3` com até 5 níveis de
  aninhamento e `const self = this` (26) para contornar o `this` das funções.
- **Impact:** Erros não propagam (ver #10), a ordem de execução depende de contadores
  manuais e não há como usar transação legível.
- **Recommendation:** Envolver o driver com `util.promisify`/Promises e reescrever com
  `async/await` (playbook P-09).

### #13 [LOW] Código morto: imports, chaves de configuração e cache sem uso
- **Anti-pattern:** AP-14 — Legibilidade
- **File:** `src/AppManager.js:2`, `src/utils.js:2-3, 5, 10`
- **Description:** `totalRevenue` é importado e nunca usado; `dbUser`, `dbPass` e
  `smtpUser` não são lidos por ninguém (a conexão é `:memory:` fixa).
- **Impact:** Sugere um faturamento acumulado e uma conexão configurável que não
  existem; confunde quem mantém.
- **Recommendation:** Remover o que não tem consumidor.

### #14 [LOW] Nomes opacos e magic values
- **Anti-pattern:** AP-14 — Legibilidade
- **File:** `src/AppManager.js:29-33`, `src/AppManager.js:46`, `src/utils.js:19`
- **Description:** Variáveis `u`, `e`, `p`, `cid`, `cc`; o literal `"4"` decide sozinho a
  aprovação do pagamento; `"PAID"`/`"DENIED"` repetidos sem enum; `10000` solto.
- **Impact:** A regra de aprovação fica invisível; cada leitura exige decifrar o fluxo.
- **Recommendation:** Nomes descritivos internos (mantendo `usr`/`eml`/... no
  contrato HTTP), enum `PaymentStatus` e constante nomeada (playbook P-14).

### #15 [LOW] Resposta de sucesso que documenta o próprio bug
- **Anti-pattern:** AP-14 — Legibilidade (contrato enganoso)
- **File:** `src/AppManager.js:131-137`
- **Description:** O DELETE responde sempre `200 "Usuário deletado, mas as matrículas e
  pagamentos ficaram sujos no banco."` — inclusive quando o id não existe.
- **Impact:** O cliente não distingue exclusão efetiva de id inexistente; a mensagem
  expõe detalhe interno.
- **Recommendation:** Responder 200 com mensagem neutra quando houve exclusão e 404
  quando nenhuma linha foi afetada.

## Deprecated APIs
| API em uso | Arquivo:linha | Substituir por |
|---|---|---|
| Callbacks aninhados do `sqlite3` para I/O | `src/AppManager.js:37-77, 83-128` | Promises + `async/await` (`util.promisify` ou wrapper) |

Varredura do catálogo (`new Buffer(`, `url.parse(`, `fs.exists(`, `createCipher(`,
`util.isArray`, `body-parser`) retornou zero; o projeto já usa `Buffer.from` e
`express.json()`.

## Categories Not Applicable
- AP-01 SQL Injection — todas as queries usam placeholders `?` (ex.: 37, 40, 50).
- AP-06 Debug ativo — não há flag de debug nem endpoint de configuração; a exposição
  em log está coberta em #5.

## Architecture Assessment
**Current:** Monolítica — uma God Class com banco, schema, rotas e regra; `app.js`
apenas instancia o `AppManager`.
**Target:** MVC com `config/`, `database/` (conexão com transação, migrations, seed),
`models/` por entidade, `services/` (checkout, relatório financeiro, usuário),
`controllers/`, `routes/` (Routers = views), `middlewares/` (auth admin, erros) e
`app.js` (factory) + `server.js` (entry point).
**Main structural gap:** O fluxo de checkout vive dentro do handler HTTP, sem
transação e sem dependências injetadas.

================================
Total: 15 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
