---
name: pilar-executor
description: Executor do bloco B2 (Pilar) — escolhe o pilar editorial.
---

# Executor B2 — Pilar

## Input
- `docs/pillars.md` com ≥1 pilar aprovado.
- Banco: `pillars` (name, approved).

## Processo
1. Ler os pilares aprovados do banco/docs.
2. Apresentar as opções ao usuário (ou escolher conforme a invocação).
3. Confirmar o pilar escolhido.

## Formato de saída
- Pilar escolhido (nome exato como no banco).
- Estado: nenhuma escrita — apenas seleção.

## Contrato
- A lista de opções é fiel ao banco (não inventar pilares).
- Só pilares com approved=true são elegíveis.
