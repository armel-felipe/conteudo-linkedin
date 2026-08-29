---
name: orquestrador-runtime
description: Orquestra o pipeline editorial local (pesquisa → ideia → escrita → publicação) em rodadas, disparando executores, validando com revisores e respeitando gates humanos configuráveis via APPROVAL_*.
---

# Orquestrador de runtime do pipeline editorial

## Overview

O orquestrador coordena os blocos processuais do pipeline editorial local. A cada invocação ele:
1. Lê o estado (banco SQLite + pastas content/ + .env).
2. Define a rodada: quais blocos rodam nesta chamada, validando pré-condições.
3. Dispara executor → aguarda revisor → abre gate humano quando a chave APPROVAL_* exigir.
4. Registra validações via `contentctl bloco-ok` e avança o estado.

## Quando Usar / Quando NÃO Usar

- Usar: para executar qualquer etapa do pipeline editorial (pesquisa, ideação, escrita, revisão, publicação).
- NÃO usar: para editar código do pipeline, para publicar conteúdo fora de content/approved/, para tarefas não editoriais.

## Blocos processuais

| Bloco | Nome | Executor | Revisor | Gate |
|---|---|---|---|---|
| B1 | Convoca | orquestrador-runtime-executor | orquestrador-runtime-revisor | humano confirma plano |
| B2 | Pilar | pilar-executor | pilar-revisor | APPROVAL_PILAR |
| B3 | Pesquisa MECE | pesquisa-mece-executor | pesquisa-mece-revisor | APPROVAL_PESQUISA |
| B4 | Executa pesquisa | pesquisa-executor | pesquisa-revisor | APPROVAL_EXECUCAO |
| B5 | Cruzamento | cruzamento-executor | cruzamento-revisor | APPROVAL_CRUZAMENTO |
| B6 | Ideação | ideacao-executor | ideacao-revisor | APPROVAL_IDEACAO |
| B7 | Escolha | humano (sempre) | — | sempre human |
| B8 | Escrita | escrita-executor | escrita-revisor | APPROVAL_ESCRITA |
| B10 | Escrita-humana | escrita-humana-executor | escrita-humana-revisor | APPROVAL_REFINAMENTO |
| B9 | Valida | humano | — | APPROVAL_VALIDACAO |
| B11 | Publica | publicar-linkedin-executor | publicar-linkedin-revisor | APPROVAL_PUBLICACAO |

## Ordem real de execução

B1 → B2 → B3 → B4 → [repetir B3-B4] → B5 → B6 → [GATE] B7 → B8 → B10 → B9 → B11

## Leitura de estado

- Banco: `data/content.db` (via `contentctl` e consultas diretas).
- Pastas: `research/`, `content/ideas/`, `content/drafts/`, `content/approved/`, `content/published/`.
- Config: `.env` (chaves APPROVAL_*).

## Gates APPROVAL_*

Cada bloco com gate lê a chave correspondente no `.env`:
- `human` (default): após o revisor aprovar, o orquestrador PAUSA e pede confirmação humana.
- `agent`: a validação do revisor é suficiente; o orquestrador avança sem pausa.

B7 é sempre humano — não há chave.

## Ciclo de revisão (por bloco)

O runtime não executa agentes implicitamente: cada executor e revisor é despachado
explicitamente em uma nova chamada `task`. O limite é `ORCHESTRATOR_MAX_REVIEW_CYCLES`,
com default `3`; valores ausentes ou inválidos usam esse default.

### Procedimento copiável

Para cada bloco, o runtime deve executar exatamente esta sequência:

1. Chamar `workflow-cycle-start` e guardar o id/ciclo retornado.
2. Despachar o executor com `task`, carregando o caminho exato do contrato
   `.agents/agents/<slug>-executor/AGENT.md` e `memory.md` quando existir.
3. Exigir do executor somente JSON estruturado com `artifact_path` e `cycle`; executar
   as verificações determinísticas do bloco.
4. Despachar o revisor como um novo `task`, nunca reutilizando contexto, carregando os
   caminhos exatos `.agents/agents/<slug>-revisor/AGENT.md` e
   `.agents/agents/<slug>-revisor/memory.md`, além do estado atual e do artefato.
5. Aceitar do revisor somente `ReviewResult` JSON:
   `{"approved": true|false, "feedback": ["..."]}`. Resposta ausente, inválida ou
   fora do schema é `invalid-response`: não avançar, não aprovar e fechar o fluxo.
6. Chamar `workflow-review` com o `ReviewResult`. Se houver feedback, incluir o feedback completo
   em uma nova tarefa `task` do executor, junto do contrato exato, estado e
   artefato, e repetir desde a verificação determinística.
7. Parar quando o ciclo atingir `ORCHESTRATOR_MAX_REVIEW_CYCLES`; sem aprovação até lá,
   encerrar fail-closed, sem chamar comandos de transição.
8. Somente após aprovação válida chamar `workflow-block-complete` e então avaliar o gate
   humano `APPROVAL_*`. Nenhuma outra transição é permitida antes desses passos.

Se o executor não retornar JSON válido, o artefato não existir, o revisor não retornar
`ReviewResult` válido ou qualquer comando falhar, o estado fica fail-closed: registrar o
erro, não chamar `contentctl bloco-ok`, não chamar `workflow-block-complete` e não avançar.

## Invocação

- "Roda o pipeline para o pilar X" → B1→B11 conforme pré-condições.
- "Executa a pesquisa Y" → B3→B4.
- "Escreve o post da ideia Z" → B8→B10→B9.
- "Publica content/approved/<arquivo>.md" → B11.

## Erros comuns

- Pular o revisor: todo trabalho de executor passa por revisor antes de qualquer aprovação.
- Pular B7: a escolha de ideias é sempre humana.
- Publicar fora de approved/: o conteúdo publicado vem somente de content/approved/.
- Sintetizar pesquisa: o stdout do LAST30DAYS_COMMAND é preservado verbatim.
