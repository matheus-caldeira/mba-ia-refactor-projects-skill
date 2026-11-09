# Template do Relatório de Auditoria — Fase 2

Formato obrigatório da saída da Fase 2. Imprima no terminal **e** salve no destino
definido no passo 7 da Fase 2 do `SKILL.md` (por padrão,
`reports/audit-<nome-do-projeto>.md` na raiz do repositório).

## Regras de preenchimento

1. **Ordenação por severidade:** CRITICAL → HIGH → MEDIUM → LOW. Dentro do mesmo
   nível, ordene por impacto.
2. **Numeração contínua** dos achados (`#1`, `#2`, ...), independente da severidade.
3. **`File:` sempre com linha ou faixa de linhas verificada** — `models.py:109-111`.
   Múltiplas ocorrências do mesmo problema: liste as linhas separadas por vírgula, ou
   uma faixa com "e mais N ocorrências" quando forem muitas.
4. **Os quatro campos são obrigatórios** em cada achado: Description, Impact,
   Recommendation e o código do anti-pattern (`AP-NN`).
5. **Description** diz o que o código faz — factual, verificável. **Impact** diz o
   que isso causa em operação — concreto, não genérico ("qualquer um que chamar
   `GET /usuarios` recebe as senhas", não "pode causar problemas de segurança").
6. **Recommendation** é acionável: o que fazer, não "melhorar o código".
7. **Trecho real** (opcional, recomendado em CRITICAL): até 6 linhas do código
   original, copiadas fielmente.
8. **Não invente achado para engordar o relatório.** Menos achados verificados vale
   mais que muitos achados especulativos.

---

## Formato

````markdown
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <nome do diretório do projeto>
Stack:   <linguagem> + <framework versão>
Files:   <N> analyzed | ~<M> lines of code
Date:    <YYYY-MM-DD>

## Summary
CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>

## Findings

### #<n> [<SEVERIDADE>] <Título curto do problema>
- **Anti-pattern:** AP-<NN> — <nome do anti-pattern>
- **File:** `<caminho>:<linhas>`
- **Description:** <o que o código faz, factual>
- **Impact:** <consequência concreta em operação>
- **Recommendation:** <ação específica de correção>

```<linguagem>
<trecho real do código, até 6 linhas>
```

<repetir para cada achado>

## Deprecated APIs
| API em uso | Arquivo:linha | Substituir por |
|---|---|---|
| <api> | <ref> | <equivalente moderno> |

<ou "Nenhuma API deprecated detectada.">

## Categories Not Applicable
<lista dos AP-NN investigados que não se aplicam a este projeto, com uma linha de
justificativa cada — prova que a varredura foi completa>

## Architecture Assessment
**Current:** <classificação da Fase 1 + uma frase>
**Target:** MVC com <camadas propostas para este projeto>
**Main structural gap:** <a mudança de maior impacto>

================================
Total: <N> findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
````

---

## Exemplo preenchido

O exemplo abaixo mostra o nível de especificidade esperado. Note que cada campo é
sustentado por evidência de leitura, e o Impact descreve um cenário real de
exploração, não uma preocupação abstrata.

````markdown
================================
ARCHITECTURE AUDIT REPORT
================================
Project: exemplo-api
Stack:   Python + Flask 3.1.1
Files:   6 analyzed | ~820 lines of code
Date:    2026-09-14

## Summary
CRITICAL: 3 | HIGH: 2 | MEDIUM: 2 | LOW: 1

## Findings

### #1 [CRITICAL] SQL Injection sistêmico por concatenação de strings
- **Anti-pattern:** AP-01 — SQL Injection por concatenação
- **File:** `models.py:109-111, 47-50, 126-129, 289-297` (22 ocorrências no arquivo)
- **Description:** Praticamente todas as queries montam SQL concatenando entrada do
  usuário na string, sem parametrização. `login_usuario` interpola `email` e `senha`
  vindos do corpo da requisição; `buscar_produtos` concatena o termo de busca dentro
  de um `LIKE`. O seed em `database.py:70-83` usa placeholders `?` corretamente,
  mostrando que a forma segura era conhecida.
- **Impact:** O login é contornável sem credencial com
  `{"email": "admin@loja.com' -- ", "senha": "x"}`, que trunca a verificação de senha
  e autentica como admin. Em `buscar_produtos`, um termo com `UNION SELECT` exfiltra
  a tabela de usuários inteira.
- **Recommendation:** Substituir toda concatenação por queries parametrizadas
  (`cursor.execute("SELECT * FROM produtos WHERE id = ?", (id,))`). Para filtros
  dinâmicos, acumular cláusulas com `?` e os valores numa lista de params.

```python
cursor.execute(
    "SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"
)
```

### #2 [HIGH] Estado global mutável compartilhado entre threads
- **Anti-pattern:** AP-07 — Estado global mutável
- **File:** `database.py:4-12`
- **Description:** Conexão única em variável global de módulo, criada com
  `check_same_thread=False`, compartilhada por todo o sistema. Não há `rollback`
  nem bloco transacional em nenhum arquivo (grep retornou zero).
- **Impact:** Com o servidor multi-thread, requisições concorrentes disputam a mesma
  conexão e o mesmo espaço de transação: um `commit` de uma requisição confirma
  escritas parcialmente aplicadas por outra. Também impede teste isolado, pois não
  há como injetar uma conexão de teste.
- **Recommendation:** Trocar o singleton por conexão de escopo de requisição
  (`g` + `teardown_appcontext` no Flask) ou pool, e injetar o repositório como
  dependência nas funções de dados.

### #3 [MEDIUM] Query N+1 na listagem
- **Anti-pattern:** AP-10 — Query N+1
- **File:** `routes/task_routes.py:41-57`
- **Description:** O laço sobre as tasks executa `User.query.get()` e
  `Category.query.get()` por item para resolver os nomes.
- **Impact:** Com 200 tasks, 401 consultas por requisição em vez de 1. A latência do
  endpoint cresce linearmente com a base.
- **Recommendation:** Carregar os relacionamentos com `joinedload`/`selectinload`, ou
  buscar os ids em lote e montar um dicionário antes do laço.

### #4 [LOW] Nomenclatura opaca e imports mortos
- **Anti-pattern:** AP-14 — Legibilidade
- **File:** `routes/task_routes.py:7`, `AppManager.js:29-33`
- **Description:** `import json, os, sys, time` com apenas `json` em uso; variáveis
  de checkout nomeadas `u`, `e`, `p`, `cid`, `cc`.
- **Impact:** Custo de leitura em toda manutenção futura; imports mortos escondem as
  dependências reais do módulo.
- **Recommendation:** Remover imports sem uso e renomear para `user_name`, `email`,
  `password`, `course_id`, `card_number`.

## Deprecated APIs
| API em uso | Arquivo:linha | Substituir por |
|---|---|---|
| `datetime.utcnow()` | `models/task.py:15-16`, `routes/report_routes.py:35` | `datetime.now(timezone.utc)` |
| `Model.query.get()` | `routes/user_routes.py:29`, `routes/task_routes.py:67` | `db.session.get(Model, id)` |
| `hashlib.md5` (senha) | `models/user.py:29,32` | `bcrypt` / `argon2` |

## Categories Not Applicable
- AP-05 Endpoint admin sem auth — não há rotas administrativas neste projeto.
- AP-13 Integridade referencial — FKs declaradas e cascade configurado nos models.

## Architecture Assessment
**Current:** Parcialmente estruturada — existem `models/`, `routes/` e `services/`,
mas as rotas acessam o ORM diretamente e concentram a regra de negócio.
**Target:** MVC com `config/`, `models/`, `controllers/`, `views/` (rotas),
`services/` e `middlewares/`.
**Main structural gap:** As rotas fazem o trabalho dos controllers; `services/`
existe mas não é chamado por ninguém.

================================
Total: 8 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
````
