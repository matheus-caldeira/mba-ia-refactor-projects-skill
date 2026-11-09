# Análise de Projeto — Heurísticas de Detecção

Referência da **Fase 1**. O objetivo é responder cinco perguntas com evidência, não
com suposição: qual a linguagem, qual o framework, qual o banco, qual o domínio, e
como o código está organizado hoje.

Regra geral: **o manifesto de dependências é a fonte da verdade**. Nomes de pastas
mentem (uma pasta `models/` pode conter rotas); o manifesto, não.

---

## 1. Detecção de linguagem

Ordem de verificação — pare no primeiro que casar:

| Sinal | Linguagem |
|---|---|
| `requirements.txt`, `pyproject.toml`, `Pipfile`, `setup.py`, `*.py` | Python |
| `package.json`, `*.js`, `*.mjs`, `*.ts` | JavaScript / TypeScript |
| `go.mod`, `*.go` | Go |
| `composer.json`, `*.php` | PHP |
| `pom.xml`, `build.gradle`, `*.java` | Java |
| `Gemfile`, `*.rb` | Ruby |
| `*.csproj`, `*.cs` | C# / .NET |

Comando de apoio (conta fontes por extensão, ignorando dependências):

```bash
find . -type f \( -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.go" -o -name "*.php" -o -name "*.rb" \) \
  -not -path "*/node_modules/*" -not -path "*/venv/*" -not -path "*/.venv/*" \
  -not -path "*/__pycache__/*" -not -path "*/dist/*" -not -path "*/.git/*" | sed 's/.*\.//' | sort | uniq -c
```

Se mais de uma linguagem aparecer, a **principal** é a que contém o entry point do
servidor; as outras são anotadas como secundárias (scripts, build, frontend).

### Versão da linguagem

Procure em `.python-version`, `runtime.txt`, `engines` no `package.json`,
`go.mod`, ou na diretiva de versão do manifesto. Não invente — se não houver
declaração, reporte "não declarada" e, se puder executar, use `python3 --version` /
`node --version` do ambiente.

---

## 2. Detecção de framework

Leia o manifesto e cruze com os imports do entry point.

### Python

| Dependência / import | Framework |
|---|---|
| `flask`, `from flask import Flask` | Flask |
| `django`, `manage.py`, `settings.py` | Django |
| `fastapi`, `from fastapi import` | FastAPI |
| `bottle`, `falcon`, `pyramid` | (respectivo) |

Extensões relevantes a anotar: `flask-sqlalchemy` (ORM), `flask-cors` (CORS),
`marshmallow`/`pydantic` (serialização), `flask-migrate`, `celery`.

### Node.js

| Dependência / import | Framework |
|---|---|
| `express`, `require('express')` | Express |
| `fastify` | Fastify |
| `@nestjs/core` | NestJS |
| `koa` | Koa |
| `next` | Next.js |

### Extração da versão

A versão declarada no manifesto é a que vale para o relatório:

```bash
# Python
grep -iE "^(flask|django|fastapi|sqlalchemy)" requirements.txt

# Node
node -e "const p=require('./package.json'); console.log({...p.dependencies,...p.devDependencies})" 2>/dev/null \
  || grep -A20 '"dependencies"' package.json
```

Cuidado: `^4.18.2` significa "4.18.2 ou compatível superior". Reporte a versão
declarada e, se `package-lock.json`/`venv` existir e for relevante, a resolvida.

---

## 3. Detecção de banco de dados

Duas frentes: **o driver** (o quê) e **o schema** (quais dados).

### Driver / camada de acesso

| Sinal | Persistência |
|---|---|
| `import sqlite3`, `require('sqlite3')`, `*.db`, `:memory:` | SQLite (driver cru) |
| `psycopg2`, `pg`, `postgres://` | PostgreSQL |
| `mysql`, `mysql2`, `PyMySQL` | MySQL / MariaDB |
| `sqlalchemy`, `SQLALCHEMY_DATABASE_URI`, `db.Model` | SQLAlchemy (ORM) |
| `sequelize`, `typeorm`, `prisma`, `mongoose` | ORM/ODM Node |
| `pymongo`, `mongodb://` | MongoDB |
| `redis` | Redis (cache/fila) |

Distinga **driver cru** de **ORM**: é a diferença entre procurar SQL injection por
concatenação (driver cru) ou procurar N+1 e lazy loading (ORM). Ambos têm seus
próprios anti-patterns no catálogo.

### Schema e tabelas

```bash
# DDL explícito
grep -rniE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "create table[[:space:]]+(if not exists[[:space:]]+)?[a-z_]+" --include='*.py' --include='*.js' --include='*.sql' .

# Modelos ORM
grep -rn --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "__tablename__\|db.Model\|sequelize.define\|@Entity\|class.*\(Base\)" --include='*.py' --include='*.js' .

# Alvos de query
grep -rhoiE --exclude-dir={venv,.venv,node_modules,.git,.claude,dist,__pycache__} "(from|into|update|join)[[:space:]]+[a-z_]{3,}" --include='*.py' --include='*.js' . | sort -u | head -30
```

Anote também **onde o schema é criado**: DDL embutido no código da aplicação
(`initDb()`, `db.create_all()`) é um achado arquitetural — migrations é o lugar
certo — e vale registrar já na Fase 1 para a Fase 2 confirmar.

### Localização do banco

String de conexão hardcoded, variável de ambiente, ou `:memory:`. Banco em memória
significa que **os dados somem a cada restart** — relevante para o domínio e para o
plano de validação da Fase 3 (o seed roda no boot).

---

## 4. Inferência do domínio

O domínio se descreve em **linguagem de negócio**, não técnica. "API REST com 4
tabelas" não é domínio; "plataforma de cursos online com matrícula e checkout" é.

Fontes de evidência, em ordem de confiabilidade:

1. **Nomes das tabelas/entidades** — `users`, `courses`, `enrollments`, `payments`
   descrevem um LMS com cobrança. `produtos`, `pedidos`, `itens_pedido` descrevem
   e-commerce. `tasks`, `categories`, `users` descrevem gestão de tarefas.
2. **Caminhos das rotas** — `/api/checkout`, `/reports/summary`, `/tasks/<id>`.
3. **README do projeto** — útil, mas confirme contra o código; README desatualiza.
4. **Mensagens e literais de texto** — e-mails, logs e mensagens de erro revelam o
   fluxo real.

Descreva também os **fluxos principais** (ex.: "checkout: cria usuário se não
existir → cobra cartão → matricula → registra auditoria"), porque é isso que a
Fase 3 precisa preservar.

---

## 5. Mapeamento da arquitetura atual

Responda, com arquivo e linha:

- **Onde está o entry point?** (`app.py`, `src/app.js`, `main.go`)
- **Onde as rotas são declaradas?** Concentradas num arquivo, espalhadas, ou em
  módulos por recurso (`Blueprint`, `Router`, `Controller`)?
- **Onde as queries são montadas?** Dentro do handler da rota, num model, ou num
  repositório?
- **Onde está a regra de negócio?** Se a resposta for "dentro da rota", já há
  achado HIGH garantido.
- **Existe camada de configuração?** Ou os valores estão hardcoded?
- **Existe tratamento de erro centralizado?**
- **Existem testes?** (`tests/`, `*_test.py`, `*.spec.js`)

### Escala de classificação

| Classificação | Critério |
|---|---|
| **Monolítica** | Rotas, queries, regra de negócio e config no mesmo arquivo (ou 2-4 arquivos sem fronteira clara). Nenhuma camada nomeada. |
| **Parcialmente estruturada** | Existem pastas por camada (`models/`, `routes/`, `services/`), mas as responsabilidades vazam: regra de negócio nas rotas, serialização no model, serviços não usados pelas rotas. |
| **Estruturada** | Camadas separadas e respeitadas, dependências injetadas, config externalizada. Ainda pode ter smells pontuais. |

**Atenção ao caso "parcialmente estruturada":** a presença de pastas por camada
induz a concluir que está tudo bem. Verifique se a separação é real — abra um
arquivo de rota e veja se ele contém apenas mapeamento HTTP. Um `routes/` com 300
linhas por arquivo e acesso direto ao ORM é monolito com pastas bonitas.

Anote ainda:

- **Maiores arquivos** (`wc -l`), candidatos naturais a God Class.
- **Estado global mutável** (variáveis de módulo mutáveis, singletons, caches).
- **Acoplamento**: quem importa quem; imports circulares.

```bash
# Tamanho dos fontes, maiores primeiro
find . -name "*.py" -o -name "*.js" | grep -vE "node_modules|venv|__pycache__" | xargs wc -l | sort -rn | head -15
```

---

## 6. Saída da fase

Consolide tudo no bloco `PHASE 1: PROJECT ANALYSIS` definido no `SKILL.md`. Cada
campo deve ser sustentável por evidência — se um campo não pôde ser determinado,
escreva "não detectado" em vez de preencher com palpite.
