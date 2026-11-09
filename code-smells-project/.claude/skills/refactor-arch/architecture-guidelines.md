# Guidelines de Arquitetura — MVC Alvo

Referência da **Fase 3**. Define a estrutura de destino e a responsabilidade de cada
camada. As regras são conceituais; a sintaxe varia por stack, a divisão não.

## A regra que resume todas as outras

**Cada camada conhece apenas a camada imediatamente abaixo.** As dependências
apontam para dentro: rota → controller → serviço → model → banco. Nunca o inverso.
Um model que importa `request` ou devolve `jsonify` quebrou a regra; uma rota que
monta SQL também.

---

## Estrutura de diretórios

Estrutura de referência, a ser adaptada às convenções da stack detectada:

```
src/                          (ou raiz, conforme convenção da linguagem)
├── config/
│   └── settings.*            # configuração a partir de variáveis de ambiente
├── models/
│   ├── <entidade>_model.*    # um arquivo por entidade do domínio
│   └── ...
├── controllers/
│   ├── <entidade>_controller.*
│   └── ...
├── services/                 # regra de negócio que cruza entidades (opcional)
│   └── <fluxo>_service.*
├── views/  (ou routes/)
│   └── routes.*              # mapeamento HTTP → controller
├── middlewares/
│   ├── error_handler.*       # tratamento de erro centralizado
│   └── auth.*                # autenticação/autorização, quando aplicável
├── repositories/             # acesso a dados, quando separado dos models (opcional)
└── app.*                     # composition root
.env.example                  # nomes das variáveis, sem valores reais
```

**Adaptação por stack** — o nome das pastas segue a convenção da linguagem, a
separação permanece:

- **Flask:** `views/` são Blueprints; `app.py` usa o padrão *application factory*.
- **Express:** `views/` são Routers; `app.js` monta os routers e sobe o servidor.
- **Django:** já impõe apps; o alvo é respeitar `models`/`views`/`serializers` e
  extrair a regra para `services.py`.
- **NestJS:** já é MVC por construção; o alvo é eliminar lógica dos controllers.

Não force pastas vazias. Um projeto sem autenticação não precisa de
`middlewares/auth`. Estrutura existe para separar o que existe, não para preencher
um gabarito.

---

## Camada Models

**Responsabilidade:** representar as entidades do domínio e o acesso a seus dados.

Deve conter:

- Definição da entidade (campos, tipos, relacionamentos);
- Operações de persistência (buscar, criar, atualizar, remover), **sempre
  parametrizadas**;
- Invariantes da própria entidade (ex.: "preço não pode ser negativo");
- Serialização explícita de saída, expondo **apenas campos públicos**.

Não deve conter:

- Nada de HTTP — sem `request`, `response`, `jsonify`, status code;
- Regra que cruza várias entidades (isso é serviço);
- Efeito colateral externo (e-mail, fila, gateway de pagamento).

**Serialização é lista de permissão, nunca espelho da tabela.** Um `to_dict()` que
devolve a linha inteira vaza o campo de senha no dia em que ele for adicionado.
Liste os campos públicos explicitamente.

---

## Camada Controllers

**Responsabilidade:** orquestrar o fluxo de um caso de uso.

Deve conter:

- Recebimento dos dados já validados;
- Chamada aos models/serviços na ordem correta;
- Decisão sobre o resultado (encontrado/não encontrado, permitido/negado);
- Tradução do resultado em algo que a view sabe devolver.

Não deve conter:

- SQL ou chamada direta ao driver de banco;
- Montagem de resposta HTTP crua (isso é da view, quando a stack separa);
- Efeito colateral direto — envie um evento ou chame um serviço injetado.

**Teste como critério:** se o controller não puder ser testado sem subir o servidor
HTTP, ele ainda está acoplado demais.

---

## Camada Views / Routes

**Responsabilidade:** a fronteira HTTP. É a camada mais fina do sistema.

Deve conter:

- Mapeamento de método + caminho → função do controller;
- Extração de parâmetros (path, query, body);
- Validação do **contrato** de entrada (campo obrigatório, tipo, formato);
- Conversão do retorno do controller em resposta HTTP com status correto.

Não deve conter:

- Regra de negócio, acesso a banco, ou qualquer decisão de domínio.

**Tamanho como sinal:** um handler de rota com mais de ~15 linhas quase sempre está
fazendo trabalho de controller. Use isso como gatilho de revisão.

---

## Camada Services (quando necessária)

Crie apenas quando houver regra que **cruza entidades** ou orquestra efeitos
colaterais — checkout que cria usuário, cobra cartão, matricula e audita; mudança de
status que repõe estoque e notifica.

- Um serviço por fluxo de negócio, nomeado pelo fluxo (`checkout_service`), não por
  entidade;
- Dependências **injetadas** (gateway, notificador, repositório), nunca instanciadas
  dentro — é isso que permite substituir por um duplo no teste;
- Transação envolvendo as escritas relacionadas: ou tudo acontece, ou nada.

Se a regra envolve uma entidade só, ela pertence ao model. Não crie serviço anêmico
que apenas repassa chamadas.

---

## Config

**Toda** configuração vem de variável de ambiente, com um único ponto de leitura.

Regras:

- Nenhum segredo literal no código — sem exceção, nem para "valor de dev";
- Segredo **sem default**: a aplicação deve falhar no boot se faltar, não subir
  insegura com um fallback silencioso;
- Valores não sensíveis (porta, host) podem ter default razoável;
- `.env.example` versionado com os **nomes** das variáveis e valores de exemplo
  vazios; `.env` real no `.gitignore`;
- Validação na inicialização: se falta variável obrigatória, erro claro dizendo qual.

```python
# Padrão de referência
class Settings:
    SECRET_KEY = os.environ["SECRET_KEY"]           # obrigatório, sem default
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
    PORT = int(os.environ.get("PORT", "5000"))
```

**Segredo que já esteve versionado está comprometido.** Mover para env var não basta
— a recomendação inclui rotacionar a chave.

---

## Error handling centralizado

Um único ponto converte exceção em resposta HTTP. As camadas internas lançam erros de
domínio tipados; elas não sabem o que é status code.

Estrutura:

1. **Erros de domínio tipados** — `NotFoundError`, `ValidationError`,
   `UnauthorizedError`, `ConflictError`;
2. **Um handler** que mapeia cada tipo para seu status (404, 400, 401, 409) e
   qualquer exceção não prevista para 500;
3. **Formato de resposta único** para toda a API;
4. **Log com o stack trace real** no servidor; para o cliente, mensagem sem detalhe
   interno.

O que isso elimina: o `except: return 500` genérico que engole a causa, e a
inconsistência de cada rota inventar seu próprio formato de erro.

---

## Entry point (composition root)

O arquivo de entrada apenas **monta** a aplicação:

1. Carrega a configuração;
2. Instancia as dependências concretas (conexão, gateways, notificadores);
3. Injeta nos controllers/serviços;
4. Registra rotas e middlewares — o error handler **por último**, para capturar tudo;
5. Sobe o servidor.

Não deve conter: rota declarada inline, regra de negócio, SQL, segredo.

Se a stack permitir, use *factory* (`create_app()`): a aplicação pode ser criada com
configuração de teste, sem subir servidor real.

---

## Checklist de conformidade

Ao final da Fase 3, todas devem ser verdadeiras:

- [ ] Nenhum segredo literal no código; config lida de env var
- [ ] `.env.example` criado; `.env` no `.gitignore`
- [ ] Models sem dependência de HTTP; serialização com lista de permissão
- [ ] Toda query parametrizada
- [ ] Controllers sem SQL e sem efeito colateral direto
- [ ] Rotas apenas mapeiam e validam contrato
- [ ] Regra que cruza entidades isolada em serviço com dependências injetadas
- [ ] Error handler centralizado; erros de domínio tipados
- [ ] Entry point é só composition root
- [ ] Arquivos antigos removidos, não duplicados
- [ ] Todas as rotas originais preservadas (salvo remoções justificadas na auditoria)
