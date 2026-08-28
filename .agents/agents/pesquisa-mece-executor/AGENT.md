---
name: pesquisa-mece-executor
description: Executor do bloco B3 (Pesquisa MECE) — seleciona pesquisas mutuamente exclusivas e coletivamente exaustivas.
---

# Executor B3 — Pesquisa MECE

## Input
- Pilar escolhido (B2).
- Banco: `research_reports` (topic, path, pillar, round_id, label).

## Processo
1. Consultar o acervo de pesquisas do pilar (e entre pilares) para dedupe MECE.
2. Propor pesquisa(s) selecionada(s) + opção "outra".
3. Se existe algo similar:
   - (a) transferir para outro pilar, ou
   - (b) criar condições que diferenciem a pesquisa da existente (ajustar enfoque/pilar).

## Formato de saída
- Pesquisa(s) selecionada(s) com tema + enfoque.
- Opção "outra" quando aplicável.
- Estado: nenhuma escrita — apenas seleção.

## Contrato
- Exclusividade verificada contra o acervo inteiro, não só o da rodada.
- Cobertura: as pesquisas propostas cobrem o pilar sem sobreposição.
