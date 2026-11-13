================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python 3.12 + Flask 3.1.1 (flask-cors 5.0.1, sqlite3 cru)
Files:   4 analyzed | ~780 lines of code
Date:    2026-11-12

## Summary
CRITICAL: 5 | HIGH: 3 | MEDIUM: 4 | LOW: 1

## Findings

### #1 [CRITICAL] SQL Injection sistêmico por concatenação de strings
- **Anti-pattern:** AP-01 — SQL Injection por concatenação
- **File:** `models.py:109-111, 289-299, 47-50, 57-61, 126-129, 279-281, 28, 68, 92, 140, 149-151, 155, 157-166, 174, 188, 192, 220, 224` (todas as queries com parâmetro do arquivo)
- **Description:** Toda query que recebe parâmetro monta o SQL concatenando o valor na string. `login_usuario` interpola `email` e `senha` vindos do corpo de `POST /login`; `buscar_produtos` concatena `q` e `categoria` da query string dentro de `LIKE`/`=`; `criar_produto`, `atualizar_produto`, `criar_usuario` e `atualizar_status_pedido` concatenam texto do payload. O seed em `database.py:70-83` usa placeholders `?` corretamente — a forma segura era conhecida e não foi aplicada.
- **Impact:** `POST /login` com `{"email": "admin@loja.com' --", "senha": "x"}` autentica como admin sem senha. `GET /produtos/busca?q=' UNION SELECT id,nome,email,senha,tipo,0,0,criado_em FROM usuarios --` devolve e-mails e senhas de todos os usuários. Um nome de produto com apóstrofo (`Monitor 27''` do próprio seed) quebra o `INSERT`/`UPDATE` com erro 500.
- **Recommendation:** Parametrizar todas as queries (`cursor.execute("... WHERE email = ?", (email,))`). Na busca dinâmica, acumular cláusulas com `?` e os valores numa lista de params; o `%` do `LIKE` vai no valor, não no SQL.

```python
cursor.execute(
    "SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"
)
```

### #2 [CRITICAL] Endpoints administrativos destrutivos sem autenticação (SQL arbitrário e reset do banco)
- **Anti-pattern:** AP-05 — Endpoint administrativo sem autenticação
- **File:** `app.py:47-57, 59-78`
- **Description:** `POST /admin/query` executa qualquer SQL recebido em `{"sql": ...}`; a checagem `startswith("SELECT")` só decide entre `fetchall` e `commit`, o ramo `else` persiste qualquer DDL/DML. `POST /admin/reset-db` apaga as quatro tabelas. Nenhuma das duas rotas exige identidade — o grep por `before_request|login_required|authorization|jwt|session[|token` retornou zero no projeto.
- **Impact:** Qualquer cliente que alcance a porta 5000 (bind em `0.0.0.0`, ver #5) lê a tabela `usuarios` inteira, executa `DROP TABLE` ou zera a loja com uma única requisição.
- **Recommendation:** Remover `/admin/query` (não existe forma segura de expor SQL arbitrário). Manter `/admin/reset-db` apenas atrás de autenticação + papel `admin` **e** de um flag de ambiente desligado por padrão (`ALLOW_DB_RESET`).

```python
cursor.execute(query)
if query.strip().upper().startswith("SELECT"):
    ...
else:
    db.commit()
```

### #3 [CRITICAL] Ausência total de autenticação/autorização (IDOR, escrita sem dono, login sem sessão)
- **Anti-pattern:** AP-05 — Endpoint sem auth / IDOR / campos privilegiados
- **File:** `app.py:11-28`, `controllers.py:167-183, 188-203, 222-227, 229-235, 237-245, 128-134, 136-144`
- **Description:** Nenhuma rota tem guard. `POST /login` devolve os dados do usuário mas não emite token/sessão — não há como provar identidade depois dele. `POST /pedidos` aceita `usuario_id` do corpo (qualquer um compra em nome de outro); `GET /pedidos/usuario/<id>` e `GET /pedidos` expõem pedidos de todos; `PUT /pedidos/<id>/status` deixa qualquer cliente aprovar/cancelar pedidos; `POST/PUT/DELETE /produtos` alteram o catálogo e preços sem papel de admin; `GET /usuarios`, `GET /usuarios/<id>` e `GET /relatorios/vendas` são públicos.

  | Rota | Hoje | Deveria |
  |---|---|---|
  | `GET /produtos*`, `GET /`, `GET /health` | público | público |
  | `POST /usuarios`, `POST /login` | público | público |
  | `POST/PUT/DELETE /produtos` | público | admin |
  | `GET /usuarios`, `GET /pedidos`, `GET /relatorios/vendas` | público | admin |
  | `GET /usuarios/<id>`, `GET /pedidos/usuario/<id>` | público | próprio usuário ou admin |
  | `POST /pedidos` | público, `usuario_id` do corpo | autenticado, dono = ator (admin pode informar outro) |
  | `PUT /pedidos/<id>/status` | público | admin |
  | `POST /admin/*` | público | admin (ver #2) |
- **Impact:** Um visitante anônimo enumera `GET /usuarios/1..N`, cancela pedidos alheios, zera o preço de um produto via `PUT /produtos/<id>` e depois compra em nome de outro usuário.
- **Recommendation:** Emitir token assinado no login (`itsdangerous`, já dependência transitiva do Flask, com `SECRET_KEY` do ambiente), criar decorators `require_auth`/`require_admin` e aplicar a matriz acima; o dono do pedido passa a ser o usuário autenticado.

### #4 [CRITICAL] Senhas em texto puro, devolvidas pela API, e seed admin com senha conhecida
- **Anti-pattern:** AP-03 — Senha em texto puro / AP-02 — Credencial hardcoded (seed)
- **File:** `models.py:126-129, 109-111, 83, 99`, `database.py:75-83`
- **Description:** `criar_usuario` grava a senha literal; `login_usuario` compara a senha em texto puro dentro do SQL; `get_todos_usuarios` e `get_usuario_por_id` incluem o campo `"senha"` na resposta. O seed cria `admin@loja.com` / `admin123` (tipo `admin`) e dois clientes com senhas literais em todo boot com banco vazio. Grep por `bcrypt|argon2|scrypt|pbkdf2|generate_password_hash|hashlib` retornou zero.
- **Impact:** `GET /usuarios` entrega, sem autenticação, o e-mail e a senha de todos os clientes (que tendem a reutilizá-la em outros serviços). Qualquer leitor do repositório entra como admin com `admin123`.
- **Recommendation:** Hash com `werkzeug.security.generate_password_hash` (scrypt/pbkdf2, já instalado com o Flask) e `check_password_hash` no login; remover `senha` de toda serialização; criar o admin só a partir de `ADMIN_EMAIL`/`ADMIN_PASSWORD` do ambiente (obrigatórios em produção) e contas de exemplo só fora de produção.

```python
usuarios = [
    ("Admin", "admin@loja.com", "admin123", "admin"),
```

### #5 [CRITICAL] SECRET_KEY hardcoded vazada em `/health`, debug ligado e bind em 0.0.0.0
- **Anti-pattern:** AP-02 — Segredos hardcoded / AP-06 — Debug ativo e exposição de configuração
- **File:** `app.py:7-9, 88`, `controllers.py:284-289`
- **Description:** `SECRET_KEY` é literal no código e é **devolvida** por `GET /health` junto com `db_path`, `debug` e `ambiente`. `DEBUG = True` e `app.run(host="0.0.0.0", ..., debug=True)` são fixos, sem env var. `CORS(app)` libera todas as origens.
- **Impact:** Com o Werkzeug em debug escutando em todas as interfaces, qualquer exceção (fácil de provocar — ver #1 e #11) abre o console interativo: execução remota de Python no servidor. A chave vazada permite forjar qualquer token/cookie que venha a ser assinado com ela; por estar no histórico do git, deve ser considerada comprometida.
- **Recommendation:** Módulo de config lendo `SECRET_KEY`, `FLASK_DEBUG`, `HOST`, `PORT`, `DB_PATH` do ambiente (boot falha sem `SECRET_KEY` em produção), `.env.example` sem valores reais, bind padrão `127.0.0.1`, `/health` devolvendo só status e contagens. Rotacionar a chave.

```python
"db_path": "loja.db",
"debug": True,
"secret_key": "minha-chave-super-secreta-123"
```

### #6 [HIGH] Conexão SQLite global compartilhada entre threads
- **Anti-pattern:** AP-07 — Estado global mutável
- **File:** `database.py:4-11`
- **Description:** Uma única conexão em variável de módulo (`global db_connection`), aberta com `check_same_thread=False`, servida a todas as requisições do servidor multi-thread do Werkzeug. Não há `rollback` nem bloco transacional em nenhum arquivo (grep retornou zero).
- **Impact:** Duas requisições simultâneas compartilham o mesmo espaço de transação: o `commit` de `POST /produtos` confirma no meio do caminho os `INSERT`s de um `POST /pedidos` concorrente; uma exceção em `criar_pedido` deixa escritas pendentes que o próximo `commit` de outra rota persiste. Também impede teste isolado.
- **Recommendation:** Conexão por requisição em `flask.g` fechada em `teardown_appcontext`, com transação explícita (`with conn:`) nas operações de múltiplas escritas; caminho do banco vindo da config.

### #7 [HIGH] Regra de negócio e efeitos colaterais nos controllers; regra anunciada e não implementada
- **Anti-pattern:** AP-08 — Regra de negócio dentro do controller/rota
- **File:** `controllers.py:43-54, 208-210, 242-250, 264-274`, `app.py:47-57`, `models.py:256-262`
- **Description:** Validações de domínio (categorias válidas, limites de nome/preço) e a lista de status válidos estão hardcoded dentro dos handlers; notificações de e-mail/SMS/push são `print` no handler; `health_check` e `reset_database` executam SQL direto na camada HTTP; a política de desconto do relatório mora na função de dados. Ao cancelar um pedido, o handler imprime "Devolver estoque." mas **nada devolve o estoque**.
- **Impact:** Bug real de negócio: cada pedido cancelado retira o estoque permanentemente. As regras não podem ser testadas sem subir HTTP, e mudar a lista de status exige editar o handler.
- **Recommendation:** Extrair um service por domínio (`produto`, `usuario`, `pedido`, `relatorio`) com as regras, constantes de domínio (categorias, status, faixas de desconto) e a devolução de estoque no cancelamento dentro de transação; notificações num serviço próprio chamado pelo service; controllers só traduzem HTTP.

```python
if novo_status == "cancelado":
    print("NOTIFICAÇÃO: Pedido " + str(pedido_id) + " cancelado. Devolver estoque.")
```

### #8 [HIGH] Camadas por papel técnico sem fronteira: `models.py` e `database.py` misturam responsabilidades de 4 entidades
- **Anti-pattern:** AP-04 — God Class / God Method (rebaixado a HIGH: há separação de arquivos, mas não de responsabilidades)
- **File:** `models.py:1-314`, `database.py:7-86`, `app.py:1-88`
- **Description:** `models.py` (314 linhas) concentra acesso a dados, serialização manual de linha e regra de negócio (desconto, cálculo de total, baixa de estoque) para produtos, usuários, pedidos e relatórios. `database.py` mistura conexão, DDL e seed num único `get_db()` executado a cada processo. `app.py` mistura config, roteamento e SQL. O mapeamento linha→dict de produto está copiado três vezes (`models.py:12-21, 31-40, 304-313`).
- **Impact:** Qualquer mudança em uma entidade toca o arquivo de todas; a duplicação da serialização já diverge (o login omite `criado_em`, as listagens incluem `senha`).
- **Recommendation:** Pacote `models/` com um módulo por entidade e uma função `_row_to_dict` por entidade; `database.py` reduzido a conexão + `init_db()` separado do seed; `app.py` como composition root.

### #9 [MEDIUM] Query N+1 nas listagens de pedidos e no checkout
- **Anti-pattern:** AP-10 — Query N+1
- **File:** `models.py:187-199, 219-231, 139-141, 154-156`
- **Description:** Para cada pedido, uma query de itens; para cada item, uma query do nome do produto. Em `criar_pedido`, cada produto é lido duas vezes (validação e inserção).
- **Impact:** `GET /pedidos` com 100 pedidos de 3 itens faz 401 consultas na conexão global compartilhada (#6), segurando-a durante toda a listagem.
- **Recommendation:** Uma query de pedidos + uma query de itens com `JOIN produtos` filtrada por `pedido_id IN (...)`, agrupando em dicionário; no checkout, ler os produtos uma vez e reutilizar.

### #10 [MEDIUM] Checkout sem transação, com corrida no estoque e sem integridade referencial
- **Anti-pattern:** AP-13 — Integridade referencial não mantida
- **File:** `models.py:139-168, 68, 164-166`, `database.py:36-53`
- **Description:** `criar_pedido` checa estoque (`produto["estoque"] < item["quantidade"]`) e só depois desconta, sem transação nem `rollback`. Itens repetidos do mesmo produto passam cada um na checagem individual. `quantidade` negativa ou zero não é rejeitada. O DDL não declara `FOREIGN KEY`; `DELETE /produtos/<id>` deixa `itens_pedido` órfãos; `usuario_id` inexistente é aceito.
- **Impact:** Duas compras simultâneas do último Notebook deixam o estoque em -1; `[{produto_id:1,quantidade:10},{produto_id:1,quantidade:10}]` com estoque 10 passa; `quantidade: -5` **aumenta** o estoque e gera pedido com total negativo. Falha no meio do loop deixa pedido sem itens.
- **Recommendation:** Agregar quantidades por produto, validar `quantidade` inteira > 0, executar tudo numa transação com baixa atômica condicional (`UPDATE ... SET estoque = estoque - ? WHERE id = ? AND estoque >= ?`, checando `rowcount`), declarar FKs com `PRAGMA foreign_keys=ON` e impedir exclusão de produto com pedidos.

### #11 [MEDIUM] Validação de entrada ausente, duplicada e divergente
- **Anti-pattern:** AP-11 — Validação ausente/duplicada
- **File:** `controllers.py:28-54, 72-90, 150-158, 169-174, 195-201, 239-243, 118-121`
- **Description:** A validação de produto está copiada entre `criar_produto` e `atualizar_produto`, e a cópia diverge: o update não valida tamanho do nome nem categoria. Não há checagem de tipo (`"preco": "abc"` causa `TypeError` → 500). `login` e `atualizar_status_pedido` chamam `dados.get` sem checar `None` (corpo vazio → 500). `criar_usuario` não valida formato de e-mail, tamanho de senha nem unicidade (a coluna não é `UNIQUE`). `preco_min=abc` na busca → 500.
- **Impact:** Entradas malformadas viram erro 500 (com stack trace interativo, dado o debug de #5) em vez de 400; e-mails duplicados tornam o login ambíguo; um produto pode ser atualizado para categoria inexistente.
- **Recommendation:** Um módulo de validação por entidade, usado por criação e atualização, verificando presença, tipo e faixa; `UNIQUE` em `usuarios.email` com resposta 409.

### #12 [MEDIUM] Tratamento de erro genérico que vaza detalhes e respostas inconsistentes
- **Anti-pattern:** AP-12 — Tratamento de erro engolido/inconsistente
- **File:** `controllers.py:10-12, 21-22, 60-62, 95-96, 108-109, 125-126, 133-134, 143-144, 164-165, 185-186, 218-220, 226-227, 234-235, 254-255, 261-262, 291-292`, `app.py:77-78`
- **Description:** 17 blocos `except Exception as e: return jsonify({"erro": str(e)}), 500` idênticos, sem log estruturado. O formato varia (`sucesso` às vezes presente, `/health` usa `{"status":"erro","detalhes":...}`). `PUT /pedidos/<id>/status` e `PUT /produtos` não distinguem recurso inexistente em todos os caminhos — o status de pedido inexistente responde 200 "Status atualizado".
- **Impact:** Mensagens internas do SQLite (nomes de tabela/coluna, trechos de SQL) chegam ao cliente e ajudam a explorar #1; cliente não tem contrato estável de erro.
- **Recommendation:** Exceções de domínio (`ValidationError`, `NotFoundError`, `ConflictError`, `AuthError`) e um `errorhandler` central que mapeia para `{"erro": ..., "sucesso": false}` + status; exceções inesperadas logadas com `logging` e respondidas com mensagem genérica.

### #13 [LOW] Imports mortos, magic numbers, `print` como log e nomes que sombreiam builtins
- **Anti-pattern:** AP-14 — Legibilidade
- **File:** `database.py:2`, `models.py:2`, `models.py:257-262`, `controllers.py:47-50, 8, 57, 106, 161, 179, 182`, `controllers.py:14, 56, 160`, `app.py:36`, `controllers.py:285`
- **Description:** `import os` (database.py) e `import sqlite3` (models.py) sem uso (`grep -c` = 0). Faixas de desconto `10000/5000/1000` e `0.1/0.05/0.02` e limites `2`/`200` do nome soltos no código. `print` no lugar de `logging`, inclusive registrando e-mails de usuários em cada login. Variável `id` sombreando o builtin. Versão `"1.0.0"` duplicada em dois arquivos.
- **Impact:** Custo de leitura; dados pessoais em stdout sem nível nem controle; mudar a política de desconto exige caçar literais.
- **Recommendation:** Remover imports mortos, nomear constantes de domínio, trocar `print` por `logging` sem PII, renomear `id` para `produto_id`/`usuario_id`, versão num único lugar da config.

## Deprecated APIs
Nenhuma API deprecated detectada (grep por `utcnow|utcfromtimestamp|query.get|hashlib.md5/sha1|before_first_request|distutils|verify=False` retornou zero; Flask 3.1.1 e flask-cors 5.0.1 usados com API atual).

## Categories Not Applicable
- AP-09 APIs deprecated — nenhuma ocorrência (ver acima).
- Todas as demais categorias (AP-01 a AP-08, AP-10 a AP-14) têm achado registrado.

## Architecture Assessment
**Current:** Monolítica — 4 arquivos divididos por papel técnico (`app`, `controllers`, `models`, `database`) sem fronteira real: SQL em `app.py` e nos controllers, regra de negócio nos controllers e nos models, config literal no código.
**Target:** MVC com `config.py`, `database.py` (conexão por requisição + schema), `models/` (um repositório parametrizado por entidade), `services/` (regras de domínio + notificações), `controllers/` (tradução HTTP), `routes/` (Blueprints = views), `middlewares/` (auth e error handler) e `app.py` como factory.
**Main structural gap:** Não há camada de serviço nem de autenticação: toda regra (e toda a segurança) depende de handlers públicos falando SQL concatenado numa conexão global.

================================
Total: 13 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
