---
name: orquestrador-runtime-executor
description: Executor do bloco B1 (Convoca) — produz o plano de rodada.
---

# Executor B1 — Convoca

## Input
- Skill orquestradora invocada.
- Estado atual: banco (data/content.db), pastas content/, .env.

## Processo
1. Ler o estado: pilares aprovados, pesquisas da rodada ativa, ideias, drafts, approved.
2. Definir a rodada: quais blocos rodam nesta chamada, validando pré-condições.
3. Escrever o plano de rodada em `runtime/rodadas/<ts>.md` com:
   - Rodada (id, pilar, status).
   - Blocos a executar e ordem.
   - Pré-condições de cada bloco.
   - Gates APPROVAL_* aplicáveis.

## Formato de saída
- Artefato: `runtime/rodadas/<ts>.md` (plano de rodada).
- Estado: rodada criada no banco via `Database.create_round`.

## Contrato
- O plano é coerente com o estado real (não inventar pilares/pesquisas).
- B7 (escolha) é sempre humano — nunca listado como gate automático.
- Sem credenciais em chat, arquivos, banco ou commits.
