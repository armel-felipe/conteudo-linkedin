# Pipeline de Conteúdo LinkedIn — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir o pipeline agentico manual de conteúdo LinkedIn (configs, memória do autor, mapa de skills, AGENTS.md e 7 skills do pipeline) conforme o design aprovado em `docs/superpowers/specs/2026-08-31-pipeline-conteudo-linkedin-design.md`.

**Architecture:** Entregáveis são arquivos Markdown/YAML (configs, memória, skills). Cada skill é um `SKILL.md` self-contained em `.agents/skills/<nome>/`. O fluxo é manual: cada etapa gera um artefato persistente. Nenhum código Python, nenhuma automação.

**Tech Stack:** Markdown, YAML, skills OpenCode (frontmatter `name` + `description`), verificação via grep/python3.

## Global Constraints

- Nada do histórico git anterior é aproveitado (recomeço).
- Skills existentes em `.agents/skills/` são MANTIDAS: `last30days`, `publicar-linkedin`, `visao-nativa-primeiro`, `orquestrador-runtime` (legado, fora do fluxo).
- Skills novas do pipeline vão em `.agents/skills/<nome>/SKILL.md`.
- Frontmatter de skill: `name` (letras/números/hífens) e `description` começando com "Use quando..." (gatilho, sem resumo do workflow).
- Posts: 900–1500 caracteres / 150–250 palavras; esqueleto ABERTURA→SITUAÇÃO→APLICAÇÃO→PROBLEMA→DECISÃO→APRENDIZADO→PERGUNTA.
- Revisão obrigatória de todo post com a skill `escrita-humana` (global em `~/.agents/skills/escrita-humana/`).
- Frentes (prioridade): IA Aplicada 10, Logística/last mile/CX 9, Liderança em operações 8, Riscos/compliance/resiliência 8, Alimentos/consumo/sustentabilidade 4.
- Fórmula de score: freshness .15, relevance .20, debate .15, evidence .10, author_fit .20, originality .10, linkedin_fit .10 → 0-100.
- Estados de conteúdo: discovered → clustered → candidate → ready_for_research → researched → drafted → approved → published → archived.
- `.env` NUNCA vai para o git (já no .gitignore).

---

### Task 1: Estrutura de diretórios + README + roadmap

**Files:**
- Create: `README.md`, `docs/roadmap.md`
- Create (dirs): `config/`, `research/signals/`, `research/topics/`, `research/briefs/`, `content/drafts/`, `content/approved/`, `content/published/`, `memory/`, `docs/superpowers/plans/`

**Interfaces:**
- Produces: estrutura de pastas que todas as tasks seguintes usam; `docs/roadmap.md` que registra itens futuros.

- [ ] **Step 1: Criar diretórios**

```bash
mkdir -p config research/signals research/topics research/briefs content/drafts content/approved content/published memory docs/superpowers/plans
```

- [ ] **Step 2: Criar `README.md`**

```markdown
# Conteúdo LinkedIn — Pipeline de Inteligência de Conteúdo

Pipeline agentico manual que transforma pesquisa em posts profissionais para LinkedIn.

Fluxo: frentes → sinais → debates → temas → oportunidades → tese → evidências → contexto do autor → post.

## Estrutura

- `config/` — frentes, fontes, autores, scoring
- `research/` — signals, topics, briefs
- `content/` — backlog, drafts, approved, published
- `memory/` — experiência profissional, opiniões, estilo de escrita
- `.agents/skills/` — skills do pipeline (ver `mapa.md`)

## Uso

1. `discover-signals` (diário) → 20-50 sinais
2. `cluster-signals` + `score-opportunities` (2x/semana) → 5-10 oportunidades
3. `research-topic` → `write-post` → `critique-post` → `escrita-humana` → aprovação → `publicar-linkedin`

Ver `mapa.md` para o guia de skills e `AGENTS.md` para o contrato de operação.
```

- [ ] **Step 3: Criar `docs/roadmap.md`**

```markdown
# Roadmap

Ações futuras com status `[ ]` pendente / `[x]` feito.

- [ ] Configurar X na last30days (cookies do browser — grátis)
- [ ] Adicionar web key (Brave grátis) para elevar qualidade de imprensa/relatórios
- [ ] Scripts Python (scoring, cluster) quando o fluxo manual estabilizar
- [ ] Logs de execução
- [ ] Automação recorrente (Fase 6 da spec)
- [ ] Ajuste periódico das frentes conforme métricas de engajamento/posicionamento
```

- [ ] **Step 4: Verificar**

```bash
ls config research/signals research/topics research/briefs content/drafts content/approved content/published memory docs
grep -c "^- \[ \]" docs/roadmap.md
```

Expected: diretórios existem; roadmap tem 6 itens pendentes.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/roadmap.md
git commit -m "chore: estrutura base do pipeline + roadmap"
```

---

### Task 2: Configs (frentes, sources, authors, scoring)

**Files:**
- Create: `config/frentes.yaml`, `config/sources.yaml`, `config/authors.yaml`, `config/scoring.yaml`

**Interfaces:**
- Produces: `config/frentes.yaml` (consumido por `discover-signals`), `config/scoring.yaml` (consumido por `score-opportunities`), `config/authors.yaml` (consumido por `discover-signals`/`research-topic`).

- [ ] **Step 1: Criar `config/frentes.yaml`**

```yaml
frentes:

  ia_aplicada:
    name: IA Aplicada
    priority: 10
    keywords:
      - AI in supply chain use cases
      - AI logistics forecasting routing
      - AI operations productivity
      - AI customer service operations
      - generative AI supply chain examples
      - AI decision making operations
      - human in the loop AI operations
      - AI data quality supply chain
      - AI automation failure operations
      - AI adoption barriers enterprise
    research_questions:
      - "Quem está usando IA em produção, e para quê?"
      - "Que ganhos estão sendo relatados: tempo, custo, qualidade ou receita?"
      - "Quais aplicações falharam?"
      - "Onde a decisão humana continua indispensável?"
      - "Quais competências os líderes precisam desenvolver?"
      - "O debate está falando de automação ou de aumento da capacidade das equipes?"
      - "Quais casos são reais e quais são apenas marketing?"

  logistica_last_mile_cx:
    name: Logística, last mile e experiência do cliente
    priority: 9
    keywords:
      - last mile delivery customer experience
      - delivery speed cost tradeoff
      - logistics operational efficiency
      - food delivery operations
      - delivery reliability customer complaints

  lideranca_operacoes:
    name: Liderança em operações
    priority: 8
    keywords:
      - operations leadership challenges
      - delegation and accountability leadership
      - building trust in operational teams
      - frontline workforce productivity
      - decision making under pressure leadership

  riscos_compliance_resiliencia:
    name: Riscos, compliance e resiliência
    priority: 8
    keywords:
      - supply chain risk management
      - operational resilience
      - AI governance compliance business
      - food safety supply chain
      - supplier risk technology

  alimentos_consumo_sustentabilidade:
    name: Alimentos, consumo e sustentabilidade
    priority: 4
    keywords:
      - food industry trends
      - functional foods market
      - food supply chain innovation
      - circular economy operations
      - sustainable logistics cost
```

- [ ] **Step 2: Criar `config/sources.yaml`**

```yaml
sources:

  reddit:
    enabled: true
    weight: 8

  hacker_news:
    enabled: true
    weight: 6

  news:
    enabled: true
    weight: 9

  reports:
    enabled: true
    weight: 10

  company_blogs:
    enabled: true
    weight: 7

  linkedin_public:
    enabled: true
    weight: 7

  google_search:
    enabled: true
    weight: 8
```

- [ ] **Step 3: Criar `config/authors.yaml`**

```yaml
authors:

  ia_aplicada:
    - name: ""
      linkedin: ""
      notes: ""

  logistica_last_mile_cx:
    - name: ""
      linkedin: ""
      notes: ""

  lideranca_operacoes:
    - name: ""
      linkedin: ""
      notes: ""

  riscos_compliance_resiliencia:
    - name: ""
      linkedin: ""
      notes: ""

  alimentos_consumo_sustentabilidade:
    - name: ""
      linkedin: ""
      notes: ""
```

Meta: 20 a 40 autores no total. Qualidade, não volume.

- [ ] **Step 4: Criar `config/scoring.yaml`**

```yaml
weights:
  freshness: 0.15
  relevance: 0.20
  debate: 0.15
  evidence: 0.10
  author_fit: 0.20
  originality: 0.10
  linkedin_fit: 0.10

scale: 0-100
```

- [ ] **Step 5: Verificar YAML válido**

```bash
python3 -c "import yaml,glob; [yaml.safe_load(open(f)) for f in glob.glob('config/*.yaml')]; print('OK')"
```

Expected: `OK` (todos os YAML parseiam).

- [ ] **Step 6: Commit**

```bash
git add config/
git commit -m "feat: configs do pipeline (frentes, sources, authors, scoring)"
```

---

### Task 3: Memória do autor (3 arquivos)

**Files:**
- Create: `memory/professional_experience.md`, `memory/opinions.md`, `memory/writing_style.md`

**Interfaces:**
- Produces: arquivos consumidos por `write-post` (entrada obrigatória) e `research-topic` (conexão com experiência).

- [ ] **Step 1: Criar `memory/professional_experience.md`**

Conteúdo inicial (rascunho para revisão do autor — o autor deve corrigir/expandir):

```markdown
# Experiência profissional

Fatos profissionais relevantes que podem ser usados nos textos. Apenas fatos — sem opinião (opiniões vão em opinions.md).

## Operações e food delivery

- Experiência em gestão de operações no setor de food delivery.
- Atuação com atendimento ao cliente, SLA e FCR (First Contact Resolution).
- Vivência com operações de entrega: prazo, custo, confiabilidade, rastreabilidade.
- Decisões operacionais envolvendo produtividade, processos e tecnologia.

## Automação e dados

- Uso de automação para reduzir o tempo entre problema e decisão.
- Experiência com dados operacionais: identificar desvios, padronizar informações, definir prioridades.
- Aprendizado: IA não corrige operação desorganizada; acelera o que já existe, inclusive erros.

## Gestão de equipes

- Gestão de equipes operacionais e tomada de decisão sob pressão.

> **Nota:** este arquivo é um rascunho inicial. O autor deve revisar, corrigir e expandir com fatos reais.
```

- [ ] **Step 2: Criar `memory/opinions.md`**

```markdown
# Banco de opiniões

Opiniões do autor sobre temas recorrentes. Evolui conforme novos posts são produzidos.

## Automação

- Automação não deve ser usada apenas para reduzir headcount.
- IA não corrige uma operação desorganizada — ela acelera o que já existe, inclusive os erros.

## Métricas

- Uma boa métrica precisa induzir o comportamento correto.
- Medir automação por deflection quando o objetivo é resolução é medir pela métrica errada.

## Inteligência Artificial

- IA aplicada em processo ruim tende a amplificar problemas existentes.
- O valor da IA está em reduzir o tempo entre um problema e uma decisão.

> **Nota:** rascunho inicial. O autor deve revisar e ajustar para refletir suas opiniões reais.
```

- [ ] **Step 3: Criar `memory/writing_style.md`**

```markdown
# Perfil de escrita

Regras de escrita do autor para posts no LinkedIn.

## Formato

- Tamanho: 900–1500 caracteres / 150–250 palavras.
- Formato: texto + imagem (anexo manual na publicação).

## Esqueleto obrigatório

1. ABERTURA — frase forte e específica (nunca genérica).
2. SITUAÇÃO — contexto real, concreto.
3. APLICAÇÃO — ferramenta/aplicação específica.
4. PROBLEMA — o que deu errado / o limite encontrado.
5. DECISÃO — o que foi feito (com critério).
6. APRENDIZADO — o insight operacional.
7. PERGUNTA — fechamento que convida à conversa.

## Critérios de qualidade

- Experiência concreta > conceito.
- Liderança parte de tensão prática, não de frase motivacional.
- Casos de empresas e movimentos de mercado têm alto potencial.
- Abertura sempre com frase forte e específica.
- Densidade: uma ideia por post.

## O que evitar

- Frases genéricas de IA: "Em um mundo cada vez mais...", "A inteligência artificial veio para...", "Mais do que nunca...", "Não é sobre X, é sobre Y...".
- Posts conceituais sem experiência concreta.
- Posts longos sem promessa explícita.

## Revisão

Todo post passa pela skill `escrita-humana` antes da aprovação.
```

- [ ] **Step 4: Verificar**

```bash
ls memory/
grep -c "ABERTURA" memory/writing_style.md
```

Expected: 3 arquivos; `ABERTURA` presente.

- [ ] **Step 5: Commit**

```bash
git add memory/
git commit -m "feat: memória do autor (experiência, opiniões, estilo de escrita)"
```

---

### Task 4: mapa.md — guia de skills

**Files:**
- Create: `mapa.md`

**Interfaces:**
- Produces: `mapa.md`, referenciado por `AGENTS.md` (Task 5). Lista TODAS as skills do projeto (novas + mantidas), com objetivo, vínculo com o projeto e como invocar.

- [ ] **Step 1: Criar `mapa.md`**

```markdown
# Mapa de Skills

Guia de todas as skills do projeto: objetivo, vínculo com o pipeline e como invocar.
Referenciado pelo `AGENTS.md`.

## Skills do pipeline (novas)

| Skill | Objetivo | Vínculo | Invocação |
|---|---|---|---|
| `discover-signals` | Encontrar sinais relevantes por frente (20-50/dia) | Etapa 1 do fluxo | "roda discover-signals" |
| `analyze-discussions` | Analisar o debate de um signal (opcional) | Etapa 1.5, sob demanda | "analisa o debate do signal X" |
| `cluster-signals` | Agrupar signals em temas | Etapa 2 (2x/semana) | "roda cluster-signals" |
| `score-opportunities` | Pontuar temas (0-100) e gerar backlog | Etapa 3 (2x/semana) | "roda score-opportunities" |
| `research-topic` | Pesquisa aprofundada → brief | Etapa 4 (ao publicar) | "pesquisa o topic X" |
| `write-post` | Escrever post a partir do brief + memória | Etapa 5 (ao publicar) | "escreve o post do topic X" |
| `critique-post` | Criticar o draft antes da aprovação | Etapa 6 (ao publicar) | "critica o draft X" |

## Skills mantidas (existentes)

| Skill | Objetivo | Vínculo | Invocação |
|---|---|---|---|
| `last30days` | Pesquisar o que se discute nos últimos 30 dias (Reddit, HN, YouTube, etc.) | Ferramenta primária de pesquisa do `discover-signals` | "pesquisa last30days sobre X" |
| `publicar-linkedin` | Publicar/agendar conteúdo aprovado no LinkedIn via browser logado | Etapa final (publicação) | "publica content/approved/X.md amanhã às 9h" |
| `visao-nativa-primeiro` | Política visual: visão nativa antes do fallback ao image-analyzer | Transversal (tarefas visuais) | Seguir sempre em tarefas visuais |
| `escrita-humana` | Editar rascunhos para ficarem mais humanos, preservando a voz | Revisão obrigatória de todo post | "revisa com escrita-humana" |
| `orquestrador-runtime` | Orquestrador do pipeline editorial antigo | LEGADO — fora do fluxo novo | Não invocar |

## Notas

- `escrita-humana` é skill global do usuário (`~/.agents/skills/escrita-humana/`), não do projeto.
- `orquestrador-runtime` foi mantida na pasta, mas o fluxo novo é manual (sem orquestrador).
```

- [ ] **Step 2: Verificar**

```bash
grep -c "| \`" mapa.md
```

Expected: 12 skills listadas (7 pipeline + 5 mantidas).

- [ ] **Step 3: Commit**

```bash
git add mapa.md
git commit -m "docs: mapa de skills do projeto"
```

---

### Task 5: AGENTS.md — contrato de operação

**Files:**
- Create: `AGENTS.md`

**Interfaces:**
- Produces: contrato que todo agente segue; referencia `mapa.md`.

- [ ] **Step 1: Criar `AGENTS.md`**

```markdown
# AGENTS.md — Contrato de Operação

## Projeto

Pipeline agentico manual de conteúdo para LinkedIn. Fluxo: frentes → sinais → debates → temas → oportunidades → tese → evidências → contexto do autor → post.

## Regras centrais

1. **Nunca começar por "sobre o que escrever?"** — começar por "o que está acontecendo?" e "onde existe debate?".
2. **Cada etapa gera um artefato persistente** (signals, topics, backlog, brief, draft). Nada depende só do contexto de conversa.
3. **Pesquisa separada de redação**: quem pesquisa não escreve; quem escreve recebe briefing estruturado e NÃO pesquisa.
4. **LinkedIn é fonte complementar**, não principal.
5. **Posts**: 900–1500 caracteres / 150–250 palavras; esqueleto ABERTURA→SITUAÇÃO→APLICAÇÃO→PROBLEMA→DECISÃO→APRENDIZADO→PERGUNTA.
6. **Todo post passa por `escrita-humana`** antes da aprovação.
7. **Nunca inventar dados** — todo fato do post tem origem no brief, com fonte/URL/data.

## Skills

Ver `mapa.md` — guia de todas as skills (objetivo, vínculo, invocação).

## Estrutura

- `config/` — frentes, sources, authors, scoring
- `research/signals/`, `research/topics/`, `research/briefs/` — artefatos de pesquisa
- `content/` — backlog, drafts, approved, published
- `memory/` — experiência, opiniões, estilo de escrita

## Segurança

- `.env` nunca vai para o git; credenciais nunca em chat, arquivos ou commits.
- Publicação usa apenas a sessão logada do browser do OpenWork (sem credenciais).

## Estados de conteúdo

discovered → clustered → candidate → ready_for_research → researched → drafted → approved → published → archived
```

- [ ] **Step 2: Verificar**

```bash
grep -c "mapa.md" AGENTS.md
```

Expected: pelo menos 1 referência a `mapa.md`.

- [ ] **Step 3: Commit**

```bash
git add AGENTS.md
git commit -m "docs: contrato de operação (AGENTS.md)"
```

---

### Task 6: Skill `discover-signals`

**Files:**
- Create: `.agents/skills/discover-signals/SKILL.md`

**Interfaces:**
- Consumes: `config/frentes.yaml`, `config/sources.yaml`, `config/authors.yaml`, skill `last30days`.
- Produces: `research/signals/signals_YYYY-MM-DD.yaml` (20-50 signals no formato da spec §8).

- [ ] **Step 1: Escrever o SKILL.md**

Criar `.agents/skills/discover-signals/SKILL.md` com:

```markdown
---
name: discover-signals
description: Use quando for preciso encontrar sinais relevantes para o pipeline de conteúdo LinkedIn (descoberta diária de 20-50 sinais por frente).
---

# Discover Signals

## Overview

Encontrar acontecimentos, discussões e ideias relacionadas às frentes do projeto, respondendo: "Sobre o que profissionais inteligentes estão discutindo, discordando ou mudando de opinião?" — NÃO "o que está trending?".

## Quando Usar / Quando NÃO Usar

- Usar: descoberta diária de sinais; antes de cluster-signals.
- NÃO usar: criar posts; definir opinião final; inventar dados; resumir apenas notícias populares.

## Entrada

- `config/frentes.yaml` (frentes, prioridades, keywords, research_questions)
- Skill `last30days` (ferramenta primária de pesquisa)
- Busca web manual (webfetch) para imprensa/relatórios quando necessário

## Fluxo

1. Ler `config/frentes.yaml`.
2. Para cada frente (por prioridade), rodar `last30days` com as keywords da frente (uma rodada por frente ou por keyword-chave).
3. Complementar com busca web manual (webfetch) quando a frente exigir imprensa/relatórios (ex.: riscos/compliance, alimentos/sustentabilidade).
4. Para a frente IA Aplicada, aplicar as 7 perguntas de pesquisa (research_questions) ao avaliar cada candidato a signal.
5. Converter cada descoberta relevante em um Signal no formato abaixo.
6. Salvar em `research/signals/signals_YYYY-MM-DD.yaml` (data de hoje).

## Formato do Signal (YAML)

```yaml
id: signal_YYYYMMDD_NNN
title: "Título curto e específico"
pillar:
  - ia_aplicada
source:
  type: article | reddit | hn | youtube | report | linkedin | web
  publisher: Nome
  url: https://...
  published_at: YYYY-MM-DD
observation: "O que foi observado, em uma frase."
debate:
  side_a: "Posição A"
  side_b: "Posição B"
evidence:
  - "Evidência 1 (com fonte)"
  - "Evidência 2 (com fonte)"
possible_angle: "Ângulo possível para o autor"
author_connection: "Conexão com a experiência do autor (memory/professional_experience.md)"
scores:
  freshness: 0-10
  relevance: 0-10
  debate: 0-10
  evidence: 0-10
  author_fit: 0-10
created_at: YYYY-MM-DD
```

## Regras

- 20-50 signals por execução.
- NÃO inventar dados: todo signal tem fonte com URL.
- NÃO escrever posts nem definir opinião final.
- Sinais devem incluir: acontecimentos recentes, discussões com opiniões divergentes, mudanças de comportamento, novas tecnologias, pesquisas recentes, decisões controversas, cases, falhas, aprendizados, novas práticas.
- Para IA Aplicada: distinguir aplicações em produção, pilotos, promessas sem comprovação, resultados mensuráveis e problemas de implantação.
- Usar `pillar` com o nome da frente (chave do YAML de frentes).

## Erros comuns

- Confundir trending com debate real.
- Inventar evidências sem fonte.
- Escrever opinião final do autor no signal.
- Ignorar as 7 perguntas de IA na frente ia_aplicada.
```

- [ ] **Step 2: Verificar frontmatter e seções**

```bash
python3 -c "import yaml; d=yaml.safe_load(open('.agents/skills/discover-signals/SKILL.md').read().split('---')[1]); assert d['name']=='discover-signals'; assert d['description'].startswith('Use quando'); print('OK')"
grep -c "^## " .agents/skills/discover-signals/SKILL.md
```

Expected: `OK`; pelo menos 6 seções (`## `).

- [ ] **Step 3: Commit**

```bash
git add .agents/skills/discover-signals/
git commit -m "feat: skill discover-signals"
```

---

### Task 7: Skill `analyze-discussions`

**Files:**
- Create: `.agents/skills/analyze-discussions/SKILL.md`

**Interfaces:**
- Consumes: 1 Signal (de `research/signals/`).
- Produces: análise do debate (pode ser anexada ao signal ou salva em `research/signals/` como bloco `discussion:`).

- [ ] **Step 1: Escrever o SKILL.md**

```markdown
---
name: analyze-discussions
description: Use quando um signal do pipeline de conteúdo LinkedIn merecer aprofundamento do debate antes de virar tema (etapa opcional entre discover-signals e cluster-signals).
---

# Analyze Discussions

## Overview

Aprofundar o debate de um Signal: mapear a pergunta central, as posições em conflito, o desacordo real e a oportunidade de conteúdo.

## Quando Usar / Quando NÃO Usar

- Usar: quando um signal tem debate rico e merece análise antes da clusterização; sob demanda.
- NÃO usar: para todo signal (a maioria já nasce com debate suficiente no discover-signals).

## Entrada

- 1 Signal (id, observation, debate, evidence, possible_angle)

## Saída (bloco `discussion:` anexado ao signal)

```yaml
discussion:
  question: "Qual é a pergunta central do debate?"
  position_a: "Posição A"
  position_b: "Posição B"
  disagreement: "Onde está o conflito real (ex.: custo vs qualidade)?"
  unanswered_question: "Pergunta que ninguém respondeu bem ainda?"
  content_opportunity: "Oportunidade de conteúdo para o autor"
```

## Fluxo

1. Ler o signal.
2. Identificar a pergunta central do debate.
3. Mapear as posições em conflito (A e B) — sem tomar partido.
4. Identificar o desacordo real (o que está em jogo).
5. Identificar a pergunta em aberto (o que ninguém respondeu bem).
6. Avaliar a oportunidade de conteúdo para o autor (usando memory/professional_experience.md e opinions.md).
7. Anexar o bloco `discussion:` ao signal no arquivo YAML.

## Regras

- Não tomar partido na análise — mapear o debate, não vencê-lo.
- A oportunidade de conteúdo deve conectar com a experiência/opinião do autor.
- Se o signal não tiver debate real, dizer isso em vez de forçar um.
```

- [ ] **Step 2: Verificar**

```bash
python3 -c "import yaml; d=yaml.safe_load(open('.agents/skills/analyze-discussions/SKILL.md').read().split('---')[1]); assert d['name']=='analyze-discussions'; print('OK')"
```

Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add .agents/skills/analyze-discussions/
git commit -m "feat: skill analyze-discussions"
```

---

### Task 8: Skill `cluster-signals`

**Files:**
- Create: `.agents/skills/cluster-signals/SKILL.md`

**Interfaces:**
- Consumes: `research/signals/signals_*.yaml`.
- Produces: `research/topics/topics_YYYY-MM-DD.yaml` (formato da spec §13).

- [ ] **Step 1: Escrever o SKILL.md**

```markdown
---
name: cluster-signals
description: Use quando houver signals coletados que precisem ser agrupados em temas (etapa 2x/semana do pipeline de conteúdo LinkedIn).
---

# Cluster Signals

## Overview

Agrupar Signals que tratam do mesmo fenômeno em Topics, cada um com pergunta central e tese possível.

## Quando Usar / Quando NÃO Usar

- Usar: 2x/semana, quando houver signals acumulados.
- NÃO usar: com poucos signals (menos de ~10) — aguardar acúmulo.

## Entrada

- `research/signals/signals_*.yaml` (todos os signals não clusterizados)

## Saída

`research/topics/topics_YYYY-MM-DD.yaml`:

```yaml
topics:
  - id: topic_YYYYMMDD_01
    title: "Título do tema"
    pillars:
      - ia_aplicada
    signals:
      - signal_YYYYMMDD_001
      - signal_YYYYMMDD_002
    central_question: "Pergunta central do tema"
    possible_thesis: "Tese possível"
    author_connection: strong | medium | weak
    status: candidate
```

## Fluxo

1. Ler todos os signals.
2. Agrupar por fenômeno comum (mesmo assunto, mesmo debate, mesma mudança).
3. Para cada grupo, formular: título, pergunta central, tese possível.
4. Avaliar a conexão com o autor (strong/medium/weak) usando memory/.
5. Salvar em `research/topics/topics_YYYY-MM-DD.yaml` com status `candidate`.

## Regras

- Um signal pode aparecer em no máximo 1 topic.
- Sinais que não formam grupo com ninguém ficam de fora (não forçar).
- A tese possível deve ser opinativa, não neutra.
- Não pontuar aqui — scoring é do score-opportunities.
```

- [ ] **Step 2: Verificar**

```bash
python3 -c "import yaml; d=yaml.safe_load(open('.agents/skills/cluster-signals/SKILL.md').read().split('---')[1]); assert d['name']=='cluster-signals'; print('OK')"
```

Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add .agents/skills/cluster-signals/
git commit -m "feat: skill cluster-signals"
```

---

### Task 9: Skill `score-opportunities`

**Files:**
- Create: `.agents/skills/score-opportunities/SKILL.md`

**Interfaces:**
- Consumes: `research/topics/topics_*.yaml`, `config/scoring.yaml`.
- Produces: `content/backlog.md` (oportunidades ranqueadas, formato da spec §15).

- [ ] **Step 1: Escrever o SKILL.md**

```markdown
---
name: score-opportunities
description: Use quando houver topics candidatos que precisem ser pontuados e ranqueados no backlog (etapa 2x/semana do pipeline de conteúdo LinkedIn).
---

# Score Opportunities

## Overview

Pontuar cada Topic candidato (0-10 por critério) e gerar o backlog ranqueado de oportunidades de conteúdo.

## Quando Usar / Quando NÃO Usar

- Usar: 2x/semana, após cluster-signals.
- NÃO usar: para pontuar signals individuais (só topics).

## Entrada

- `research/topics/topics_*.yaml`
- `config/scoring.yaml` (pesos)

## Critérios (0-10 cada)

freshness, relevance, debate, evidence, author_fit, originality, linkedin_fit

## Fórmula

score = freshness*0.15 + relevance*0.20 + debate*0.15 + evidence*0.10 + author_fit*0.20 + originality*0.10 + linkedin_fit*0.10 → 0-100

## Saída

`content/backlog.md` (formato da spec §15):

```markdown
# Content Backlog

## 92 — Título do tema

Pilares: IA Aplicada / Logística

Tese: ...

Por que agora: ...

Evidências disponíveis: N

Experiência pessoal relacionada: Alta | Média | Baixa

Status: Ready for research
```

## Fluxo

1. Ler topics e scoring.yaml.
2. Pontuar cada topic nos 7 critérios (0-10).
3. Calcular o score final (fórmula acima).
4. Ordenar por score decrescente.
5. Escrever o backlog com os top 5-10.
6. Atualizar o status do topic para `ready_for_research` quando entrar no backlog.

## Regras

- Pontuar com base nas evidências reais do topic (não no potencial imaginado).
- author_fit alto exige conexão real com memory/professional_experience.md.
- Não inflar notas para "empurrar" um tema favorito.
```

- [ ] **Step 2: Verificar**

```bash
python3 -c "import yaml; d=yaml.safe_load(open('.agents/skills/score-opportunities/SKILL.md').read().split('---')[1]); assert d['name']=='score-opportunities'; print('OK')"
```

Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add .agents/skills/score-opportunities/
git commit -m "feat: skill score-opportunities"
```

---

### Task 10: Skill `research-topic`

**Files:**
- Create: `.agents/skills/research-topic/SKILL.md`

**Interfaces:**
- Consumes: `topic_id` (do backlog), skill `last30days`, busca web manual.
- Produces: `research/briefs/<topic_id>.md` (formato da spec §17).

- [ ] **Step 1: Escrever o SKILL.md**

```markdown
---
name: research-topic
description: Use quando um topic do backlog for escolhido para virar post e precisar de pesquisa aprofundada (gera o research brief).
---

# Research Topic

## Overview

Pesquisa aprofundada de um topic escolhido, produzindo um brief confiável com fatos, números, estudos, opiniões, contrapontos e riscos — tudo rastreável.

## Quando Usar / Quando NÃO Usar

- Usar: apenas quando um topic for escolhido para virar post (status ready_for_research).
- NÃO usar: para descobrir sinais (isso é do discover-signals); para escrever o post (isso é do write-post).

## Entrada

- `topic_id` (ex.: topic_20260831_01)
- O topic correspondente em `research/topics/`
- Os signals do topic em `research/signals/`
- Skill `last30days` + busca web manual (webfetch)

## Saída

`research/briefs/<topic_id>.md` (formato da spec §17):

```markdown
# Research Brief

## Tema
## Pergunta
## Tese potencial
## O que está acontecendo
## Evidências
### Evidência 1
Fonte: | URL: | Data:
Resumo:
### Evidência 2
...
## Argumentos favoráveis
## Argumentos contrários
## Pontos ainda incertos
## Conexão com experiência profissional
## Possíveis ângulos
1. 2. 3.
## Riscos de afirmações não verificadas
```

## Fluxo

1. Ler o topic e seus signals.
2. Re-rodar `last30days` no tema (aprofundado).
3. Abrir as URLs dos signals (webfetch) e extrair fatos/números.
4. Buscar imprensa/relatórios/estudos complementares (webfetch).
5. Para IA Aplicada, aplicar as 7 perguntas de pesquisa.
6. Preencher o brief com TODAS as evidências rastreáveis (fonte, URL, data).
7. Listar argumentos favoráveis e contrários, pontos incertos e riscos.
8. Conectar com memory/professional_experience.md.
9. Salvar em `research/briefs/<topic_id>.md` e atualizar status do topic para `researched`.

## Regras

- NUNCA inventar dados: toda evidência tem fonte/URL/data.
- Separar fato de opinião e de tendência.
- Registrar explicitamente o que NÃO foi verificado (riscos).
- O brief é a ÚNICA fonte de referência do write-post.
```

- [ ] **Step 2: Verificar**

```bash
python3 -c "import yaml; d=yaml.safe_load(open('.agents/skills/research-topic/SKILL.md').read().split('---')[1]); assert d['name']=='research-topic'; print('OK')"
grep -c "Riscos de afirmações" .agents/skills/research-topic/SKILL.md
```

Expected: `OK`; seção de riscos presente.

- [ ] **Step 3: Commit**

```bash
git add .agents/skills/research-topic/
git commit -m "feat: skill research-topic"
```

---

### Task 11: Skill `write-post`

**Files:**
- Create: `.agents/skills/write-post/SKILL.md`

**Interfaces:**
- Consumes: `research/briefs/<topic_id>.md`, `memory/professional_experience.md`, `memory/opinions.md`, `memory/writing_style.md`.
- Produces: `content/drafts/<topic_id>.md`.

- [ ] **Step 1: Escrever o SKILL.md**

```markdown
---
name: write-post
description: Use quando um research brief estiver pronto e for preciso escrever o post do LinkedIn (900-1500 caracteres, esqueleto fixo).
---

# Write Post

## Overview

Escrever o post a partir do brief e da memória do autor. O writer NÃO pesquisa — escreve apenas com o material recebido.

## Quando Usar / Quando NÃO Usar

- Usar: quando o brief existir (status researched).
- NÃO usar: sem brief; para pesquisar (isso é do research-topic).

## Entrada obrigatória

- `research/briefs/<topic_id>.md`
- `memory/professional_experience.md`
- `memory/opinions.md`
- `memory/writing_style.md`

## Saída

`content/drafts/<topic_id>.md` — o post pronto para revisão.

## Regras de escrita

- Tamanho: 900–1500 caracteres / 150–250 palavras.
- Esqueleto obrigatório: ABERTURA → SITUAÇÃO → APLICAÇÃO → PROBLEMA → DECISÃO → APRENDIZADO → PERGUNTA.
- Abertura com frase forte e específica (nunca genérica).
- Experiência concreta > conceito.
- Uma ideia por post.
- Todo fato do post deve ter origem no brief (nunca inventar).
- Usar a voz e opiniões de memory/opinions.md e o estilo de memory/writing_style.md.

## O que evitar

- Frases genéricas de IA: "Em um mundo cada vez mais...", "A inteligência artificial veio para...", "Mais do que nunca...", "Não é sobre X, é sobre Y...".
- Posts conceituais sem experiência concreta.
- Afirmações sem evidência no brief.

## Fluxo

1. Ler o brief e os 3 arquivos de memória.
2. Escolher o ângulo (dos "Possíveis ângulos" do brief) com melhor conexão com a experiência do autor.
3. Escrever o post seguindo o esqueleto e as regras.
4. Verificar tamanho (900-1500 caracteres).
5. Salvar em `content/drafts/<topic_id>.md` e atualizar status do topic para `drafted`.
```

- [ ] **Step 2: Verificar**

```bash
python3 -c "import yaml; d=yaml.safe_load(open('.agents/skills/write-post/SKILL.md').read().split('---')[1]); assert d['name']=='write-post'; print('OK')"
grep -c "900" .agents/skills/write-post/SKILL.md
```

Expected: `OK`; regra de tamanho presente.

- [ ] **Step 3: Commit**

```bash
git add .agents/skills/write-post/
git commit -m "feat: skill write-post"
```

---

### Task 12: Skill `critique-post`

**Files:**
- Create: `.agents/skills/critique-post/SKILL.md`

**Interfaces:**
- Consumes: `content/drafts/<topic_id>.md`, `memory/writing_style.md`.
- Produces: críticas ao draft (o executor corrige; depois passa por `escrita-humana`).

- [ ] **Step 1: Escrever o SKILL.md**

```markdown
---
name: critique-post
description: Use quando um draft de post estiver pronto e precisar de crítica antes da aprovação (clareza, originalidade, credibilidade, tom humano, risco de alucinação).
---

# Critique Post

## Overview

Criticar a primeira versão do post antes da aprovação, procurando especificamente clichês de IA, falta de evidência e tom genérico.

## Quando Usar / Quando NÃO Usar

- Usar: após write-post, antes da aprovação.
- NÃO usar: para reescrever o post (apenas criticar); para validar texto já aprovado.

## Entrada

- `content/drafts/<topic_id>.md`
- `memory/writing_style.md` (regras do autor)

## Critérios

clareza, originalidade, credibilidade, tom humano, densidade, relevância, consistência, uso de evidências, risco de alucinação, linguagem genérica de IA

## Frases-clichê a procurar (quando usadas de forma genérica)

- "Em um mundo cada vez mais..."
- "A inteligência artificial veio para..."
- "Mais do que nunca..."
- "Não é sobre X, é sobre Y..."

## Saída

Lista de críticas por critério, com:
- O que está bom (manter)
- O que está fraco (corrigir)
- Risco de alucinação (afirmações sem origem no brief)
- Sugestão concreta de correção

## Fluxo

1. Ler o draft e o writing_style.md.
2. Avaliar cada critério (0-10) com justificativa.
3. Procurar frases-clichê e tom genérico.
4. Verificar que todo fato tem origem no brief (risco de alucinação).
5. Verificar tamanho (900-1500 caracteres) e esqueleto.
6. Entregar a lista de críticas. O executor corrige o draft; depois o post passa por `escrita-humana` e pela aprovação do autor.

## Regras

- Crítica específica, não genérica ("melhore o texto" é proibido).
- Não reescrever — apontar e sugerir.
- Se o draft estiver bom, dizer o que está bom (nem tudo é falha).
```

- [ ] **Step 2: Verificar**

```bash
python3 -c "import yaml; d=yaml.safe_load(open('.agents/skills/critique-post/SKILL.md').read().split('---')[1]); assert d['name']=='critique-post'; print('OK')"
grep -c "alucinação" .agents/skills/critique-post/SKILL.md
```

Expected: `OK`; risco de alucinação presente.

- [ ] **Step 3: Commit**

```bash
git add .agents/skills/critique-post/
git commit -m "feat: skill critique-post"
```

---

## Self-Review

**1. Cobertura da spec/design:**
- Estrutura de diretórios → Task 1 ✅
- Configs (frentes, sources, authors, scoring) → Task 2 ✅
- Memória (3 arquivos) → Task 3 ✅
- mapa.md → Task 4 ✅
- AGENTS.md → Task 5 ✅
- 7 skills do pipeline → Tasks 6-12 ✅
- Roadmap → Task 1 ✅
- README → Task 1 ✅
- Skill publicar-linkedin (já atualizada) → fora do plano (feita) ✅
- Skills mantidas (last30days, visao-nativa-primeiro, escrita-humana, orquestrador-runtime) → documentadas no mapa.md (Task 4) ✅

**2. Placeholder scan:** nenhum TBD/TODO; todo conteúdo de arquivo está no plano. ✅

**3. Consistência de tipos:** nomes de frentes (`ia_aplicada`, `logistica_last_mile_cx`, etc.) consistentes entre frentes.yaml, authors.yaml, signals e topics. Formato de saída de cada skill definido e referenciado pelas tasks seguintes. ✅
