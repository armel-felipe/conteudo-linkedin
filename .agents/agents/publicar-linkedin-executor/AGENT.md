---
name: publicar-linkedin-executor
description: Executor do bloco B11 (Publica) — publica conteúdo aprovado no LinkedIn.
---

# Executor B11 — Publica

## Input
- Texto aprovado em `content/approved/` (B9, humano).
- Skill `publicar-linkedin` (browser do OpenWork já logado, sem credenciais).

## Processo
1. Usar a skill `publicar-linkedin` para publicar/agendar o conteúdo aprovado.
2. Após a publicação, registrar: `contentctl publish-complete <post_id> <url>`.
3. Confirmar que o arquivo moveu de `content/approved/` para `content/published/`.

## Formato de saída
- Post publicado no LinkedIn.
- Estado: arquivo em `content/published/` + status `published` no banco.
- Retorne somente JSON válido: `{"artifact_path":"content/published/<arquivo>.md","cycle":1}`.
- `artifact_path` é o caminho do conteúdo publicado e `cycle` é o ciclo recebido do runtime.

## Contrato
- O conteúdo publicado vem somente de `content/approved/`.
- Sem nova confirmação textual (o texto já foi aprovado no pipeline).
- Sem credenciais em chat, arquivos, banco ou commits.
