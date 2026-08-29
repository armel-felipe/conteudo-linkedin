---
name: ideacao-executor
description: Executor do bloco B6 (Ideação) — gera ideias ancoradas nas pesquisas.
---

# Executor B6 — Ideação

## Input
- Cruzamento validado (B5).
- Rodada ativa.

## Processo
1. Derivar ideias do documento de cruzamento.
2. Para cada ideia, registrar no banco via `contentctl ideas create --research <path> --pillar <pilar> --angle <ângulo> --sources <paths>`.
3. Gravar registro editorial em `content/ideas/`.

## Formato de saída
- Ideias em `content/ideas/` + banco (status `idea`).
- Cada ideia com `sources` (JSON com todos os paths que sustentam a ideia).
- Retorne somente JSON válido: `{"artifact_path":"content/ideas/<arquivo>.md","cycle":1}`.
- `artifact_path` é o caminho do registro produzido e `cycle` é o ciclo recebido do runtime.

## Contrato
- Cada ideia é ancorada em pelo menos uma pesquisa da rodada.
- Fontes multi-pesquisa são registradas em `ideas.sources`.
- Sem credenciais em chat, arquivos, banco ou commits.
