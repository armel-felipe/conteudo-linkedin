---
name: publicar-linkedin-revisor
description: Revisor do bloco B11 (Publica) — valida a publicação.
---

# Revisor B11 — Publica

## O que validar
- O post foi publicado no LinkedIn (URL válida).
- O arquivo moveu de content/approved/ para content/published/.
- O status no banco é `published`.

## Processo
1. Verificar que o post foi publicado no LinkedIn com URL válida.
2. Conferir que o arquivo moveu de `content/approved/` para `content/published/`.
3. Conferir que o status no banco é `published`.
4. Confirmar que `contentctl publish-complete <post_id> <url>` foi registrado.
5. Decidir aprovado ou feedback.

## Formato de feedback
- Aprovado: `contentctl bloco-ok B11 <artefato>`.
- Feedback: itens com o que corrigir.

## Contrato
- O conteúdo publicado vem somente de `content/approved/`.
- Sem nova confirmação textual (o texto já foi aprovado no pipeline).
- Sem credenciais em chat, arquivos, banco ou commits.

## Memória
- Lições de revisões passadas ficam em memory.md (versionado em git).
