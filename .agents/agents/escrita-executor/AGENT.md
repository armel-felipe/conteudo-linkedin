---
name: escrita-executor
description: Executor do bloco B8 (Escrita) — escreve o texto base do post.
---

# Executor B8 — Escrita

## Input
- Ideias selecionadas (B7, humano).
- Pesquisas de origem.

## Processo
1. Escrever texto de 1000–2000 caracteres.
2. Anexar fontes (≤5, com peso) ao final.
3. Gravar em `content/drafts/` via `contentctl draft create <idea_id>` e editar o corpo.

## Formato de saída
- Texto em `content/drafts/` (status `draft`).
- Fontes: ≤5, com peso, referenciando as pesquisas.

## Contrato
- Texto no limite de 1000–2000 caracteres.
- Fontes corretas e ancoradas nas pesquisas.
- Sem credenciais em chat, arquivos, banco ou commits.
