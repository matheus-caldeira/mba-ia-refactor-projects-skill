# Playbook de Refatoração

Referência da **Fase 3**. Catorze padrões de transformação, um por família de
anti-pattern, com código antes/depois. Os exemplos alternam Python e JavaScript de
propósito: **o padrão é o mesmo, a sintaxe é detalhe**.

Ordem de aplicação recomendada: P-02 (config) → P-01/P-03 (segurança de dados) →
P-04/P-08 (estrutura) → demais.

---

## P-01 · Parametrizar queries

**Resolve:** AP-01 (SQL Injection). Corrija **todas** as ocorrências — uma sobrando
mantém a vulnerabilidade.

**Antes**
```python
cursor.execute(
    "SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"
)
```

**Depois**
```python
cursor.execute(
    "SELECT id, nome, email, tipo FROM usuarios WHERE email = ?", (email,)
)
```

Note que o depois muda duas coisas: parametriza **e** para de comparar senha no SQL
(a verificação do hash passa a ser feita em código — ver P-03).

### Filtro dinâmico

O caso que mais tenta a concatenação. A solução é montar os **placeholders**
dinamicamente, nunca os valores:

**Antes**
```python
sql = "SELECT * FROM produtos WHERE 1=1"
if termo:
    sql += " AND nome LIKE '%" + termo + "%'"
if categoria:
    sql += " AND categoria = '" + categoria + "'"
cursor.execute(sql)
```

**Depois**
```python
sql = "SELECT * FROM produtos WHERE 1=1"
params = []
if termo:
    sql += " AND nome LIKE ?"
    params.append(f"%{termo}%")      # o curinga vai no VALOR, não no SQL
if categoria:
    sql += " AND categoria = ?"
    params.append(categoria)
cursor.execute(sql, params)
```

**Nunca parametrizável:** nome de tabela ou coluna não aceita placeholder. Se
precisar ser dinâmico, valide contra uma lista fixa de valores permitidos:

```python
COLUNAS_ORDENACAO = {"nome", "preco", "criado_em"}
if ordenar_por not in COLUNAS_ORDENACAO:
    raise ValidationError("Coluna de ordenação inválida")
sql += f" ORDER BY {ordenar_por}"   # seguro: valor veio de allow-list
```

---

## P-02 · Extrair configuração para o ambiente

**Resolve:** AP-02, AP-06.

**Antes** (`utils.js`)
```javascript
const config = {
    dbUser: "admin_master",
    dbPass: "senha_super_secreta_prod_123",
    paymentGatewayKey: "pk_live_1234567890abcdef",
    port: 3000
};
```

**Depois** (`config/settings.js`)
```javascript
function required(name) {
    const value = process.env[name];
    if (!value) throw new Error(`Variável de ambiente obrigatória ausente: ${name}`);
    return value;
}

module.exports = {
    db: { user: required('DB_USER'), password: required('DB_PASSWORD') },
    paymentGatewayKey: required('PAYMENT_GATEWAY_KEY'),
    port: parseInt(process.env.PORT || '3000', 10),
    debug: process.env.NODE_ENV !== 'production',
};
```

**`.env.example`** (versionado, sem valores reais)
```
DB_USER=
DB_PASSWORD=
PAYMENT_GATEWAY_KEY=
PORT=3000
NODE_ENV=development
```

Três detalhes que importam: segredo **sem default** (falha no boot em vez de subir
inseguro), `debug` derivado do ambiente em vez de literal, e `.env` no `.gitignore`.
Registre no relatório que as chaves expostas precisam ser **rotacionadas** — elas
estão no histórico do Git.

---

## P-03 · Hash de senha e remoção da serialização

**Resolve:** AP-03. São três correções distintas; aplique as três.

**Antes**
```python
def set_password(self, pwd):
    self.password = hashlib.md5(pwd.encode()).hexdigest()

def check_password(self, pwd):
    return self.password == hashlib.md5(pwd.encode()).hexdigest()

def to_dict(self):
    return {'id': self.id, 'email': self.email, 'password': self.password}
```

**Depois**
```python
from werkzeug.security import generate_password_hash, check_password_hash

def set_password(self, pwd):
    self.password_hash = generate_password_hash(pwd)   # salt + algoritmo lento

def check_password(self, pwd):
    return check_password_hash(self.password_hash, pwd)

def to_dict(self):
    # Lista de permissão: campo novo só aparece aqui se for deliberadamente público
    return {'id': self.id, 'name': self.name, 'email': self.email, 'role': self.role}
```

**Login sem comparar senha no SQL:**
```python
user = repo.find_by_email(email)           # busca só por e-mail
if user is None or not user.check_password(senha):
    raise UnauthorizedError("Credenciais inválidas")   # mensagem única
```

A mensagem genérica é intencional: distinguir "e-mail não existe" de "senha errada"
entrega ao atacante a lista de e-mails válidos.

**Migração:** hashes MD5 antigos não são reversíveis. Force redefinição de senha, ou
re-hash no próximo login bem-sucedido.

---

## P-04 · Quebrar God Class em camadas

**Resolve:** AP-04.

**Antes** — `AppManager.js`, uma classe com DDL, seed, rotas, pagamento e auditoria:
```javascript
class AppManager {
    constructor() { this.db = new sqlite3.Database(':memory:'); }
    initDb() { /* CREATE TABLE x5 + INSERT de seed */ }
    setupRoutes(app) {
        app.post('/api/checkout', (req, res) => { /* 50 linhas de tudo */ });
        app.get('/api/admin/financial-report', (req, res) => { /* 50 linhas */ });
    }
}
```

**Depois** — responsabilidades separadas por arquivo:
```
src/
├── config/settings.js
├── database/connection.js        # só conexão
├── database/migrations.js        # só DDL
├── database/seed.js              # só dados iniciais
├── models/course-model.js
├── models/enrollment-model.js
├── services/checkout-service.js  # o fluxo de negócio
├── controllers/checkout-controller.js
├── views/checkout-routes.js
└── app.js                        # composition root
```

Processo — extraia **uma responsabilidade por vez**, rodando a aplicação entre cada
passo:

1. DDL e seed saem para `database/`;
2. Cada grupo de queries vira um model por entidade;
3. O fluxo de negócio vira serviço;
4. O handler vira controller magro;
5. A declaração da rota vira arquivo de rotas;
6. `AppManager` é **deletado** — não deixe a classe antiga ao lado da nova.

---

## P-05 · Remover ou proteger endpoint administrativo

**Resolve:** AP-05.

**Antes**
```python
@app.route("/admin/query", methods=["POST"])
def executar_query():
    query = request.get_json().get("sql", "")
    cursor.execute(query)              # SQL arbitrário, sem autenticação
    if query.strip().upper().startswith("SELECT"):
        return jsonify(cursor.fetchall())
    db.commit()                        # qualquer DDL/DML é persistido
```

**Depois** — a correção é **remover**. Não existe uso legítimo de um executor de SQL
arbitrário exposto por HTTP; a checagem de `startswith("SELECT")` não restringe nada,
apenas escolhe entre ler e gravar.

Se houver necessidade real de manutenção, ela vira script de CLI, executado
localmente, fora do processo web:

```python
# scripts/db_console.py — executado por quem já tem acesso à máquina
if __name__ == "__main__":
    print(run_query(sys.argv[1]))
```

Para rotas administrativas que **precisam** existir (reset em ambiente de dev):

```python
@admin_bp.route("/admin/reset-db", methods=["POST"])
@require_admin                                  # autenticação + papel
def reset_db():
    if settings.ENVIRONMENT == "production":
        raise ForbiddenError("Operação indisponível em produção")
    ...
```

Remoção de endpoint é mudança de contrato — declare-a explicitamente no relatório
final da Fase 3.

---

## P-06 · Endpoint de health sem vazamento

**Resolve:** AP-06.

**Antes**
```python
@app.route("/health")
def health():
    return jsonify({
        "status": "ok", "ambiente": "producao", "debug": True,
        "secret_key": app.config["SECRET_KEY"],       # segredo na resposta
        "db_path": "/var/app/loja.db",
    })
```

**Depois**
```python
@system_bp.get("/health")
def health():
    database_ok = health_model.ping()             # SELECT 1 via model, sem SQL na rota
    return jsonify({
        "status": "ok" if database_ok else "erro",
        "database": "connected" if database_ok else "unavailable",
        "versao": settings.APP_VERSION,
    }), 200 if database_ok else 503
```

Health check responde **uma** pergunta: o processo (e suas dependências) está vivo?
Segredo, flags de debug, ambiente e caminho de banco saem **sempre** — são
reconhecimento gratuito para quem sonda a aplicação. Campos operacionais não
sensíveis que clientes já consomem (status, conectividade, contagens públicas) podem
ficar, para não quebrar o contrato; declare na Fase 3 quais campos foram removidos.

---

## P-07 · Substituir estado global por escopo e injeção

**Resolve:** AP-07.

**Antes**
```python
db_connection = None

def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect(db_path, check_same_thread=False)
    return db_connection
```

**Depois** — conexão com escopo de requisição:
```python
from flask import g

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(settings.DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

# no factory: app.teardown_appcontext(close_db)
```

**Melhor ainda** — injetar o repositório, o que torna o código testável:
```python
class ProdutoRepository:
    def __init__(self, connection):
        self._conn = connection          # recebe, não importa um global

    def find_by_id(self, produto_id):
        cur = self._conn.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,))
        return cur.fetchone()

# Teste: ProdutoRepository(sqlite3.connect(":memory:")) — sem tocar no global
```

**Escritas relacionadas em transação:**
```python
try:
    conn.execute("INSERT INTO pedidos ...", params)
    conn.execute("UPDATE produtos SET estoque = estoque - ? ...", params)
    conn.commit()
except Exception:
    conn.rollback()      # ou tudo, ou nada
    raise
```

Para cache global, use uma instância com limite e TTL, injetada como dependência —
`globalCache = {}` cresce sem limite até o processo morrer.

---

## P-08 · Extrair regra de negócio do controller

**Resolve:** AP-08.

**Antes**
```python
@app.route("/pedidos", methods=["POST"])
def criar_pedido():
    resultado = models.criar_pedido(dados)
    print("ENVIANDO EMAIL: Pedido " + str(resultado["pedido_id"]) + " criado")
    print("ENVIANDO SMS: ...")
    print("ENVIANDO PUSH: ...")
    return jsonify(resultado), 201
```

**Depois** — serviço com dependências injetadas:
```python
# services/pedido_service.py
class PedidoService:
    def __init__(self, repo, notificador):
        self._repo = repo
        self._notificador = notificador

    def criar(self, dados):
        pedido = self._repo.criar(dados)
        self._notificador.pedido_criado(pedido)   # canais são detalhe do notificador
        return pedido

    def alterar_status(self, pedido_id, novo_status):
        if novo_status not in StatusPedido.valores():
            raise ValidationError(f"Status inválido: {novo_status}")
        pedido = self._repo.buscar(pedido_id)
        if pedido is None:
            raise NotFoundError("Pedido não encontrado")

        if novo_status == StatusPedido.CANCELADO:
            self._repo.devolver_estoque(pedido)    # regra realmente executada
        self._repo.atualizar_status(pedido_id, novo_status)
        return pedido
```

```python
# controllers/pedido_controller.py
class PedidoController:
    def __init__(self, service):
        self._service = service

    def criar(self, dados):
        return self._service.criar(dados)
```

```python
# views/pedido_routes.py
@pedido_bp.route("/pedidos", methods=["POST"])
def criar_pedido():
    return jsonify(controller.criar(request.get_json())), 201
```

Ganho concreto: qualquer ponto de entrada (worker, CLI, outro endpoint) cria pedido
com as mesmas notificações, e o teste injeta um notificador falso sem capturar
stdout.

**Atenção às regras "anunciadas mas não implementadas".** Um comentário ou `print`
dizendo "cancelar devolve estoque" sem código que devolva é **bug de negócio**: o
estoque nunca é reposto. Implemente de verdade e registre como correção funcional.

**Enum no lugar da lista hardcoded:**
```python
class StatusPedido(str, Enum):
    PENDENTE = "pendente"
    APROVADO = "aprovado"
    CANCELADO = "cancelado"

    @classmethod
    def valores(cls):
        return {s.value for s in cls}
```

---

## P-09 · Substituir APIs deprecated

**Resolve:** AP-09. Troque pelo equivalente moderno, sem alterar comportamento.

**Python**
```python
# Antes                                  # Depois
datetime.utcnow()                        datetime.now(timezone.utc)
User.query.get(user_id)                  db.session.get(User, user_id)
hashlib.md5(pwd.encode()).hexdigest()    generate_password_hash(pwd)
```

Atenção ao caso de `utcnow()`: ele devolve datetime **naive** (sem timezone) e
`now(timezone.utc)` devolve **aware**. Comparar um naive com um aware levanta
`TypeError`, então a troca precisa ser consistente em todo o projeto — inclusive nos
defaults das colunas do ORM:

```python
# models/task.py
created_at = db.Column(db.DateTime(timezone=True),
                       default=lambda: datetime.now(timezone.utc))
```

**JavaScript**
```javascript
// Antes                                 // Depois
new Buffer(data)                         Buffer.from(data)
url.parse(req.url)                       new URL(req.url, `http://${req.headers.host}`)
app.use(bodyParser.json())               app.use(express.json())
crypto.createCipher(algo, key)           crypto.createCipheriv(algo, key, iv)
```

Verifique a versão declarada no manifesto antes de trocar, e rode a validação depois
— substituição de API é onde regressão silenciosa aparece com mais frequência.

---

## P-10 · Eliminar N+1

**Resolve:** AP-10.

**Antes**
```python
tasks = Task.query.all()
for t in tasks:
    user = User.query.get(t.user_id)         # 1 query por task
    cat = Category.query.get(t.category_id)  # +1 query por task
```

**Depois (ORM)** — carregamento antecipado:
```python
from sqlalchemy.orm import joinedload

tasks = db.session.execute(
    select(Task).options(joinedload(Task.user), joinedload(Task.category))
).scalars().all()
```

**Depois (sem ORM)** — busca em lote e mapa em memória:
```python
tasks = repo.listar_tasks()
user_ids = {t.user_id for t in tasks if t.user_id}
users = {u.id: u for u in repo.buscar_usuarios_por_ids(user_ids)}   # 1 query
for t in tasks:
    t.user_name = users.get(t.user_id).name if t.user_id in users else None
```

**Callbacks aninhados (Node)** — o caso mais grave, porque junta N+1 com pirâmide de
callbacks e contadores manuais de conclusão:

```javascript
// Antes: db.all(courses) → forEach → db.all(enrollments) → forEach →
//        db.get(user) → db.get(payment), com coursesPending/enrPending decrementando
```

```javascript
// Depois: uma query com JOIN e agregação, em async/await
const rows = await db.all(`
    SELECT c.id, c.title, u.name AS student, p.amount, p.status
    FROM courses c
    LEFT JOIN enrollments e ON e.course_id = c.id
    LEFT JOIN users u       ON u.id = e.user_id
    LEFT JOIN payments p    ON p.enrollment_id = e.id
`);
const report = groupByCourse(rows);   // agregação em memória, 1 ida ao banco
```

Além da performance, isto elimina uma classe de bug: com contadores manuais, um erro
em qualquer callback intermediário faz a resposta nunca ser enviada e a requisição
pendurar até o timeout.

---

## P-11 · Centralizar validação em schema

**Resolve:** AP-11.

**Antes** — validação manual, repetida em cada rota, divergindo entre elas:
```python
if not data: return jsonify({'error': 'Dados inválidos'}), 400
if not name: return jsonify({'error': 'Nome é obrigatório'}), 400
if not email: return jsonify({'error': 'Email é obrigatório'}), 400
if not re.match(r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$', email):
    return jsonify({'error': 'Email inválido'}), 400
if len(password) < 4: return jsonify({'error': 'Senha muito curta'}), 400
```

**Depois** — schema declarativo, fonte única da regra:
```python
# schemas/user_schema.py
class UserCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=12))
    role = fields.Str(load_default="user", validate=validate.OneOf(["user", "admin"]))
```

```python
# views/user_routes.py
@user_bp.route("/users", methods=["POST"])
def create_user():
    dados = UserCreateSchema().load(request.get_json())   # erro → handler central
    return jsonify(controller.create(dados)), 201
```

Três ganhos: `fields.Email` cobre casos que o regex caseiro erra (o regex do exemplo
aceita `a@b`, sem TLD); a regra vive em um lugar só; e o erro de validação vira
exceção tratada pelo handler central, com formato consistente.

Se o manifesto já declara `marshmallow`/`pydantic`/`zod` sem uso, use — a dependência
já está paga.

---

## P-12 · Centralizar tratamento de erro

**Resolve:** AP-12.

**Antes**
```python
try:
    ...
except:
    return jsonify({'error': 'Erro interno'}), 500   # causa perdida, log vazio
```

**Depois** — erros de domínio tipados e um handler único:
```python
# errors.py
class AppError(Exception):
    status_code = 500
    message = "Erro interno"

class NotFoundError(AppError):      status_code, message = 404, "Recurso não encontrado"
class ValidationError(AppError):    status_code, message = 400, "Dados inválidos"
class UnauthorizedError(AppError):  status_code, message = 401, "Não autorizado"
class ConflictError(AppError):      status_code, message = 409, "Conflito"
```

```python
# middlewares/error_handler.py
def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({"error": err.message}), err.status_code

    @app.errorhandler(MarshmallowValidationError)
    def handle_schema_error(err):
        return jsonify({"error": "Dados inválidos", "fields": err.messages}), 400

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        app.logger.exception("Erro não tratado")      # stack trace no servidor
        return jsonify({"error": "Erro interno"}), 500  # sem detalhe para o cliente
```

As camadas internas passam a apenas lançar:
```python
if task is None:
    raise NotFoundError("Task não encontrada")
```

**Em Node**, o equivalente é o middleware de erro de 4 argumentos, registrado **por
último**, com as rotas usando `async` e um wrapper que encaminha rejeições:

```javascript
app.use((err, req, res, next) => {
    const status = err.statusCode || 500;
    if (status >= 500) console.error(err);
    res.status(status).json({ error: status >= 500 ? 'Erro interno' : err.message });
});
```

E nunca ignore o `err` de um callback: `(err) => { res.send("ok") }` responde sucesso
para uma operação que falhou.

---

## P-13 · Transação e integridade referencial

**Resolve:** AP-13 (escritas encadeadas sem transação, exclusão que deixa órfãos,
schema sem FOREIGN KEY).

**Antes** (Node, callbacks encadeados sem transação)
```javascript
db.run("INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)", [userId, cid], function (err) {
    const enrId = this.lastID;
    db.run("INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)", [enrId, price, status], (err) => {
        // se este INSERT falhar, a matrícula acima já está gravada: aluno matriculado sem pagamento
    });
});
```

**Depois** (Unit of Work: ou tudo, ou nada)
```javascript
// database/connection.js
async transaction(work) {
    await this.run('BEGIN TRANSACTION');
    try {
        const result = await work(this);
        await this.run('COMMIT');
        return result;
    } catch (error) {
        await this.run('ROLLBACK');
        throw error;
    }
}

// services/checkout-service.js
return this.db.transaction(async (tx) => {
    const enrollmentId = await this.enrollments.create({ userId, courseId }, tx);
    await this.payments.create({ enrollmentId, amount: course.price, status }, tx);
    return { enrollmentId };
});
```

**Schema** — declare a relação e o que acontece na exclusão; no SQLite, ligue a
verificação por conexão:
```sql
-- Antes
CREATE TABLE enrollments (id INTEGER PRIMARY KEY, user_id INTEGER, course_id INTEGER);

-- Depois
PRAGMA foreign_keys = ON;
CREATE TABLE enrollments (
    id        INTEGER PRIMARY KEY,
    user_id   INTEGER NOT NULL REFERENCES users(id)   ON DELETE CASCADE,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE
);
```

Em Python com `sqlite3`, o equivalente é `try: ... conn.commit() except: conn.rollback(); raise`;
com SQLAlchemy, um único `session.commit()` ao final do caso de uso (e `rollback()`
no handler de erro central). Decida explicitamente entre **cascade** (apagar
dependentes) e **bloqueio** (recusar a exclusão com 409) — e registre a escolha como
mudança de contrato se ela alterar uma resposta.

---

## P-14 · Legibilidade: constantes nomeadas, nomes claros, imports mortos

**Resolve:** AP-14.

**Antes**
```python
import json, os, sys, time            # nenhum usado

if faturamento > 10000:
    desconto = faturamento * 0.1
elif faturamento > 5000:
    desconto = faturamento * 0.05
elif faturamento > 1000:
    desconto = faturamento * 0.02
```

**Depois**
```python
# limiar mínimo de faturamento -> percentual de desconto (do maior para o menor)
FAIXAS_DESCONTO = ((10_000, 0.10), (5_000, 0.05), (1_000, 0.02))

def calcular_desconto(faturamento):
    for limiar, percentual in FAIXAS_DESCONTO:
        if faturamento > limiar:
            return faturamento * percentual
    return 0.0
```

**Antes** (JS, nomes opacos e literal mágico)
```javascript
let u = req.body.usr, e = req.body.eml, cc = req.body.card;
let status = cc.startsWith("4") ? "PAID" : "DENIED";
```

**Depois**
```javascript
const PaymentStatus = Object.freeze({ PAID: 'PAID', DENIED: 'DENIED' });
const APPROVED_CARD_PREFIX = '4'; // regra da simulação do gateway

const { usr: name, eml: email, card: cardNumber } = req.body; // contrato HTTP mantido
const status = cardNumber.startsWith(APPROVED_CARD_PREFIX) ? PaymentStatus.PAID : PaymentStatus.DENIED;
```

Regras: renomeie **variáveis internas**, nunca os campos do contrato HTTP (`usr`,
`eml` continuam sendo aceitos — mudar isso quebra clientes); apague imports após
confirmar com `grep -c` que o símbolo não é usado; enumere status/roles num único
lugar e importe de lá.

---

## Validação após cada padrão aplicado

Depois de cada transformação, antes de seguir para a próxima:

1. A aplicação ainda sobe?
2. Os endpoints afetados ainda respondem igual?
3. O sinal de detecção do anti-pattern sumiu (rode o grep da Fase 2)?

Se qualquer resposta for "não", corrija antes de continuar. Acumular transformações
sem validar torna impossível identificar qual delas quebrou o quê.
