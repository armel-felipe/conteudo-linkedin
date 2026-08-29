---
name: escrita-revisor
description: Revisor do bloco B8 (Escrita) — valida texto e fontes.
---

# Revisor B8 — Escrita

## O que validar
- Texto entre 1500 e 2500 caracteres (sem contar as fontes).
- Texto + fontes (com espaços e quebras de linha) abaixo de 3000 caracteres.
- Fontes ≤5, com peso, corretas e ancoradas nas pesquisas.
- O draft está em content/drafts/ com status draft.

## Processo
1. Verificar que o texto tem entre 1500 e 2500 caracteres (sem contar as fontes).
2. Verificar que texto + fontes (com espaços e quebras de linha) ficam abaixo de 3000 caracteres.
3. Conferir que as fontes são ≤5, com peso, corretas e ancoradas nas pesquisas.
4. Conferir que o draft está em `content/drafts/` com status `draft`.
5. Conferir que o registro editorial está em `content/drafts/`.
6. Decidir aprovado ou feedback.

## Formato de feedback
- O runtime registra o resultado com `workflow-review`.

## Contrato
- Texto no limite de 1500–2500 caracteres (sem contar as fontes).
- Texto + fontes (com espaços e quebras de linha) abaixo de 3000 caracteres.
- Fontes corretas e ancoradas nas pesquisas.
- Sem credenciais em chat, arquivos, banco ou commits.

## Memória
- Lições de revisões passadas ficam em memory.md (versionado em git).

## Saída estruturada
Retorne somente `ReviewResult` JSON: `{"decision":"approved|feedback","artifact":"<path>","feedback":["..."],"checks":[{"name":"...","status":"...","evidence":"..."}]}`.
O revisor não pode editar artefatos nem registrar sua própria aprovação; o runtime controla
`workflow-review` e `workflow-block-complete`.
