# AGENTS.md — Contrato de Operação

## Projeto

Pipeline agentico manual de conteúdo para LinkedIn. Fluxo: frentes → sinais → debates → temas → oportunidades → tese → evidências → contexto do autor → post.

## Blocos

O pipeline opera em **três blocos lógicos**, executados em levas. Cada bloco tem fronteira nítida, saída persistente própria e é acionado por invocações específicas. **Um bloco não atravessa o outro.**

### Bloco 1 — Pesquisar e escolher (gera ideias e a fila)

- **Objetivo:** descobrir o que está acontecendo, agrupar em temas, pontuar e formar o backlog de oportunidades `ready_for_research`.
- **Skills (fluxo canônico):** `discover-signals` → `analyze-discussions` (opcional, sob demanda) → `cluster-signals` → `score-opportunities`.
- **Ferramenta de pesquisa do bloco:** skill `last30days` (primária).
- **Saídas persistentes:** `research/signals/signals_*.yaml` (signals `discovered`/`clustered`), `research/topics/topics_*.yaml` (temas `candidate` e depois `ready_for_research`), `content/backlog.md` (ranqueado por score).
- **Estado fim do bloco:** backlog com temas `ready_for_research`. **O bloco 1 não gera posts.**

### Bloco 2 — Gerar o post (de tema a texto aprovado)

- **Objetivo:** transformar um tema `ready_for_research` em um post `approved`, em lote, com checkpoints e falha isolada.
- **Skill único de entrada:** `run-editorial-batch` (não invocar as etapas internas isoladamente numa rodada).
- **Fluxo canônico por topic (em ordem obrigatória):** `research-topic` → `brief_review_gauntlet` → `write-post` → `critique-post` → `correction_gauntlet` → `humanize_pass_1` → `humanize_review_1` → `humanize_pass_2` → `humanize_review_2` → `approval_humana`.
- **Saídas persistentes:** `research/briefs/topic_*.md`, `content/drafts/topic_*.md`, `runs/<run_id>/manifest.yaml` + `state.yaml`/`events.yaml`/`reviews/`. O post **permanece em `content/drafts/`** mesmo após a aprovação.
- **Estado fim do bloco:** post com marco editorial `approved` (arquivo ainda em `content/drafts/`). **O bloco 2 não publica, agenda nem move o arquivo.**

### Bloco 3 — Publicar (texto aprovado para o LinkedIn)

- **Objetivo:** publicar ou agendar um post aprovado no LinkedIn usando a sessão logada do browser do OpenWork.
- **Skill único:** `publicar-linkedin`.
- **Entrada:** posts com marco `approved` que ainda estão em `content/drafts/`. **Não entra post que já foi agendado** (já moveu para `published/`).
- **Saída:** post publicado/agendado no LinkedIn; comentário `<!-- agendado: ... -->` registrado no arquivo; arquivo **movido literalmente** de `content/drafts/` para `content/published/` após a confirmação do agendamento/publicação.
- **Estado fim do bloco:** publicado ou agendado com confirmação na lista; arquivo em `content/published/`.

### Regras dos blocos

- **Fronteira rígida:** bloco 1 termina no backlog; bloco 2 termina em `approved`; bloco 3 termina no LinkedIn. Nenhum bloco chama o bloco seguinte automaticamente.
- **Operação em levas:** cada bloco é acionado por invocação explícita humana, quantas vezes necessário; não há automação do fluxo entre blocos.
- **Seleção no bloco 2:** `--topics 1 | N | all | id1,id2` — sempre sobre temas `ready_for_research`.
- **Nunca** publicar/agendar dentro do bloco 2 (`run-editorial-batch` não chama `publicar-linkedin`).

## Regras centrais

1. **Nunca começar por "sobre o que escrever?"** — começar por "o que está acontecendo?" e "onde existe debate?".
2. **Cada etapa gera um artefato persistente** (signals, topics, backlog, brief, draft). Nada depende só do contexto de conversa.
3. **Pesquisa separada de redação**: quem pesquisa não escreve; quem escreve recebe briefing estruturado e NÃO pesquisa.
4. **LinkedIn é fonte complementar**, não principal.
5. **Posts**: 900–1500 caracteres / 150–250 palavras; esqueleto ABERTURA→SITUAÇÃO→APLICAÇÃO→PROBLEMA→DECISÃO→APRENDIZADO→PERGUNTA.
6. **Todo post passa por `escrita-humana`** antes da aprovação.
7. **Nunca inventar dados** — todo fato do post tem origem no brief, com fonte/URL/data.
8. **Todo post termina com `## Fontes`** — arquivos em `content/drafts/` e `content/approved/` devem terminar com uma seção `## Fontes` listando as fontes usadas (título, URL, data), herdadas do brief.
9. **Entrada de lote** — para executar uma rodada de um ou mais topics, usar `run-editorial-batch`; ele seleciona e congela a fila de `ready_for_research`, processa um topic por vez e persiste checkpoints.
10. **Política Gauntlet** — briefs e posts passam pelo Gauntlet, com `coverage >= 0.99`, todos os critérios `>=9/10` e no máximo cinco ciclos; `hard_failures` sempre sobrepõem a aprovação agregada de 95%.
11. **Falha isolada** — se um topic falhar, marcar somente esse item como `blocked`, persistir o checkpoint e continuar para o próximo item da fila; nunca liberar um item bloqueado para a etapa seguinte.
12. **Escrita humana obrigatória** — todo post deve passar por `humanize_pass_1` → `humanize_review_1` → `humanize_pass_2` → `humanize_review_2`; cada revisor usa o contrato JSON compartilhado e `hard_failures` bloqueia a aprovação humana.

## Skills

Ver `mapa.md` — guia de todas as skills (objetivo, vínculo, invocação).

## Estrutura

- `config/` — frentes, sources, authors, scoring
- `research/signals/`, `research/topics/`, `research/briefs/` — artefatos de pesquisa
- `content/` — backlog, drafts, approved, published, arquived
- `memory/` — experiência, opiniões, estilo de escrita

## Organização de posts em content/

Cada arquivo de post fica em **exatamente uma** pasta de `content/`, e é **movido literalmente** (git mv / mv) quando o estado do fluxo evolui. As pastas refletem a **fase física no pipe**:

- `content/drafts/` — todo texto que o fluxo **gerou ou editou e ainda não foi agendado**. É a pasta de trabalho; um post pode sair daqui apenas para `published/` ou `arquived/`.
- `content/published/` — texto **já agendado ou com publicação disparada** no LinkedIn (fim do Bloco 3).
- `content/arquived/` — texto que você **descartou** do pipe (não será aproveitado). Só recebe arquivo por decisão explícita sua; começa e permanece vazia a menos que você descarte.
- `approved` é um **marco editorial lógico** (fim do Bloco 2), NÃO uma pasta de destino física: o texto aprovado continua em `content/drafts/` até ser agendado.

**Regra de movimentação:** quando um post muda de fase, o arquivo é movido fisicamente:
- **Agendar/publicar** → move de `content/drafts/` para `content/published/` (a aprovação editorial e o agendamento acontecem com o arquivo ainda em `drafts/`).
- **Descartar** → move de onde estiver para `content/arquived/` (apenas por decisão sua).

O histórico dos markers (`<!-- agendado: ... -->`) acompanha o arquivo. Em qualquer momento de consulta: `published/` = agendados/disparados, `drafts/` = os demais, `arquived/` = descartados, `approved/` = vazia.

## Segurança

- `.env` nunca vai para o git; credenciais nunca em chat, arquivos ou commits.
- Publicação usa apenas a sessão logada do browser do OpenWork (sem credenciais).

## Estados de conteúdo

discovered → clustered → candidate → ready_for_research → researched → drafted → approved → published → archived
