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
2. Resumir cada pesquisa em linguagem simples (o que diz, de onde veio, vozes-fonte).
3. Identificar concordâncias, discordâncias e lacunas.
4. Gravar documento em `content/drafts/cruzamento-<rodada>.md`.

## Formato de saída
- Artefato: `content/drafts/cruzamento-<rodada>.md` com seções:
  - Resumo das pesquisas (uma seção por pesquisa, em linguagem simples).
  - Mapa dos temas.
  - Concordâncias.
  - Discordâncias/contrapontos.
  - Lacunas (viram novas pesquisas/ideias).

## Convenção de referência
- Pesquisas são referenciadas como **R#** (R1, R2, R3, ...) na ordem da base de evidência.
- Contrapontos são referenciados como **P#** (P1, P2, P3, ...) na mesma ordem.
- Concordâncias como **C#**, discordâncias como **D#**, lacunas como **L#**.

## Contrato
- O documento cobre TODAS as pesquisas da rodada.
- Cada afirmação referencia a pesquisa de origem (path).
- Pesquisas sempre referenciadas como R#; contrapontos como P#.
