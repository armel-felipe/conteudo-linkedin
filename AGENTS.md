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
- **Saídas persistentes:** `research/briefs/topic_*.md`, `content/drafts/topic_*.md`, `runs/<run_id>/manifest.yaml` + `state.yaml`/`events.yaml`/`reviews/`, e por fim `content/approved/topic_*.md`.
- **Estado fim do bloco:** arquivo em `content/approved/`. **O bloco 2 não publica nem agenda.**

### Bloco 3 — Publicar (texto aprovado para o LinkedIn)

- **Objetivo:** publicar ou agendar um post aprovado no LinkedIn usando a sessão logada do browser do OpenWork.
- **Skill único:** `publicar-linkedin`.
- **Entrada:** somente arquivos em `content/approved/`. **Não entra post de `drafts/`.**
- **Saída:** post publicado/agendado no LinkedIn; comentário `<!-- agendado: ... -->` registrado no arquivo aprovado; `content/published/` marcando o que já saiu.
- **Estado fim do bloco:** publicado ou agendado com confirmação na lista.

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
- `content/` — backlog, drafts, approved, published
- `memory/` — experiência, opiniões, estilo de escrita

## Segurança

- `.env` nunca vai para o git; credenciais nunca em chat, arquivos ou commits.
- Publicação usa apenas a sessão logada do browser do OpenWork (sem credenciais).

## Estados de conteúdo

discovered → clustered → candidate → ready_for_research → researched → drafted → approved → published → archived
