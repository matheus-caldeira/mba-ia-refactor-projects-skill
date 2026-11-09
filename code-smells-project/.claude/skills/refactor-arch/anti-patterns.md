# Catálogo de Anti-Patterns

Referência da **Fase 2**. São 14 anti-patterns, cada um com sinais de detecção
acionáveis, severidade e o critério que separa achado real de falso positivo.

## Escala de severidade

| Nível | Critério |
|---|---|
| **CRITICAL** | Falha grave de arquitetura ou segurança: expõe dados sensíveis, permite comprometimento do sistema, ou viola completamente a separação de responsabilidades (God Class com banco + roteamento + regra no mesmo lugar). |
| **HIGH** | Forte violação de MVC/SOLID que dificulta muito manutenção e teste: regra de negócio pesada no controller, acoplamento sem injeção de dependência, estado global mutável. |
| **MEDIUM** | Padronização, duplicação ou performance moderada: N+1, validação ausente, middleware mal usado, tratamento de erro inadequado. |
| **LOW** | Legibilidade: nomenclatura ruim, magic numbers, imports mortos, código comentado. |

**Escopo dos comandos:** todos os `grep -r` abaixo excluem `venv/`, `node_modules/`,
`.git/`, `dist/`, `__pycache__/` e `.claude/` (a própria skill contém exemplos de
código ruim e geraria falso positivo). Ao adaptar um comando, mantenha o
`--exclude-dir`.

**Regra antes de registrar qualquer achado:** abra o arquivo na linha e leia o
trecho. Grep aponta candidatos; a leitura confirma. Todo achado carrega
`arquivo:linha` verificado.

---

## AP-01 · SQL Injection por concatenação — CRITICAL

**O que é:** entrada do usuário interpolada direto na string SQL, sem parametrização.

**Sinais de detecção:**

```bash
# Python — concatenação e f-string em SQL
grep -rnE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "(execute|executemany)\(.*(\+|%|\.format\(|f\")" --include='*.py' .
grep -rnE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "(SELECT|INSERT|UPDATE|DELETE).*(\"[[:space:]]*\+|\+[[:space:]]*str\()" --include='*.py' .

# JS/TS — template literal com interpolação em SQL
grep -rnE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "(query|execute|run|all|get)\(\s*\`.*\\\$\{" --include='*.js' --include='*.ts' .
grep -rnE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "(SELECT|INSERT|UPDATE|DELETE).*['\"]\s*\+" --include='*.js' --include='*.ts' .
```

**Confirmação:** o valor concatenado precisa vir de entrada externa (`request.`,
`req.body`, `req.params`, `req.query`, argumento de função pública). SQL montado só
com constantes internas é feio, não é injeção — classifique como LOW/MEDIUM.

**Agravantes que elevam o impacto no relatório:** concatenação em query de login
(permite bypass de autenticação com `' --`), em `LIKE` de busca (permite `UNION
SELECT` para exfiltrar tabelas), ou em endpoint sem autenticação.

**Dica de contraste:** se em algum ponto o projeto usa placeholders corretamente
(`?`, `$1`, `:nome`) e em outro concatena, cite os dois — prova que a forma segura
era conhecida e o problema é inconsistência, não desconhecimento.

**Correção:** playbook P-01.

---

## AP-02 · Credenciais e segredos hardcoded — CRITICAL

**O que é:** senha, API key, token ou `SECRET_KEY` como literal no código-fonte.

**Sinais de detecção:**

```bash
# Atribuição direta: SECRET = "...", apiKey: "...", self.email_password = "..."
grep -rniE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "(secret|password|passwd|pwd|api[_-]?key|token|private[_-]?key|gateway[_-]?key)[[:space:]]*[:=][[:space:]]*['\"][^'\"]{6,}" \
  --include='*.py' --include='*.js' --include='*.ts' --include='*.json' . | grep -v node_modules

# Forma indexada: app.config["SECRET_KEY"] = "...", settings['DB_PASS'] = "..."
# Sem esta linha o idioma mais comum de Flask passa despercebido.
grep -rniE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "\[['\"][A-Z_]*(SECRET|PASSWORD|KEY|TOKEN)[A-Z_]*['\"]\][[:space:]]*=[[:space:]]*['\"][^'\"]{6,}" \
  --include='*.py' --include='*.js' . | grep -v node_modules

# Chaves de provedores conhecidos
grep -rnE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "(sk_live|pk_live|AKIA[0-9A-Z]{16}|ghp_|xox[baprs]-)" . | grep -v node_modules
```

**Aspas nas flags `--include`:** mantenha `--include='*.py'` entre aspas. Sem elas, o
shell (zsh) expande o glob antes do grep e o comando aborta com `no matches found` —
retornando zero achados e dando a falsa impressão de que o projeto está limpo. Vale
para todos os greps deste catálogo.

**Confirmação:** descarte placeholders óbvios (`"your-api-key-here"`, `"changeme"`,
`os.environ.get(...)` com default vazio) e valores em `.env.example`. Um segredo em
arquivo versionado deve ser tratado como **permanentemente comprometido** — a
recomendação inclui rotacionar, não só mover para env var.

**Agravante:** segredo devolvido por endpoint HTTP (ex.: `/health` retornando
`secret_key`) é vazamento ativo, não apenas exposição no repositório.

**Correção:** playbook P-02.

---

## AP-03 · Senha em texto puro ou hash fraco — CRITICAL

**O que é:** senha armazenada sem hash, comparada literalmente, ou protegida por
algoritmo inadequado (MD5, SHA1, ou "criptografia" caseira).

**Sinais de detecção:**

```bash
# Ausência de hashing forte — zero resultados aqui é o próprio achado
grep -rniE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "bcrypt|argon2|scrypt|pbkdf2|generate_password_hash|werkzeug.security" --include='*.py' --include='*.js' . | grep -v node_modules

# Hash fraco presente
grep -rniE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "(md5|sha1)\(" --include='*.py' --include='*.js' .

# Senha vazando na serialização
grep -rniE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "['\"](password|senha|pass|pwd)['\"][[:space:]]*:" --include='*.py' --include='*.js' . | grep -v node_modules
```

**Confirmação:** verifique três lugares distintos — onde a senha é **gravada**, onde
é **comparada** no login, e se aparece na **resposta** da API (`to_dict`,
serializers, `SELECT *` devolvido cru).

**Por que MD5/SHA1 contam:** são hashes rápidos e sem salt, projetados para
velocidade. Uma GPU testa bilhões por segundo; para senha, isso é equivalente a
texto puro com passo extra.

**Agravante máximo:** campo de senha incluído na serialização de um endpoint
público — qualquer um que chame `GET /users` recebe as credenciais.

**Correção:** playbook P-03.

---

## AP-04 · God Class / God Method — CRITICAL

**O que é:** um arquivo ou função concentrando responsabilidades de várias camadas —
roteamento, SQL, regra de negócio, formatação — para múltiplos domínios.

**Sinais de detecção:**

```bash
# Arquivos grandes
find . -name "*.py" -o -name "*.js" | grep -vE "node_modules|venv" | xargs wc -l | sort -rn | head -10

# Um arquivo que importa banco E rotas E regra
grep -ln "sqlite3\|psycopg2\|mysql" *.py *.js 2>/dev/null | xargs grep -l "route\|app\.\(get\|post\)" 2>/dev/null
```

**Critérios objetivos:**

- Arquivo com mais de ~300 linhas concentrando mais de uma camada;
- Classe/arquivo cujo nome é genérico (`AppManager`, `Helper`, `Utils`, `Manager`,
  `Handler`) — nome genérico denuncia responsabilidade indefinida;
- Função com mais de ~50 linhas ou aninhamento acima de 4 níveis;
- Um arquivo tocando 3+ entidades de domínio diferentes.

**Confirmação:** tamanho sozinho não basta. O achado é a **mistura de camadas**: uma
classe de 400 linhas que só faz acesso a dados é um repositório grande, não uma God
Class. Cite quais responsabilidades coexistem e em quais linhas.

**Correção:** playbook P-04.

---

## AP-05 · Endpoint administrativo sem autenticação — CRITICAL

**O que é:** rota que executa operação destrutiva ou privilegiada (SQL arbitrário,
reset de banco, alteração de papel) sem exigir identidade.

**Sinais de detecção:**

```bash
# Rotas sensíveis
grep -rnE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "route\(['\"].*(admin|debug|internal|reset|query|exec|eval)" --include='*.py' --include='*.js' .
grep -rnE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "app\.(get|post|put|delete)\(['\"].*(admin|debug|reset|query)" --include='*.js' .

# Existe alguma camada de auth? Zero resultados = achado
grep -rniE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "before_request|@login_required|authenticate|authorization|jwt|passport|session\[" --include='*.py' --include='*.js' . | grep -v node_modules
```

**Confirmação:** rastreie se há middleware/decorator protegendo a rota. Uma
verificação superficial não conta como proteção — por exemplo, checar apenas se a
query "começa com SELECT" para decidir entre `fetch` e `commit` **não restringe
nada**: o ramo alternativo persiste qualquer DDL/DML.

**Agravante:** combinado com bind em `0.0.0.0`, a superfície passa de local para
toda a rede.

**Autorização por objeto (IDOR) e mass assignment — mesma família, mesma severidade:**
existir autenticação não basta. Verifique, rota a rota, *quem* pode agir sobre *qual*
recurso:

- rota que recebe id de usuário (path `/<id>`, `usuario_id`/`user_id` no corpo ou na
  query) e lê ou altera dados dele **sem comparar com o usuário autenticado**
  (próprio usuário ou papel privilegiado);
- update que aceita do payload campos privilegiados (`role`, `tipo`, `is_admin`,
  `active`) sem exigir papel de admin;
- troca de senha pelo próprio usuário sem exigir a senha atual;
- decorator de auth implementado mas **não aplicado** a todas as rotas de escrita.

```bash
# Rotas de escrita/leitura por id — liste e confira, uma a uma, o guard aplicado
grep -rnE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "(route|add_url_rule)\(.*<int:|\.(get|put|patch|delete)\(['\"][^'\"]*:id" --include='*.py' --include='*.js' .

# Campos privilegiados vindos do payload
grep -rnE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "(data|dados|req\.body)(\[|\.get\(|\.)['\"]?(role|tipo|is_admin|active)" --include='*.py' --include='*.js' .
```

Monte no relatório (ou no plano da Fase 3) uma **matriz rota × quem pode** — público,
autenticado, próprio usuário, admin — e trate cada linha sem guard como achado.

**Correção:** playbook P-05.

---

## AP-06 · Debug ativo e exposição de configuração — CRITICAL

**O que é:** modo debug ligado em produção, e/ou endpoint devolvendo configuração
interna (caminhos, flags, segredos, versões).

**Sinais de detecção:**

```bash
grep -rnE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "debug[[:space:]]*=[[:space:]]*True|DEBUG['\"]?\][[:space:]]*=[[:space:]]*True|NODE_ENV.*development" --include='*.py' --include='*.js' .
grep -rnE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "app\.run\(|listen\(" --include='*.py' --include='*.js' . | grep -iE "0\.0\.0\.0|debug"
```

**Por que é CRITICAL em Flask:** com `debug=True`, o Werkzeug serve um console
interativo na página de exceção. Exposto em `0.0.0.0`, isso é execução remota de
código Python no servidor — não é apenas "log verboso".

**Confirmação:** verifique se o valor é fixo no código ou vem de env var. `debug=os.
getenv("FLASK_DEBUG") == "1"` é aceitável; `debug=True` literal não é.

**Correção:** playbook P-02 e P-06.

---

## AP-07 · Estado global mutável compartilhado — HIGH

**O que é:** conexão, cache ou contador em variável de módulo, compartilhado por
todas as requisições sem sincronização nem escopo.

**Sinais de detecção:**

```bash
# Python — singleton de conexão
grep -rn --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "^[a-z_]* *= *None\|global " --include='*.py' .
grep -rn --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "check_same_thread=False" --include='*.py' .

# JS — objeto de módulo mutável exportado
grep -rnE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "^(let|var) [a-zA-Z_]+ *= *(\{\}|\[\]|0)" --include='*.js' . | grep -v node_modules
```

**Confirmação:** o estado precisa ser (a) mutável, (b) de escopo de módulo e (c)
alcançado por mais de uma requisição. Constante de configuração congelada não conta.

**Agravantes específicos:**

- `check_same_thread=False` no SQLite desativa justamente a proteção contra uso
  concorrente entre threads — com servidor multi-thread, transações de requisições
  distintas se misturam e um `commit` confirma escrita parcial de outra.
- Cache global sem limite de tamanho ou TTL é vazamento de memória.
- Estado global impede teste isolado: não há como injetar um duplo.

**Correção:** playbook P-07.

---

## AP-08 · Regra de negócio dentro do controller/rota — HIGH

**O que é:** o handler HTTP decide regra de domínio, dispara efeitos colaterais e
monta queries, em vez de apenas traduzir HTTP.

**Sinais de detecção:**

```bash
# Handlers longos
grep -rn --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} -A40 "@app.route\|@.*_bp.route\|app\.\(get\|post\|put\|delete\)(" --include='*.py' --include='*.js' . | grep -c ""

# Efeito colateral direto no handler
grep -rnE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "(smtplib|sendmail|send_email|requests\.(post|get)|fetch\(|print\(.*EMAIL|console\.log.*ENVIANDO)" --include='*.py' --include='*.js' .

# Acesso a dados dentro da rota
grep -rnE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "(cursor\.execute|\.query\.(all|get|filter)|db\.(run|get|all))" --include='*.py' --include='*.js' .
```

**Confirmação:** abra o handler e classifique cada bloco: validação de contrato HTTP
(ok), chamada a serviço (ok), decisão de domínio (achado), SQL (achado), envio de
e-mail/SMS/push (achado).

**Sinal revelador:** lista de status/estados válidos hardcoded dentro do handler, ou
regra anunciada mas não implementada (ex.: "cancelar devolve estoque" que é apenas
um `print`) — o segundo caso é bug real de negócio, não só arquitetura.

**Correção:** playbook P-08.

---

## AP-09 · APIs deprecated / obsoletas — HIGH ou MEDIUM

**O que é:** uso de API marcada como obsoleta pelo mantenedor, que já tem
equivalente moderno e tende a quebrar em versão futura.

Severidade: **HIGH** quando a API deprecated tem impacto de segurança ou correção
(hash fraco, verificação de TLS desligada); **MEDIUM** quando é só dívida técnica
com data de validade.

### Python

| Deprecated | Desde | Substituir por |
|---|---|---|
| `datetime.utcnow()` | Python 3.12 | `datetime.now(timezone.utc)` — retorna datetime *aware* |
| `datetime.utcfromtimestamp()` | Python 3.12 | `datetime.fromtimestamp(ts, timezone.utc)` |
| `Model.query.get(id)` (SQLAlchemy) | SQLAlchemy 2.0 | `db.session.get(Model, id)` |
| `Query.get()` / estilo `Model.query` | SQLAlchemy 2.0 | `db.session.execute(select(Model))` |
| `hashlib.md5` / `sha1` para senha | — | `bcrypt` / `argon2` |
| `imp` | 3.4 | `importlib` |
| `collections.Mapping` etc. | 3.3 | `collections.abc.Mapping` |
| `distutils` | 3.10 (removido em 3.12) | `setuptools` / `packaging` |
| `@app.before_first_request` (Flask) | Flask 2.2 (removido em 2.3) | inicialização no factory / `with app.app_context()` |
| `assertEquals`, `failUnless` | — | `assertEqual`, `assertTrue` |
| `os.popen`, `commands` | — | `subprocess` |
| `verify=False` em `requests` | — | verificação de certificado habilitada |

### Node.js / JavaScript

| Deprecated | Substituir por |
|---|---|
| `new Buffer(...)` | `Buffer.from()` / `Buffer.alloc()` |
| `url.parse()` | `new URL()` |
| `fs.exists()` | `fs.existsSync()` / `fs.promises.access()` |
| `require('crypto').createCipher` | `createCipheriv` |
| `body-parser` avulso | `express.json()` / `express.urlencoded()` (nativos desde Express 4.16) |
| `util.isArray` | `Array.isArray` |
| `domain` | `async_hooks` / `AsyncLocalStorage` |
| Callbacks aninhados para I/O | `async/await` com `util.promisify` |
| `process.on('SIGTERM')` sem cleanup | shutdown gracioso explícito |
| `var` | `const` / `let` |

**Sinais de detecção:**

```bash
grep -rnE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "datetime\.utcnow\(\)|utcfromtimestamp|\.query\.get\(|hashlib\.(md5|sha1)|before_first_request|assertEquals|distutils|verify=False" --include='*.py' .
grep -rnE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "new Buffer\(|url\.parse\(|fs\.exists\(|createCipher\(|util\.isArray|require\(['\"]body-parser" --include='*.js' . | grep -v node_modules
```

Confirme a versão declarada no manifesto antes de classificar: `Model.query.get()`
só é deprecated a partir do SQLAlchemy 2.0 — em projeto preso na 1.4 é aviso, não
erro. Sempre cite **o substituto exato**, não apenas "está obsoleto".

**Correção:** playbook P-09.

---

## AP-10 · Query N+1 — MEDIUM

**O que é:** uma consulta para obter a lista, e mais uma consulta por item dentro do
laço. Com 100 itens, 101 idas ao banco.

**Sinais de detecção:**

```bash
# Python — query dentro de laço
grep -rn --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} -B3 -A3 "for .* in .*:" --include='*.py' . | grep -E "\.query\.(get|filter|all)|cursor\.execute"

# JS — query dentro de forEach/map
grep -rn --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} -A6 "\.forEach(\|\.map(" --include='*.js' . | grep -E "db\.(get|all|run)|\.query\("
```

**Confirmação:** a consulta interna precisa estar no corpo do laço e depender do
item iterado. Em ORM, atenção a acesso lazy a relacionamento (`user.tasks` dentro do
laço) — dispara query sem chamada explícita e é o caso mais fácil de passar batido.

**Correção:** playbook P-10.

---

## AP-11 · Validação de entrada ausente ou duplicada — MEDIUM

**O que é:** handler que confia no payload, ou a mesma regra de validação copiada em
vários lugares (e divergindo entre eles).

**Sinais de detecção:**

```bash
# Consumo de payload sem validação subsequente
grep -rn --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} -A6 "request.get_json()\|req\.body" --include='*.py' --include='*.js' . | grep -v "if not\|validate\|schema"

# Regex de validação repetido — duplicação
grep -rnE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "re\.match\(r?['\"]\^\[a-zA-Z0-9" --include='*.py' . | sort | uniq -c | sort -rn
```

**Confirmação:** identifique se existe biblioteca de schema no manifesto
(`marshmallow`, `pydantic`, `zod`, `joi`) e se está de fato em uso. Dependência
declarada e não usada é achado por si — alguém pretendeu validar e não terminou.

**Sinal de duplicação:** o mesmo regex de e-mail em `utils/helpers.py` e copiado
inline nas rotas significa duas fontes de verdade que vão divergir.

**Correção:** playbook P-11.

---

## AP-12 · Tratamento de erro engolido ou inconsistente — MEDIUM

**O que é:** `except`/`catch` genérico que descarta a exceção, erro ignorado em
callback, ou cada rota devolvendo formato e status diferentes para a mesma falha.

**Sinais de detecção:**

```bash
# Python — except nu / silencioso
grep -rnE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "except[[:space:]]*:|except Exception[[:space:]]*:|except.*:[[:space:]]*(pass|return None)" --include='*.py' .

# JS — erro recebido e não tratado
grep -rnE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "\(err[a-zA-Z]*,|catch[[:space:]]*\(" --include='*.js' . | grep -v node_modules

# Inconsistência de formato de resposta de erro
grep -rnE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "(jsonify|res\.(json|send|status))\(.*(error|erro|msg)" --include='*.py' --include='*.js' .
```

**Confirmação:** um `except: return 500` genérico esconde a causa real e transforma
bug de programação em erro de servidor silencioso — o usuário vê "Erro interno" e o
log não registra nada. Em Node, o padrão `(err, result) => { /* err ignorado */ }` é
o mesmo problema: a operação falha e o fluxo segue como se tivesse dado certo.

**Sinal de inconsistência:** misturar `res.send("string")` com `res.json({erro:...})`
e status ora 400 ora 500 para a mesma classe de falha — o cliente não tem contrato.

**Correção:** playbook P-12.

---

## AP-13 · Integridade referencial não mantida — MEDIUM

**O que é:** exclusão ou atualização que deixa registros filhos órfãos; ausência de
FK, cascade ou transação envolvendo múltiplas escritas.

**Sinais de detecção:**

```bash
# DELETE sem tratar dependentes
grep -rnE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "DELETE FROM" --include='*.py' --include='*.js' .

# Ausência de FK no DDL
grep -rn --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "CREATE TABLE" --include='*.py' --include='*.js' --include='*.sql' . | grep -v "FOREIGN KEY\|REFERENCES"

# Escritas múltiplas sem transação
grep -rniE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "begin|commit|rollback|transaction" --include='*.py' --include='*.js' . | grep -v node_modules
```

**Confirmação:** rastreie o que aponta para a tabela afetada. Se `users` é deletado e
`enrollments.user_id` continua apontando para o id removido, há órfão. Sequência de
`INSERT` encadeados sem transação envolvente é o mesmo problema no tempo: falha no
terceiro insert deixa os dois primeiros persistidos.

**Condição de corrida check-then-act:** ler um saldo/estoque, validar em código e
só depois gravar (`if estoque < qtd: erro` … `UPDATE ... SET estoque = estoque - ?`) permite
que duas requisições simultâneas passem pela checagem e deixem o valor negativo.
Atenção também a itens repetidos do mesmo produto no mesmo pedido, que escapam de uma
checagem feita item a item.

**Correção:** playbook P-13.

---

## AP-14 · Legibilidade: nomes ruins, magic numbers, imports mortos — LOW

**O que é:** o conjunto de problemas que não quebram nada, mas custam atenção em
toda leitura futura.

**Sinais de detecção:**

```bash
# Nomes de uma letra / abreviações opacas em atribuição
grep -rnE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "\b(let|var|const)?[[:space:]]*\b[a-z]{1,2}[[:space:]]*=[[:space:]]*req(\.|uest)" --include='*.py' --include='*.js' .

# Magic numbers em comparação
grep -rnE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "[<>=!]=?[[:space:]]*[0-9]{2,}" --include='*.py' --include='*.js' . | grep -v node_modules

# Imports agregados — candidatos a morto
grep -rnE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "^import [a-z]+, ?[a-z]+|^from .* import .*,.*,.*" --include='*.py' .

# Código comentado
grep -rnE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "^[[:space:]]*(#|//)[[:space:]]*(def |class |function |if |return |app\.)" --include='*.py' --include='*.js' .
```

**Confirmação:** para import morto, confirme que o símbolo não aparece no resto do
arquivo (`grep -c`). Uma linha como `import json, os, sys, time` no topo de um
arquivo de rotas quase sempre tem 3 dos 4 sem uso.

**Exemplos do que registrar:** `u`, `e`, `p`, `cid`, `cc` para dados de checkout;
prioridade comparada contra `1..5` sem enum; `if len(password) < 4` com o limite
solto; `to_dict()` com campo sensível junto dos públicos.

**Agrupamento:** vários itens LOW do mesmo tipo podem virar **um** achado com lista
de ocorrências, para o relatório não virar ruído.

**Correção:** playbook P-14.

---

## Checklist de cobertura da Fase 2

Antes de fechar o relatório, confirme que investigou **todas** as 14 categorias e
registre as que não se aplicam:

- [ ] AP-01 SQL Injection
- [ ] AP-02 Segredos hardcoded
- [ ] AP-03 Senha em texto puro / hash fraco
- [ ] AP-04 God Class / God Method
- [ ] AP-05 Endpoint sem auth, IDOR, campos privilegiados no payload
- [ ] AP-06 Debug ativo / config exposta
- [ ] AP-07 Estado global mutável
- [ ] AP-08 Regra de negócio no controller
- [ ] AP-09 APIs deprecated
- [ ] AP-10 Query N+1
- [ ] AP-11 Validação ausente/duplicada
- [ ] AP-12 Erro engolido/inconsistente
- [ ] AP-13 Integridade referencial
- [ ] AP-14 Legibilidade
