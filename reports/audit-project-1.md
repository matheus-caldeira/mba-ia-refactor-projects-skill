================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python 3.12 + Flask 3.1.1 (flask-cors 5.0.1, sqlite3 da stdlib)
Files:   4 analyzed | ~780 lines of code (models.py 314, controllers.py 292, app.py 88, database.py 86)
Date:    2026-11-09

> Saída da Fase 2 da skill `refactor-arch`, gerada sobre o código **original** do
> projeto (commit base do repositório, antes da Fase 3). Todas as referências
> `arquivo:linha` apontam para esse estado — para conferir, use
> `git show 6d1ce62:code-smells-project/<arquivo>`.

## Summary
CRITICAL: 5 | HIGH: 3 | MEDIUM: 4 | LOW: 4

## Findings

### #1 [CRITICAL] SQL Injection sistêmico por concatenação de strings
- **Anti-pattern:** AP-01 — SQL Injection por concatenação
- **File:** `models.py:28, 47-50, 57-61, 68, 92, 109-111, 126-129, 140, 148-151, 155, 157-161, 163-166, 174, 188, 192, 220, 224, 279-281, 289-297` (19 statements)
- **Description:** Praticamente toda query monta o SQL concatenando valores vindos da
  requisição (`email`, `senha`, `nome`, termo de busca, `status`, ids). O único trecho
  parametrizado é o seed em `database.py:70-83`, prova de que a forma segura era
  conhecida e foi ignorada no resto.
- **Impact:** O login é contornado sem senha: `POST /login` com
  `{"email": "admin@loja.com' -- ", "senha": "x"}` devolve **200 autenticado como
  Admin** (reproduzido na execução de baseline). Em `/produtos/busca` um termo com
  `UNION SELECT` exfiltra a tabela `usuarios`; em `PUT /pedidos/<id>/status` o campo
  `status` permite reescrever qualquer coluna.
- **Recommendation:** Parametrizar 100% das queries (`?` + tupla de valores). No
  filtro dinâmico de busca, acumular cláusulas com placeholders e os valores numa
  lista (playbook P-01). Parar de comparar senha no SQL (ver #3).

```python
cursor.execute(
    "SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"
)
```

### #2 [CRITICAL] Endpoints administrativos sem autenticação, incluindo executor de SQL arbitrário
- **Anti-pattern:** AP-05 — Endpoint administrativo sem autenticação
- **File:** `app.py:59-78` (`POST /admin/query`), `app.py:47-57` (`POST /admin/reset-db`)
- **Description:** `/admin/query` executa qualquer SQL recebido no corpo; o
  `startswith("SELECT")` (linha 70) só decide entre `fetchall` e `commit`, não
  restringe nada. `/admin/reset-db` apaga as quatro tabelas. Nenhuma das duas exige
  identidade: `grep` por `before_request|login_required|Authorization|session[` no
  projeto retorna zero.
- **Impact:** Qualquer cliente lê `SELECT email, senha FROM usuarios` (baseline:
  devolveu todas as senhas em claro), executa `DROP TABLE` ou zera o banco com um POST.
  Com `host="0.0.0.0"` (app.py:88) a superfície é a rede inteira.
- **Recommendation:** Remover `/admin/query` (não há uso legítimo de SQL arbitrário
  via HTTP). Manter `/admin/reset-db` apenas atrás de token administrativo vindo do
  ambiente e indisponível em produção (playbook P-05). Declarar como mudança de contrato.

```python
@app.route("/admin/query", methods=["POST"])
def executar_query():
    dados = request.get_json()
    query = dados.get("sql", "")
    ...
        cursor.execute(query)
```

### #3 [CRITICAL] Senhas em texto puro, comparadas no SQL e devolvidas pela API
- **Anti-pattern:** AP-03 — Senha em texto puro ou hash fraco
- **File:** `models.py:126-129` (grava em claro), `models.py:109-111` (compara no SQL),
  `models.py:83, 99` (serializa `senha`), `database.py:75-79` (seed em claro)
- **Description:** Não existe hashing (grep por `bcrypt|argon2|scrypt|pbkdf2|werkzeug.security`
  retorna zero). `get_todos_usuarios` e `get_usuario_por_id` incluem o campo `senha`
  na resposta.
- **Impact:** `GET /usuarios` — endpoint público — devolve e-mail e senha de todos os
  usuários, inclusive `admin@loja.com / admin123` (confirmado no baseline). Além disso,
  o seed cria a conta **admin** com senha literal (`database.py:76`): mesmo com hash e
  autorização, qualquer leitor do repositório entraria como administrador. Qualquer
  vazamento do arquivo `loja.db` expõe as senhas diretamente.
- **Recommendation:** Gravar com `generate_password_hash`, verificar com
  `check_password_hash` em código (buscando só por e-mail) e serializar usuário por
  lista de permissão sem `senha` (playbook P-03). A conta admin deve vir de
  `ADMIN_EMAIL`/`ADMIN_PASSWORD` do ambiente (obrigatórias em produção) e as contas de
  exemplo só existir fora de produção (playbook P-02).

```python
"email": row["email"],
"senha": row["senha"],
"tipo": row["tipo"],
```

### #4 [CRITICAL] SECRET_KEY hardcoded, DEBUG ligado em 0.0.0.0 e segredo exposto no /health
- **Anti-pattern:** AP-02 — Credenciais hardcoded / AP-06 — Debug ativo e exposição de configuração
- **File:** `app.py:7-8`, `app.py:88`, `controllers.py:285-289`
- **Description:** `SECRET_KEY = "minha-chave-super-secreta-123"` e `DEBUG = True`
  literais; `app.run(host="0.0.0.0", port=5000, debug=True)`. O `/health` devolve
  `secret_key`, `debug`, `db_path` e `ambiente`.
- **Impact:** Com debug ligado e bind em todas as interfaces, o console interativo do
  Werkzeug fica acessível na rede (execução remota de código). A chave que assina
  sessões está no repositório **e** é entregue a qualquer um por `GET /health`.
- **Recommendation:** Módulo de configuração lendo variáveis de ambiente, sem segredo
  literal; `DEBUG` falso por padrão; bind em `127.0.0.1` por padrão; `/health` sem
  segredo nem configuração interna (playbook P-02 e P-06). Rotacionar a chave.

```python
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
app.config["DEBUG"] = True
```

### #5 [CRITICAL] God Module: models.py concentra dados, regra de negócio e formatação de quatro domínios
- **Anti-pattern:** AP-04 — God Class / God Method
- **File:** `models.py:1-314`
- **Description:** Um único módulo de 314 linhas contém SQL, serialização e regra de
  negócio de produtos, usuários, pedidos e relatórios: validação de estoque e cálculo
  de total do pedido (133-169), faixas de desconto do relatório (256-262), autenticação
  (105-120). Os "controllers" (`controllers.py`) também leem `request` e montam
  resposta, e `app.py` acessa o banco diretamente nas rotas `/admin/*` (49-55, 66-69),
  furando a própria divisão.
- **Impact:** Não há como testar a regra de pedido sem banco real; qualquer mudança em
  um domínio exige editar o arquivo de todos. A divisão em arquivos é nominal, não de
  responsabilidade.
- **Recommendation:** Um model por entidade (`produto_model`, `usuario_model`,
  `pedido_model`), regra que cruza entidades em `services/pedido_service`, rotas em
  Blueprints e `app.py` como composition root (playbook P-04/P-08).

### #6 [HIGH] Conexão SQLite global e mutável compartilhada entre threads
- **Anti-pattern:** AP-07 — Estado global mutável compartilhado
- **File:** `database.py:4-12`
- **Description:** `db_connection` é variável de módulo criada uma vez com
  `check_same_thread=False` e reutilizada por todas as requisições; o mesmo `get_db()`
  ainda cria o schema e o seed (14-84). Não há `rollback` em nenhum arquivo.
- **Impact:** O servidor do Flask é multi-thread: requisições concorrentes compartilham
  a mesma transação, e um `commit()` de uma confirma escritas parciais de outra.
  Impossível injetar uma conexão de teste.
- **Recommendation:** Conexão por requisição (`flask.g` + `teardown_appcontext`),
  schema/seed executados uma vez no boot pelo factory (playbook P-07).

```python
db_connection = None
...
        db_connection = sqlite3.connect(db_path, check_same_thread=False)
```

### #7 [HIGH] Regra de negócio e efeitos colaterais dentro dos controllers
- **Anti-pattern:** AP-08 — Regra de negócio dentro do controller/rota
- **File:** `controllers.py:208-210`, `controllers.py:247-250`, `controllers.py:52-54`, `controllers.py:242`
- **Description:** O controller dispara as "notificações" de e-mail/SMS/push com
  `print`, decide a lista de categorias e de status válidos inline e anuncia
  "Devolver estoque" ao cancelar — mas `models.atualizar_status_pedido` (models.py:275-283)
  só faz `UPDATE` do status.
- **Impact:** Bug de negócio real: cancelar um pedido **nunca** devolve o estoque.
  Efeitos colaterais acoplados ao handler HTTP não podem ser trocados por um canal real
  nem testados sem capturar stdout.
- **Recommendation:** Serviço de pedido com notificador injetado; cancelamento repõe
  estoque na mesma transação da mudança de status; enums de status/categoria num único
  lugar (playbook P-08).

```python
if novo_status == "cancelado":
    print("NOTIFICAÇÃO: Pedido " + str(pedido_id) + " cancelado. Devolver estoque.")
```

### #8 [HIGH] Dados e operações por usuário sem nenhuma verificação de identidade (IDOR)
- **Anti-pattern:** AP-05 — Endpoint sem autenticação/autorização (autorização por objeto)
- **File:** `app.py:18-19, 23-26, 11-16, 28`, `controllers.py:136-144` (`buscar_usuario`), `controllers.py:195-203` (`criar_pedido` usa `usuario_id` do corpo), `controllers.py:222-227` (`listar_pedidos_usuario`)
- **Description:** O `POST /login` não emite credencial nenhuma, e nenhuma rota identifica
  quem chama. O id do usuário vem do path ou do corpo e é aceito como está: qualquer
  cliente lê os dados e os pedidos de qualquer usuário, cria pedidos em nome de outro,
  lista todos os usuários e todos os pedidos, altera o catálogo
  (`POST/PUT/DELETE /produtos`), muda o status de qualquer pedido e lê o relatório de
  faturamento.
- **Impact:** Não existe fronteira entre cliente e administrador: enumerar
  `/pedidos/usuario/1..N` expõe o histórico de compra de toda a base, e um cliente
  cancela ou aprova pedidos alheios.
- **Recommendation:** Token assinado emitido no login; operações de catálogo, de status
  de pedido, listagens globais e relatórios restritas a `tipo = admin`; rotas por
  usuário restritas ao próprio usuário ou a admin (playbook P-05).

### #9 [MEDIUM] Criação de pedido sem transação, com corrida no estoque, e schema sem integridade referencial
- **Anti-pattern:** AP-13 — Integridade referencial não mantida
- **File:** `models.py:133-169`, `database.py:36-53`
- **Description:** `criar_pedido` insere o pedido, cada item e a baixa de estoque em
  statements separados sem `try/rollback`; o produto é consultado duas vezes por item
  (140 e 155). O schema declara `usuario_id`, `pedido_id` e `produto_id` sem
  `FOREIGN KEY` (grep por `FOREIGN KEY|REFERENCES` = 0) e `deletar_produto` faz DELETE
  físico (models.py:68).
- **Impact:** Uma falha no meio do laço deixa pedido sem itens ou estoque baixado sem
  pedido; a checagem de estoque (144) é feita antes e separada da baixa (163-166), então
  dois pedidos simultâneos — ou o mesmo produto repetido em dois itens do mesmo pedido —
  passam pela validação e deixam o estoque negativo; excluir um produto deixa `itens_pedido` apontando para um id inexistente
  (a listagem mostra "Desconhecido").
- **Recommendation:** Envolver pedido + itens + estoque numa transação única, baixar o
  estoque com UPDATE condicional (`... WHERE id = ? AND estoque >= ?`) conferindo as
  linhas afetadas, somar quantidades repetidas antes de validar, e declarar as FKs com
  `PRAGMA foreign_keys = ON` (playbook P-13).

### #10 [MEDIUM] Query N+1 nas listagens de pedidos
- **Anti-pattern:** AP-10 — Query N+1
- **File:** `models.py:171-201` (`get_pedidos_usuario`), `models.py:203-233` (`get_todos_pedidos`)
- **Description:** Para cada pedido, uma query de itens (188, 220); para cada item, uma
  query só para obter o nome do produto (192, 224).
- **Impact:** 1 + N + N×M queries por requisição em `GET /pedidos`; com 1.000 pedidos
  de 3 itens são ~4.000 idas ao banco numa conexão compartilhada.
- **Recommendation:** Uma query de pedidos e uma de itens com `LEFT JOIN produtos`,
  agrupando em memória por `pedido_id` (playbook P-10).

### #11 [MEDIUM] Validação duplicada, divergente ou ausente nos handlers
- **Anti-pattern:** AP-11 — Validação de entrada ausente ou duplicada
- **File:** `controllers.py:28-50` vs `controllers.py:72-90`, `controllers.py:146-162`, `controllers.py:169-170`, `controllers.py:239-240`
- **Description:** A validação de produto é copiada entre criar e atualizar, mas o
  update não verifica tamanho do nome nem categoria; `criar_usuario` não valida formato
  nem unicidade do e-mail (o schema não tem `UNIQUE`, database.py:30); `login` e
  `atualizar_status_pedido` chamam `dados.get` sem checar corpo nulo; `preco`/`estoque`
  não são checados quanto ao tipo.
- **Impact:** O update aceita o que a criação recusa; dois usuários com o mesmo e-mail
  são aceitos; uma requisição sem JSON vira 500 com stack interna em vez de 400.
- **Recommendation:** Uma função de validação por entidade, reutilizada em criar e
  atualizar; unicidade de e-mail no model e no schema; erros de validação como exceção
  tipada tratada pelo handler central (playbook P-11).

### #12 [MEDIUM] 16 blocos `except Exception` devolvendo `str(e)` ao cliente
- **Anti-pattern:** AP-12 — Tratamento de erro engolido ou inconsistente
- **File:** `controllers.py:10, 21, 60, 95, 108, 125, 133, 143, 164, 185, 218, 226, 234, 254, 261, 291`, `app.py:77-78`
- **Description:** Cada handler captura qualquer exceção e responde 500 com a mensagem
  crua; formatos de erro variam (`{"erro"}`, `{"erro","sucesso"}`, `{"status","detalhes"}`).
- **Impact:** Mensagens do SQLite (com trechos de SQL) vazam ao cliente; validação,
  ausência e falha interna viram o mesmo 500; não há log com stack trace.
- **Recommendation:** Erros de domínio tipados (`ValidationError`, `NotFoundError`,
  `ConflictError`, `UnauthorizedError`) e um único `errorhandler` que loga o stack e
  devolve mensagem genérica em 500 (playbook P-12).

### #13 [LOW] Imports não utilizados
- **Anti-pattern:** AP-14 — Legibilidade
- **File:** `models.py:2`, `database.py:2`
- **Description:** `models.py` importa `sqlite3` e `database.py` importa `os` sem
  nenhum uso (grep do símbolo no arquivo = só a linha do import).
- **Impact:** Sugere dependências que não existem (o caminho do banco segue hardcoded
  em `database.py:5` apesar do `import os`).
- **Recommendation:** Remover os imports; ler o caminho do banco da configuração.

### #14 [LOW] Magic numbers e literais de status espalhados
- **Anti-pattern:** AP-14 — Legibilidade
- **File:** `models.py:256-262`, `models.py:247-254`, `controllers.py:242`
- **Description:** Faixas de desconto como seis literais soltos (10000/5000/1000 e
  0.1/0.05/0.02) num if/elif; os status `'pendente'`, `'aprovado'`, `'cancelado'` são
  repetidos como strings em SQL e no controller.
- **Impact:** Alterar uma alíquota sem o limiar correspondente passa despercebido;
  um status digitado errado em um dos pontos não é detectado.
- **Recommendation:** Constante `FAIXAS_DESCONTO` e enum `StatusPedido` (playbook P-14).

### #15 [LOW] Serialização copiada literalmente em várias funções
- **Anti-pattern:** AP-14 — Legibilidade (duplicação)
- **File:** `models.py:12-21, 31-40, 304-313` (produto), `models.py:79-86, 95-102` (usuário), `models.py:178-185, 211-218` (pedido)
- **Description:** O mesmo dicionário campo a campo repetido em cada função de leitura.
- **Impact:** Corrigir um vazamento (ex.: o campo `senha`, #3) exige editar todas as
  cópias; esquecer uma mantém o problema.
- **Recommendation:** Uma função `serializar(row)` por entidade com lista de campos
  públicos.

### #16 [LOW] `print` usado como log em todo o projeto
- **Anti-pattern:** AP-14 — Legibilidade
- **File:** `controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 219`, `app.py:56, 83-86`
- **Description:** Eventos e erros registrados com `print` e concatenação de string,
  inclusive o e-mail de quem tentou login (179, 182).
- **Impact:** Sem nível, sem timestamp, sem stack trace; dado pessoal vai para stdout
  sem controle.
- **Recommendation:** Módulo `logging` com logger por módulo e sem dados pessoais nas
  mensagens.

## Deprecated APIs
Nenhuma API deprecated detectada. A varredura do catálogo (AP-09:
`datetime.utcnow`, `.query.get(`, `hashlib.md5/sha1`, `before_first_request`,
`distutils`, `verify=False`) nos 4 arquivos retornou zero ocorrências; o projeto usa
`sqlite3` puro e `CURRENT_TIMESTAMP` no schema. A ausência de `md5` aqui não é mérito:
decorre de não haver hash algum (#3).

## Categories Not Applicable
- Nenhuma das 14 categorias foi descartada: AP-09 foi investigado e está registrado na
  seção acima como "nenhuma ocorrência".

## Architecture Assessment
**Current:** Monolítica — 4 arquivos com camadas apenas nominais: `models.py` mistura
SQL, regra e formatação de 4 domínios; `controllers.py` lê `request` e devolve
`jsonify`; `app.py` declara rotas e acessa o banco direto.
**Target:** MVC com `config/` (settings por env), `models/` (um por entidade + conexão
por requisição), `controllers/` (casos de uso), `services/` (pedido e relatório, com
notificador injetado), `routes/` (Blueprints = views), `middlewares/` (erros tipados e
handler central) e `app.py` como composition root.
**Main structural gap:** Não existe camada de dados isolada nem configuração: SQL cru
concatenado sobre uma conexão global impede parametrização centralizada, transação e
teste.

================================
Total: 16 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
