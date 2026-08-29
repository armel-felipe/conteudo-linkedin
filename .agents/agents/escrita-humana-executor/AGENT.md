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
2. Reanexar as fontes ao final.

## Formato de saída
- Texto refinado em `content/drafts/`.
- Fontes reanexadas (≤5, com peso).

## Contrato
- Texto + fontes (com espaços e quebras de linha) abaixo de 3000 caracteres.
- Fontes intactas (mesmas do texto base).
- Sem credenciais em chat, arquivos, banco ou commits.
