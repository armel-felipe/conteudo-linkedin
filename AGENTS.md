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
8. **Todo post termina com `## Fontes`** — arquivos em `content/drafts/` e `content/approved/` devem terminar com uma seção `## Fontes` listando as fontes usadas (título, URL, data), herdadas do brief.
9. **Entrada de lote** — para executar uma rodada de um ou mais topics, usar `run-editorial-batch`; ele seleciona e congela a fila de `ready_for_research`, processa um topic por vez e persiste checkpoints.
10. **Política Gauntlet** — briefs e posts passam pelo Gauntlet, com coverage `>99%`, todos os critérios `>=9/10` e no máximo cinco ciclos; hard failures sempre sobrepõem a aprovação agregada de 95%.
11. **Falha isolada** — se um topic falhar, marcar somente esse item como `blocked`, persistir o checkpoint e continuar para o próximo item da fila; nunca liberar um item bloqueado para a etapa seguinte.
12. **Escrita humana obrigatória** — todo post deve passar por duas passagens separadas de `escrita-humana`, cada uma seguida de seu próprio revisor, antes da aprovação humana.

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
