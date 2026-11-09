---
name: refactor-arch
description: Audita e refatora uma codebase de backend para o padrão MVC, em qualquer linguagem ou framework. Executa três fases sequenciais — análise da stack, auditoria de anti-patterns com relatório e confirmação, e refatoração validada. Use quando o usuário pedir para auditar arquitetura, encontrar code smells, avaliar segurança estrutural, reorganizar um projeto em camadas, migrar para MVC, ou disser "refatora esse projeto", "esse código tá uma bagunça", "separa isso em camadas", "roda a auditoria de arquitetura".
---

# refactor-arch — Auditoria e Refatoração Arquitetural

Transforma um projeto legado de backend em uma aplicação organizada no padrão MVC,
sem quebrar o comportamento existente.

A skill é **agnóstica de tecnologia**: toda decisão parte do que foi detectado na
Fase 1, nunca de suposições sobre uma stack específica. O mesmo procedimento roda
em Python/Flask, Node.js/Express, ou qualquer outro backend com rotas e persistência.

## Princípios inegociáveis

Estes valem nas três fases e não são negociáveis por conveniência:

1. **Nada é modificado antes do "sim" do usuário.** As Fases 1 e 2 são estritamente
   read-only. Nenhum `Write`, `Edit` ou comando que altere arquivo pode ocorrer
   antes da confirmação explícita ao fim da Fase 2.
2. **Todo achado cita arquivo e linha reais.** Nunca reporte um problema sem ter
   lido o trecho. Se você não consegue apontar a linha, o achado não entra no
   relatório.
3. **Comportamento preservado.** A refatoração reorganiza e corrige defeitos; ela
   não inventa funcionalidade nem remove endpoints. Cada rota que existia antes
   precisa continuar respondendo depois.
4. **Validação com execução real.** "Deve funcionar" não é validação. A Fase 3 só
   termina depois que a aplicação subiu de fato e os endpoints responderam.
5. **Sem resultado inventado.** Se algo não pôde ser validado (falta dependência,
   porta ocupada, banco ausente), diga explicitamente que ficou pendente e por quê.

## Invocação e argumentos

```
/refactor-arch                                  # audita o diretório atual
/refactor-arch ../reports/audit-project-1.md    # idem, definindo onde salvar o relatório
```

O diretório de trabalho atual é o projeto auditado. Se `$ARGUMENTS` contiver um
caminho terminado em `.md`, ele é o destino do relatório da Fase 2; caso contrário
use o destino padrão descrito na Fase 2. Nenhum outro argumento é necessário — a
skill descobre a stack sozinha.

## Arquivos de referência

Carregue cada um no início da fase correspondente — não tente trabalhar de memória:

| Arquivo | Quando ler | Conteúdo |
|---|---|---|
| `project-analysis.md` | Fase 1 | Heurísticas de detecção de linguagem, framework, banco e mapeamento de arquitetura |
| `anti-patterns.md` | Fase 2 | Catálogo de 14 anti-patterns com sinais de detecção e severidade |
| `report-template.md` | Fase 2 | Formato exato do relatório de auditoria |
| `architecture-guidelines.md` | Fase 3 | Regras do MVC alvo e responsabilidade de cada camada |
| `refactoring-playbook.md` | Fase 3 | 14 padrões de transformação com código antes/depois |

---

## FASE 1 — ANÁLISE

**Objetivo:** entender o que é o projeto antes de julgá-lo. Read-only.

Leia `project-analysis.md` e siga as heurísticas de detecção. Em resumo:

1. **Detectar a stack** pelos arquivos de manifesto (`requirements.txt`,
   `package.json`, `go.mod`, `composer.json`, `pom.xml`, `Gemfile`). O manifesto é
   a fonte da verdade sobre framework e versões — não deduza pelo nome das pastas.
2. **Inventariar os fontes**: liste os arquivos de código, conte linhas, identifique
   os maiores. Ignore `node_modules/`, `venv/`, `.git/`, `dist/`, `__pycache__/` e a
   própria pasta `.claude/`. O número de arquivos impresso no resumo tem de bater com
   essa listagem — ele é conferido depois.
3. **Detectar a persistência**: driver de banco no manifesto, string de conexão,
   `CREATE TABLE`, definições de modelo/ORM. Extraia os nomes das tabelas.
4. **Inferir o domínio** pelos nomes de tabelas, rotas e entidades — descreva o que
   a aplicação faz em linguagem de negócio, não em termos técnicos.
5. **Mapear a arquitetura atual**: existe separação de camadas? Onde moram as rotas,
   as queries, as regras de negócio? Classifique conforme a escala em
   `project-analysis.md` (Monolítica / Parcialmente estruturada / Estruturada).

**Leia os arquivos de verdade.** Para projetos pequenos (até ~1500 linhas), leia
todos os fontes integralmente — é o que permite citar linhas exatas depois. Em
projetos maiores, leia integralmente os arquivos de rotas, models e configuração, e
amostre o restante.

Ao final, imprima **exatamente** neste formato:

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <linguagem + versão se detectável>
Framework:     <framework + versão do manifesto>
Dependencies:  <libs relevantes, separadas por vírgula>
Domain:        <descrição do domínio em linguagem de negócio>
Architecture:  <classificação + uma frase justificando>
Source files:  <N> files analyzed (<M> lines)
DB tables:     <tabelas detectadas, ou "nenhuma detectada">
================================
```

Depois siga direto para a Fase 2, sem pedir confirmação (nada foi alterado ainda).

---

## FASE 2 — AUDITORIA

**Objetivo:** produzir um relatório acionável de todos os problemas. Read-only.

1. Leia `anti-patterns.md` integralmente.
2. Para **cada** anti-pattern do catálogo, aplique os sinais de detecção ao código
   já lido. Use `grep`/`rg` para os sinais mecânicos (concatenação em SQL, segredos
   hardcoded, APIs deprecated) e leitura dirigida para os estruturais (God Class,
   regra de negócio no controller).
3. **Confirme cada suspeita abrindo o arquivo na linha apontada.** Um grep que casa
   não é um achado; o trecho lido é. Isso elimina falso positivo — por exemplo, uma
   string SQL com `+` dentro de um comentário, ou um "segredo" que é um placeholder
   de exemplo.
4. **Registre a ausência também.** Verificar que *não existe* camada de autenticação
   (grep por middleware/decorator/sessão retornando zero) é um achado forte, e a
   ausência precisa ser comprovada por busca, não presumida.
5. Classifique cada achado pela escala de severidade (definida em `anti-patterns.md`):
   - **CRITICAL** — segurança comprometida ou violação total de separação de responsabilidades
   - **HIGH** — forte violação de MVC/SOLID que impede teste e manutenção
   - **MEDIUM** — duplicação, performance moderada, validação ausente
   - **LOW** — legibilidade, nomenclatura, magic numbers
6. Gere o relatório seguindo **exatamente** `report-template.md`, com os achados
   ordenados de CRITICAL para LOW.
7. Salve o relatório (o mesmo texto impresso no terminal) em:
   - o caminho `.md` recebido em `$ARGUMENTS`, se houver; senão
   - `reports/audit-<nome-do-projeto>.md` na **raiz do repositório git** que contém
     o projeto (`git rev-parse --show-toplevel`); fora de um repositório git, na raiz
     do próprio projeto.

   Crie `reports/` se necessário. Gravar o relatório é a **única** escrita permitida
   antes da confirmação — ele é um artefato novo, fora do código auditado.

**Meta de qualidade:** mínimo de 5 achados em qualquer projeto real. Se encontrou
menos, você não procurou o suficiente — releia o catálogo, inclusive as categorias
MEDIUM e LOW, que são as mais fáceis de deixar passar em projetos que "parecem
organizados". Um projeto com camadas já separadas ainda costuma ter N+1, validação
duplicada, tratamento de erro engolido e APIs deprecated.

### Ponto de parada obrigatório

Imprima o relatório e **pare**. Pergunte, literalmente:

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

Então **aguarde a resposta do usuário**. Não prossiga por iniciativa própria, não
interprete silêncio como aprovação e não comece a "preparar" arquivos enquanto
espera. Só um "y"/"sim"/equivalente explícito do usuário libera a Fase 3. Se a
resposta for "n", encerre informando onde o relatório foi salvo — ele tem valor
por si só.

---

## FASE 3 — REFATORAÇÃO

**Objetivo:** reestruturar para MVC corrigindo os achados, e provar que funciona.

Só entre aqui após o "y" explícito.

### 3.1 Preparação

1. Leia `architecture-guidelines.md` (estrutura alvo) e `refactoring-playbook.md`
   (como transformar cada anti-pattern).
2. **Capture o comportamento atual antes de mexer.** Liste todas as rotas existentes
   (método + caminho) a partir do código. Essa lista é o contrato que a validação
   final vai verificar.
3. Se a aplicação puder ser executada, suba-a e registre a resposta dos endpoints
   principais **antes** da refatoração. Comparar antes/depois é a única forma
   honesta de afirmar que nada quebrou.

### 3.2 Execução

Refatore na ordem de risco crescente, validando a cada etapa:

1. **Config primeiro** — extraia segredos e constantes para um módulo de
   configuração lendo variáveis de ambiente. Crie `.env.example` (sem valores
   reais). Isso resolve os CRITICAL de credencial sem mexer em lógica.
2. **Camada de dados** — crie os Models, um por entidade do domínio, com as queries
   parametrizadas. Elimine concatenação de SQL aqui.
3. **Camada de serviço/controller** — mova regra de negócio para fora das rotas.
   Controllers orquestram; não montam SQL nem formatam HTML.
4. **Rotas/Views** — deixe apenas o mapeamento HTTP, delegando aos controllers.
5. **Error handling centralizado** — um handler único no lugar dos `try/except`
   genéricos espalhados.
6. **Entry point** — reduza a um composition root: cria config, instancia
   dependências, registra rotas, sobe o servidor.

**Adapte ao ponto de partida detectado na Fase 1:**

- **Monolítica** — crie as camadas do zero a partir de `architecture-guidelines.md`.
- **Parcialmente estruturada** — não recrie o que já funciona. Mantenha as pastas
  existentes que já respeitam sua responsabilidade (ex.: `models/` com o ORM), extraia
  o que vaza (regra de negócio da rota → controller; acesso a dados → repository/model),
  passe a *usar* o que existe e está morto (métodos de model, serviços, constantes) e
  remova o que for código morto.
- **Estruturada** — limite-se aos achados pontuais do relatório.

Regras durante a execução:

- **Preserve os contratos HTTP.** Mesmos caminhos, métodos, formato de resposta e
  status codes. Exceção legítima: remover um endpoint que é uma falha de segurança
  (ex.: executor de SQL arbitrário sem autenticação) ou parar de vazar um campo
  sensível numa resposta. Ambos são correções exigidas pela auditoria — anuncie-os
  explicitamente no relatório final como mudanças intencionais de contrato.
- **Um anti-pattern por vez.** Não misture a extração de config com a reescrita das
  queries no mesmo passo; fica impossível saber o que quebrou.
- **Arquivos antigos são removidos**, não deixados órfãos ao lado dos novos. Duas
  versões do mesmo código é pior que o problema original.

### 3.3 Validação obrigatória

A fase não termina sem isto. Execute de verdade:

1. **Boot** — suba a aplicação e confirme que inicia sem exceção. Se houver
   dependências faltando, instale no ambiente isolado do projeto (`./venv` para
   Python, `npm install` local para Node) — nunca no sistema global.
2. **Endpoints** — chame cada rota da lista capturada em 3.1 (curl ou equivalente) e
   confirme que responde com status coerente. Compare com o comportamento anterior.
3. **Regressão dos achados** — rode novamente os greps de detecção da Fase 2 e
   confirme que os sinais sumiram.
4. **Autorização** — para cada rota protegida, confirme 401 sem token e 403 com
   um usuário que não é dono do recurso nem admin — **incluindo as de leitura**
   (listagens, buscas e estatísticas devolvem só o escopo do ator) — e que nenhuma
   conta privilegiada do seed tem senha conhecida em produção. Se o projeto tiver suíte de
   testes, escreva esses casos nela e rode a suíte.
5. **Concorrência mínima** — se a refatoração introduziu transação, pool ou troca de
   conexão, dispare ~8 requisições de escrita em paralelo (`curl ... &` + `wait`) e
   confirme que todas respondem com sucesso. Transação explícita sobre uma conexão
   única compartilhada (`BEGIN` aninhado) é a regressão típica deste passo.
6. **Encerre o processo** que você subiu.

Se qualquer passo falhar, **corrija antes de declarar conclusão**. Se algo não pôde
ser validado por limitação do ambiente, diga explicitamente o que ficou pendente e
por quê — jamais reporte sucesso presumido.

Imprima o resultado final:

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
<árvore de diretórios resultante>

## Findings Resolved
CRITICAL: <n>/<total> | HIGH: <n>/<total> | MEDIUM: <n>/<total> | LOW: <n>/<total>

## Contract Changes
<mudanças intencionais de contrato, ou "nenhuma">

## Validation
  [ok|falhou] Application boots without errors
  [ok|falhou] All endpoints respond correctly (<n>/<total> rotas verificadas)
  [ok|falhou] Anti-pattern signals no longer present

## Pending
<o que não pôde ser validado e por quê, ou "nada pendente">
================================
```
