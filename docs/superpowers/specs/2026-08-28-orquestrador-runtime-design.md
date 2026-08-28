# Design — Orquestrador de runtime do pipeline editorial

- **Data:** 28/08/2026
- **Status:** aprovado (design)
- **Escopo:** skill orquestradora + agentes executores/revisores + indexação por rodada + gates de aprovação configuráveis, cobrindo o fluxo completo pesquisa → ideia → escrita → publicação

---

## Contexto e motivação

O pipeline de produção de conteúdo é **local** (pesquisa → ideia → draft → revisão → aprovação) e não
depende de Zernio. Hoje os passos são executados ad hoc: `contentctl research discover`, `pillars
propose/approve`, `ideas create`, `draft create`, e a skill `publicar-linkedin` para o envio.

O que falta é um **orquestrador** que:

1. Defina **blocos processuais independentes** (cada um com executor, revisor, gate e contrato de artefato).
2. Permita **rodadas dinâmicas** — a cada chamada, seleciona quais blocos rodam, validando pré-condições.
3. Garanta que **todo trabalho de subagente passe por um revisor especializado** antes de qualquer aprovação.
4. Mantenha **estado persistente** (banco + pastas `content/`) para retomada e automação futura.
5. Permita **autonomia progressiva** via chaves `APPROVAL_*` no `.env` (`human` → `agent`), sem mudar os blocos.

---

## Arquitetura (3 camadas)

```
┌─────────────────────────────────────────────────────┐
│  CAMADA 1: SKILL ORQUESTRADORA (fluxo, gates, rodada)│
│  .agents/skills/orquestrador-runtime/SKILL.md        │
│  - Lê estado (banco + pastas + .env)                 │
│  - Define rodada: quais blocos rodam nesta chamada   │
│  - Dispara executor → aguarda revisor → gate humano  │
│  - Orquestra paralelismo entre blocos independentes  │
└──────────────┬──────────────────────────────────────┘
               │ invoca
┌──────────────▼──────────────────────────────────────┐
│  CAMADA 2: AGENTES (executores + revisores)          │
│  .agents/agents/<bloco>-executor/  (AGENT.md +       │
│  .agents/agents/<bloco>-revisor/   memory.md próprio)│
│  - Executor produz artefato conforme contrato        │
│  - Revisor valida contra requisitos + memória        │
└──────────────┬──────────────────────────────────────┘
               │ chama (passos mecânicos)
┌──────────────▼──────────────────────────────────────┐
│  CAMADA 3: CONTENTCTL (estado, persistência)         │
│  research discover --pillar, pillars propose/approve │
│  ideas create, draft create, + NOVOS: bloco-ok,      │
│  publish-complete (move approved→published)           │
└──────────────────────────────────────────────────────┘
```

**Princípios de isolamento:**
- Cada agente tem diretório próprio com instruções estáveis + `memory.md` (feedbacks versionados em git).
- Contratos de artefato são **arquivos** (não estado volátil) — cada bloco grava saída em `content/` ou `research/` e registra status no SQLite.
- Rodadas paralelas (sessões simultâneas) não competem: cada bloco lê/escreve artefatos com nomes únicos (prefixo `round-<id>-`).
- Versionamento: git cobre skill + agentes + specs + plans + conteúdo.

---

## Blocos processuais, contratos e gates

**Ordem real de execução** (numeração preserva a origem nos passos do fluxo; a ordem difere):

```
B1 Convoca → B2 Pilar → B3 Pesquisa MECE → B4 Executa pesquisa → [repetir B3-B4]
→ B5 Cruzamento → B6 Ideação → [GATE] B7 Escolha (humano)
→ B8 Escrita → B10 Escrita-humana → B9 Valida texto (humano) → B11 Publica
```

| Bloco | Pré-condição (inputs) | Executor | Saída (artefato + estado) | Revisor valida | Gate `APPROVAL_*` |
|---|---|---|---|---|---|
| B1 Convoca | Skill invocada | orquestrador-runtime-executor | Plano de rodada (`runtime/rodadas/<ts>.md`) | plano coerente com estado | — (humano confirma plano) |
| B2 Pilar | `pillars` com ≥1 aprovado | pilar-executor | Pilar escolhido | lista fiel ao banco | `APPROVAL_PILAR` |
| B3 Pesquisa MECE | Pilar escolhido | pesquisa-mece-executor | Pesquisa(s) selecionada(s) + opção "outra"; dedupe MECE | exclusividade/cobertura vs. banco | `APPROVAL_PESQUISA` |
| B4 Executa pesquisa | Pesquisa aprovada | pesquisa-executor | `research/<ts>-<slug>.md` + row em `research_reports` (com pillar, round_id, label) | stdout verbatim preservado + fonte LinkedIn quando houver | `APPROVAL_EXECUCAO` |
| B5 Cruzamento | ≥2 pesquisas da rodada | cruzamento-executor | `content/drafts/cruzamento-<rodada>.md` (concordâncias/discordâncias/lacunas) | cobre todas as pesquisas da rodada | `APPROVAL_CRUZAMENTO` |
| B6 Ideação | Cruzamento validado | ideacao-executor | Ideias em `content/ideas/` + banco (status `idea`) | cada ideia ancorada em pesquisa | `APPROVAL_IDEACAO` |
| B7 Escolha | Ideias `idea` | **humano** (sempre) | Ideias selecionadas (status `selected`) | (não há revisor; gate é humano) | sempre human |
| B8 Escrita | Ideias selecionadas | escrita-executor | Texto 1000–2000 chars + fontes (≤5, peso) em `content/drafts/` | texto no limite + fontes corretas | `APPROVAL_ESCRITA` |
| B10 Escrita-humana | Texto base revisado | escrita-humana-executor | Texto refinado ≤15% delta + fontes reanexadas | delta respeitado + fontes intactas | `APPROVAL_REFINAMENTO` |
| B9 Valida | Texto refinado | **humano** | Texto validado (status `approved`) | (gate humano; revisor já passou) | `APPROVAL_VALIDACAO` |
| B11 Publica | Texto aprovado | publicar-linkedin-executor | Post publicado + **move `approved/`→`published/`** + status `published` | publicado + estado atualizado | `APPROVAL_PUBLICACAO` |

**Chaves `.env` (default `human`):**

```
APPROVAL_PILAR=human
APPROVAL_PESQUISA=human
APPROVAL_EXECUCAO=human
APPROVAL_CRUZAMENTO=human
APPROVAL_IDEACAO=human
APPROVAL_ESCRITA=human
APPROVAL_REFINAMENTO=human
APPROVAL_VALIDACAO=human
APPROVAL_PUBLICACAO=human
```

**B7** é o único bloco **sem chave** — sempre humano por definição. O revisor-agente valida **sempre** o
trabalho do executor, independentemente da chave; a chave decide apenas se o humano também precisa
confirmar (calibração) ou se a validação do revisor é suficiente.

---

## Indexação por rodada

**Nova tabela `rounds`** (unidade de trabalho que agrupa B4→B6):

```
rounds: id, created_at, pillar (tema), status (open|closed), plano_path
research_reports: + round_id (FK), + label (TEXT ≤50 chars)
```

**Convenção de label** (aliás legível, exibido nas opções ao usuário):

```
label = YYYY_MM_DD <pillar-slug> <detalhe-pesquisa>     (≤50 caracteres)
```

Exemplo: `2026_08_28 lideranca-gestao-times cultura-times-alta-perf`

O executor B4 gera o label ao capturar a pesquisa; o humano pode renomear na validação.

**Consultas do acervo coerente** (usadas pelo orquestrador ao oferecer opções):

| Pergunta do orquestrador | Consulta |
|---|---|
| "Quais pesquisas desta rodada?" | `research_reports WHERE round_id = ?` |
| "Quais pesquisas do pilar X?" | `WHERE pillar = ?` |
| "Quais ideias derivadas destas pesquisas?" | `ideas JOIN research_reports ON research_report_id = id WHERE round_id = ?` |
| "Já existe algo similar a esta pesquisa (MECE)?" | busca por termo em `topic`/`label` dentro do pilar + **entre pilares** |
| "Que fontes sustentam esta ideia?" | `ideas.sources` (JSON, novo) |

**B5/B6 trabalham sobre o acervo da rodada:** o cruzamento recebe as pesquisas
`WHERE round_id = ?` (não escolhidas uma a uma), e a ideação deriva do documento de cruzamento,
com ligação preservada via `round_id` + `research_report_id`.

**Dedupe MECE indexado:** B3 consulta o banco (topic/pillar em `research_reports`) antes de propor
"outra" — a exclusividade é verificada contra o acervo inteiro, não só o da rodada. Se existe algo
similar, oferece: (a) transferir para outro pilar, ou (b) criar condições que diferenciem a pesquisa
da existente (ajustar enfoque/pilar).

**Fontes de ideias multi-pesquisa:** `ideas` mantém `research_report_id` (pesquisa-mãe) **+**
`ideas.sources` (JSON com todos os paths que sustentam a ideia) — reutilizando o padrão de
`posts.sources`.

---

## Subagentes, memória de revisores e paralelismo

**Estrutura por bloco** (somente A — agentes definidos no repo):

```
.agents/agents/<bloco>-executor/
├── AGENT.md        (instruções: input, processo, formato de saída, contrato)
└── memory.md       (lições de execuções passadas — opcional para executor)

.agents/agents/<bloco>-revisor/
├── AGENT.md        (instruções: o que validar contra requisitos, formato de feedback)
└── memory.md       (feedbacks acumulados — OBRIGATÓRIO, versionado em git)
```

**Ciclo de revisão** (por bloco, sempre):
1. Executor entrega artefato + dados de saída padronizados.
2. Revisor lê contrato do bloco (em AGENT.md) + sua `memory.md`.
3. Se memória ambígua/contraditória → revisor clarifica **antes** de revisar (auto-clarificação).
4. Valida contra requisitos; decide **aprovado** ou **feedback** (com dados de saída corretos/formatados).
5. Feedback → executor ajusta → revisor reavalia (loop).
6. Aprovado → registra `bloco-ok` no banco → orquestrador avança ou abre gate humano.

**Paralelismo entre rodadas (sessões):**
- Cada rodada tem `rounds.id` único; artefatos com prefixo `round-<id>-`.
- Sessões não compartilham arquivos em escrita; banco serializa por idempotência.
- O orquestrador pode disparar B4 de duas rodadas em paralelo (subagentes independentes).

**Tratamento de erro:** bloco falha → revisor registra causa; orquestrador marca rodada `open`
(pode retomar) e reporta o que falta; nada é apagado — artefatos parciais ficam visíveis para
diagnóstico.

---

## Pesquisa multicanal com peso no LinkedIn

- A pesquisa é **multicanal**: o relatório cobre last30days (YouTube, Reddit, HN, TikTok, etc.)
  **+ LinkedIn** (via ScrapeCreators no engine e/ou captura manual no browser).
- **Peso e ordem no LinkedIn:** a captura começa pelo LinkedIn (fonte com maior peso na síntese),
  e o restante dos canais complementa. Isso reflete a decisão editorial: LinkedIn primeiro, demais
  canais como contexto.
- O `LAST30DAYS_COMMAND` já inclui a fonte LinkedIn (`INCLUDE_SOURCES=linkedin` + chave
  ScrapeCreators no config global).

---

## Novos comandos `contentctl`

- `bloco-ok <bloco> <artefato>` — registra validação do revisor (contrato padronizado).
- `publish-complete <post_id> <url>` — move `approved/`→`published/`, atualiza `posts` e metadata.

---

## Roadmap e autonomia futura

**Fase 1 (agora) — Base segura:**
- Skill orquestradora + 11 blocos + agentes (executores + revisores) com memória.
- Banco v5→v6 (`rounds`, `round_id`, `label`).
- `contentctl bloco-ok` + `contentctl publish-complete` (approved→published).
- Todas as chaves `APPROVAL_*` em `human`.

**Fase 2 — Autonomia calibrada (roadmap):**
- Troca de chave `APPROVAL_*` para `agent` bloco a bloco, conforme confiança no revisor daquele bloco.
- Critério de troca: N execuções sem feedback negativo do humano naquele bloco (registrado no
  `memory.md` do revisor).
- **B7** permanece humano; roadmap registra automação futura via **agenda editorial ou critérios de
  engajamento (TBD)**.

**Fase 3 — Automação de rodadas (roadmap):**
- Automações do OpenWork (horário) consultam o estado e disparam blocos executáveis
  (ex: 10:00 pesquisa+ideação pilar X, 10:05 escrita de ideias Y, 10:07 agendamento Z).
- A automação respeita gates: para nos blocos com chave `human`; segue nos `agent`.
- `content/published/` passa a alimentar métricas de engajamento (roadmap).

**Governança de mudanças (sempre):**
- Toda mudança de fluxo: spec → plan → implementação com TDD → registro em git.
- Memória dos revisores versionada: o que o humano corrigiu vira feedback permanente.

---

## Fora do escopo (roadmap registrado em `docs/roadmap.md`)

- Automação do B7 (escolha de ideias) via agenda editorial ou engajamento (TBD).
- Métricas/analytics pós-publicação.
- Anexar imagem automaticamente na postagem (já registrado no roadmap da skill de publicação).

---

## Verificação

- Todo trabalho de subagente passa por revisor especializado antes de qualquer aprovação.
- **B7** (escolha de ideias) é o único gate humano intocável — nunca é pulado por chave de configuração.
- Rodadas paralelas não corrompem estado (idempotência + prefixo de artefato).
- O conteúdo publicado vem somente de `content/approved/` e transita para `content/published/`.
- Autonomia futura é configurável por bloco via `APPROVAL_*` no `.env`, sem mudar blocos.
