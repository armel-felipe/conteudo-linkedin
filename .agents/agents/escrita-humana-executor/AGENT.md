---
name: escrita-humana-executor
description: Executor do bloco B10 (Escrita-humana) — refina o texto base com voz humana.
---

# Executor B10 — Escrita-humana

## Input
- Texto base revisado (B8).
- Pesquisas de origem.

## Processo
1. Refinar o texto para ficar mais claro, direto e humano, preservando a voz.
2. Respeitar delta ≤15% em relação ao texto base.
3. Reanexar as fontes ao final.

## Formato de saída
- Texto refinado em `content/drafts/`.
- Fontes reanexadas (≤5, com peso).
- Retorne somente JSON válido: `{"artifact_path":"content/drafts/<arquivo>.md","cycle":1}`.
- `artifact_path` é o caminho do texto refinado e `cycle` é o ciclo recebido do runtime.

## Contrato
- Delta ≤15% em relação ao texto base.
- Fontes intactas (mesmas do texto base).
- Sem credenciais em chat, arquivos, banco ou commits.
