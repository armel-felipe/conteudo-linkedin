# Conteúdo LinkedIn — Pipeline de inteligência de conteúdo

Pipeline agentico **manual** que transforma pesquisa em posts relevantes no LinkedIn, operado por você em **levas**. Você aciona cada etapa — e às vezes cada post dentro de uma etapa — de forma explícita; nada roda sozinho.

O projeto começa pelo que está acontecendo e onde existe debate, não por "sobre o que escrever".

## Modelo de 3 blocos

O pipeline é dividido em **3 blocos lógicos**. Cada bloco é uma fase com fronteira nítida, saída própria e invocação manual. Um bloco não chama o próximo automaticamente.

```text
┌────────────────────────┬──────────────────────────┬────────────────────────┐
│  BLOCO 1               │   BLOCO 2                │   BLOCO 3              │
│  Pesquisar e escolher  │   Gerar o post           │   Publicar             │
│                        │                          │                        │
│  sinais → temas        │  tema → brief → draft    │  aprovado → LinkedIn   │
│  → oportunidades       │  → post aprovado         │  (publica ou agenda)   │
└────────────────────────┴──────────────────────────┴────────────────────────┘
   gera o backlog            gera texto aprovado          publica no LinkedIn
```

### Fluxo de ponta a ponta

```text
frentes → sinais → temas → oportunidades → brief → draft → aprovação humana → publicação/agendamento
```

## Bloco 1 — Pesquisar e escolher (gera ideias)

**O que faz:** descobre o que está acontecendo e onde há debate, agrupa em temas, pontua e monta o backlog de oportunidades prontas para virar post.

**Fluxo canônico do bloco:**

```
discover-signals → (analyze-discussions, opcional) → cluster-signals → score-opportunities
```

**Como operar (invocações que você faz no OpenWork):**

| Ação (leva) | Como invocar | O que acontece |
|---|---|---|
| Descobrir sinais | `Rode discover-signals para as cinco frentes` | Coleta 20–50 sinais por frente e salva em `research/signals/signals_YYYY-MM-DD.yaml`. Usa a skill `last30days` como principal fonte. |
| Aprofundar um debate *(opcional)* | `Analise o debate do signal X` | Adiciona um bloco de discussão a um signal promissor. |
| Agrupar em temas | `Rode cluster-signals` | Agrupa sinais do mesmo fenômeno em temas e salva em `research/topics/topics_YYYY-MM-DD.yaml`. |
| Pontuar o backlog | `Rode score-opportunities` | Dá nota 0–100 a cada tema e ordena o backlog em `content/backlog.md`. |

**Saída do bloco:** backlog com temas `status: ready_for_research`. **Este bloco não escreve posts.**

## Bloco 2 — Gerar o post (de tema a texto aprovado)

**O que faz:** pega temas `ready_for_research` do backlog, pesquisa a fundo cada um, escreve o post, revisa e humaniza até a aprovação — em lote, com checkpoints e falha isolada (se um tema falha, os outros seguem).

**Skill única:** `run-editorial-batch`. Você não chama as etapas internas isoladamente numa rodada.

**Como operar (invocação):**

```text
Rode run-editorial-batch --topics 1            # só o melhor tema elegível
Rode run-editorial-batch --topics 5            # os 5 melhores
Rode run-editorial-batch --topics all          # todos os prontos
Rode run-editorial-batch --topics id1,id2      # temas específicos, nessa ordem
```

**Fluxo canônico por tema (executado pelo lote, em ordem obrigatória):**

```
research-topic → brief_review_gauntlet → write-post → critique-post
→ correction_gauntlet → humanize_pass_1 → humanize_review_1
→ humanize_pass_2 → humanize_review_2 → approval_humana
```

- **research-topic** — pesquisa a fundo e gera o `research/briefs/topic_*.md` (fatos, números, argumentos dos dois lados, incertezas, fontes com URL e data).
- **brief_review_gauntlet** — gate: exige ≥2 fontes independentes e conexão com a experiência do autor.
- **write-post** — escreve o rascunho em `content/drafts/topic_*.md` (900–1500 caracteres, estrutura editorial, seção `## Fontes`). **Não pesquisa** — só usa o brief.
- **critique-post** — crítica o rascunho (clareza, originalidade, tom humano, risco de alucinação, clichês de IA…).
- **correction_gauntlet** — corrige o rascunho conforme a crítica.
- **humanize_pass_1 / review_1** e **humanize_pass_2 / review_2** — duas passadas obrigatórias de escrita humana.
- **approval_humana** — você aprova o texto; ele recebe o marco editorial `approved`, mantendo-se em `content/drafts/topic_*.md`.

**Regras que valem para você ao operar o bloco 2:**

- Cada gate (Gauntlet) usa até **5 ciclos** e aprova só com `coverage ≥ 0.99` e todos os critérios `≥ 9/10`. Falha → o tema vira `blocked` e **o lote segue para o próximo** (não para tudo).
- Há **checkpoints persistentes** em `runs/<run_id>/` a cada etapa — dá para retomar de onde parou.
- O lote **nunca publica nem agenda**. Ele termina em `approved`.
- Só entram temas com `status: ready_for_research`.

**Saída do bloco:** post com marco editorial `approved` (arquivo ainda em `content/drafts/`). **Este bloco não publica.**

## Bloco 3 — Publicar (texto aprovado para o LinkedIn)

**O que faz:** publica ou agenda um post aprovado no LinkedIn, usando a sessão já logada do browser do OpenWork. **Sem credenciais** — só a sessão do browser.

**Skill única:** `publicar-linkedin`.

**Como operar (invocação):**

```text
Publique content/drafts/topic_X.md agora
Agende content/drafts/topic_X.md para 2026-09-10 às 09:00 (horário de São Paulo)
```

**Entrada:** post em `content/drafts/` com marco `approved`. **Nunca** um post já agendado (que já moveu para `published/`).

**Saída:** post publicado ou agendado no LinkedIn, com confirmação visual na lista; o horário é registrado no arquivo como `<!-- agendado: ... -->`; o arquivo **move** de `content/drafts/` para `content/published/`. `approved` é marco editorial (não pasta) e `content/approved/` permanece vazia.

**Regras:**

- Rota do browser, em ordem: **MCP Chrome DevTools → Playwright (`playwright_fallback`) → screenshot → visão → stop**. MCP é a rota inicial; Playwright só pode ser usado como `playwright_fallback` quando MCP falhar antes de uma mutação confirmada.
- **Registrar** em cada execução a rota escolhida e o **motivo**: registro de rota, razão, resultado e evidência.
- O fallback visual (screenshot + visão) ocorre **depois das duas rotas** de controle e não substitui evidência; em mutação ambígua, pare em **fail-closed**, não repita.
- Agendar exige confirmar data e hora, refazer o horário após trocar a data, conferir prévia e confirmar em "Publicações agendadas".
- Nunca abrir um novo composer para reagendar uma publicação existente (evita duplicata) — use `Alterar agenda`.
- A aprovação editorial (bloco 2) é separada da publicação (bloco 3).
- O timestamp só é registrado no arquivo aprovado depois da confirmação na lista, sem nova aprovação textual.

## Estado dos artefatos do pipeline

```text
discovered → clustered → candidate → ready_for_research → researched
→ drafted → approved → published → archived
```

- `research/signals/` — os sinais (`discovered` → `clustered`)
- `research/topics/` — os temas e scores (`candidate` → `ready_for_research`)
- `content/backlog.md` — oportunidades ranqueadas
- `research/briefs/` — briefs de pesquisa
- `content/drafts/` — posts em elaboração (todo texto ainda não agendado, mantém-se aqui mesmo após o marco editorial `approved`)
- `content/published/` — posts já agendados ou com publicação disparada
- `content/arquived/` — posts descartados do pipe por decisão humana (começa vazia)
- `runs/` — estado, checkpoints, reviews e métricas das rodadas de lote

**Regra de movimentação:** cada post vive em **exatamente uma** pasta de `content/`. `approved` é um **marco editorial lógico** (fim do Bloco 2), não pasta física: o texto continua em `content/drafts/` até ser agendado. Ao mudar de fase, o arquivo é **movido literalmente** (git mv / mv): `draft → published` quando o Bloco 3 agenda/publica, ou `→ arquived/` quando você descarta o post. O histórico de markers (`<!-- agendado: ... -->`) acompanha o arquivo.

## Skills envolvidas e o que fazem

Cada skill é invocada por frase no OpenWork. O agente lê a skill e executa só aquela etapa.

| Skill | Bloco | O que faz | Quando invocar |
|---|---|---|---|
| `last30days` | 1 | Pesquisa o que se discute nos últimos 30 dias em Reddit, HN, YouTube, TikTok e mais | dentro do `discover-signals` (principal) |
| `discover-signals` | 1 | Descobre 20–50 sinais por frente e persiste em `research/signals/` | diariamente |
| `analyze-discussions` | 1 | Aprofunda o debate de um signal promissor | opcional, sob demanda |
| `cluster-signals` | 1 | Agrupa sinais em temas com pergunta central e tese | 2×/semana |
| `score-opportunities` | 1 | Pontua 0–100 cada tema e ordena o backlog | 2×/semana |
| `run-editorial-batch` | 2 | Roda pesquisa → escrita → humanização → aprovação em lote | quando quiser gerar posts |
| `research-topic` | 2 | Pesquisa a fundo e gera o brief | dentro do lote |
| `write-post` | 2 | Escreve o draft do post a partir do brief | dentro do lote |
| `critique-post` | 2 | Critica o draft antes dos ajustes | dentro do lote |
| `gauntlet-loop` | 2 | Validar tarefas com gates determinísticos e bloqueio fail-closed | revisão transversal |
| `escrita-humana` | 2 | Humaniza o texto preservando sua voz | dentro do lote (2 passadas) |
| `publicar-linkedin` | 3 | Publica/agenda post aprovado no LinkedIn via browser logado | sempre após aprovação |
| `visao-nativa-primeiro` | — | Política visual (visão nativa antes de image-analyzer) | tarefas visuais |
| `orquestrador-runtime` | — | **LEGADO** — não usar no fluxo novo | nunca |

Consulte `mapa.md` para o objetivo, o vínculo e a invocação detalhados de cada skill.

## Pré-requisitos

- OpenWork/OpenCode com acesso a este workspace.
- Skill `last30days` disponível em `.agents/skills/last30days/`.
- Python 3.12+ para executar o engine do `last30days`.
- `PyYAML` para validar os arquivos YAML: `pip install pyyaml`.
- Sessão do LinkedIn já autenticada no browser do OpenWork — **somente** para o bloco 3.

### Configuração inicial

```bash
cp .env.example .env
```

O `.env` é local e nunca deve ser commitado. O `.env.example` traz o comando portátil da pesquisa `last30days`.

## Onde configurar o projeto

| Arquivo | Função |
|---|---|
| `config/frentes.yaml` | Frentes, prioridades, keywords e perguntas de pesquisa |
| `config/sources.yaml` | Fontes disponíveis e pesos |
| `config/authors.yaml` | Autores para acompanhar |
| `config/scoring.yaml` | Critérios e pesos do ranking |
| `memory/professional_experience.md` | Experiências que fundamentam os posts |
| `memory/opinions.md` | Opiniões e posições do autor |
| `memory/writing_style.md` | Voz, estrutura, tamanho e restrições de escrita |

> As memórias são rascunhos e devem ser revisadas por você antes de serem tratadas como definitivas.

## Sequência resumida por bloco

```text
Bloco 1: discover-signals → (analyze) → cluster-signals → score-opportunities  → backlog
Bloco 2: run-editorial-batch --topics N                                           → approved
Bloco 3: publicar-linkedin                                                         → LinkedIn
```

O roadmap está em `docs/roadmap.md`. O guia completo das skills está em `mapa.md`. O contrato de operação está em `AGENTS.md`.

## Segurança

- Nunca commite `.env` ou credenciais.
- Não coloque tokens, cookies ou chaves de API em posts, briefs ou memória.
- A publicação usa somente a sessão já logada do browser do OpenWork.
