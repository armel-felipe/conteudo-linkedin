# Mapa de Skills

Guia de todas as skills do projeto: objetivo, vínculo com o pipeline e como invocar.
Referenciado pelo `AGENTS.md`.

> **Blocos:** o pipeline opera em 3 blocos — **1 Pesquisar e escolher**, **2 Gerar o post**, **3 Publicar**. Veja `AGENTS.md` (§Blocos) e `README.md`.

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
| `gauntlet-loop` | Validar uma tarefa nova em ciclos isolados com gates determinísticos e bloqueio fail-closed | Procedimento transversal de revisão | "roda o gauntlet da tarefa X" |
| `run-editorial-batch` | Selecionar e executar uma fila congelada de topics, sequencialmente, com checkpoints e bloqueio individual | Novo ponto de entrada para pesquisa e redação em lote | "roda um lote editorial com --topics N" |

## Skills mantidas (existentes)

| Skill | Objetivo | Vínculo | Invocação |
|---|---|---|---|
| `last30days` | Pesquisar o que se discute nos últimos 30 dias (Reddit, HN, YouTube, etc.) | Ferramenta primária de pesquisa do `discover-signals` | "pesquisa last30days sobre X" |
| `publicar-linkedin` | Publicar/agendar conteúdo aprovado no LinkedIn via browser logado; MCP Chrome DevTools (`mcp_chrome_devtools`) é a rota inicial, e Playwright é `playwright_fallback` somente após falha registrada, seguido de `screenshot` e visão como fallback visual pós-rotas; registrar motivo, resultado e evidência, com fail-closed e `stop` se ilegível | Etapa final operacional, separada da aprovação editorial e do lote (`run-editorial-batch` não publica nem agenda) | "publica content/approved/X.md amanhã às 9h" |
| `visao-nativa-primeiro` | Política visual: visão nativa antes do fallback ao image-analyzer | Transversal (tarefas visuais) | Seguir sempre em tarefas visuais |
| `escrita-humana` | Editar rascunhos para ficarem mais humanos, preservando a voz | Revisão obrigatória de todo post | "revisa com escrita-humana" |
| `orquestrador-runtime` | Orquestrador do pipeline editorial antigo | LEGADO — fora do fluxo novo | Não invocar |

## Notas

- `escrita-humana` é skill global do usuário (`~/.agents/skills/escrita-humana/`), não do projeto.
- `orquestrador-runtime` foi mantida na pasta, mas o fluxo novo é manual (sem orquestrador).
