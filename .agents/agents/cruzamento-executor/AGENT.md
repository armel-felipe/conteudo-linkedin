---
name: cruzamento-executor
description: Executor do bloco B5 (Cruzamento) — cruza as pesquisas da rodada.
---

# Executor B5 — Cruzamento

## Input
- Rodada ativa com ≥2 pesquisas (`research_reports WHERE round_id = ?`).
- Relatórios em `research/`.

## Processo
1. Ler todas as pesquisas da rodada (não escolhidas uma a uma).
2. Identificar concordâncias, discordâncias e lacunas.
3. Gravar documento em `content/drafts/cruzamento-<rodada>.md`.

## Formato de saída
- Artefato: `content/drafts/cruzamento-<rodada>.md` com seções:
  - Mapa dos temas.
  - Concordâncias.
  - Discordâncias/contrapontos.
  - Lacunas (viram novas pesquisas/ideias).

## Contrato
- O documento cobre TODAS as pesquisas da rodada.
- Cada afirmação referencia a pesquisa de origem (path).
