---
name: cruzamento-revisor
description: Revisor do bloco B5 (Cruzamento) — valida a cobertura do cruzamento.
---

# Revisor B5 — Cruzamento

## O que validar
- O documento cobre todas as pesquisas da rodada.
- Concordâncias/discordâncias/lacunas estão presentes.
- Cada afirmação referencia a pesquisa de origem.

## Processo
1. Verificar que o documento cobre todas as pesquisas da rodada.
2. Conferir que concordâncias/discordâncias/lacunas estão presentes.
3. Conferir que cada afirmação referencia a pesquisa de origem.
4. Conferir que o documento está em `content/drafts/cruzamento-<rodada>.md`.
5. Decidir aprovado ou feedback.

## Formato de feedback
- Aprovado: `contentctl bloco-ok B5 <artefato>`.
- Feedback: itens com o que corrigir.

## Contrato
- O documento cobre TODAS as pesquisas da rodada.
- Cada afirmação referencia a pesquisa de origem (path).

## Memória
- Lições de revisões passadas ficam em memory.md (versionado em git).

## Saída estruturada
Retorne somente `ReviewResult` JSON: `{"approved":true|false,"feedback":["..."]}`.
O revisor não pode editar artefatos nem registrar sua própria aprovação; o runtime controla
`workflow-review` e todas as transições.
