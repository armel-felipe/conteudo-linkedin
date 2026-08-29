# Whole-Branch Review Report

## Status

Os sete achados da revisão whole-branch foram corrigidos no orquestrador híbrido.

## Correções

- Artefatos e eventos bloqueiam e redigem atribuições com formato de credencial para `API_KEY`, `TOKEN`, `CT0`, `AUTH_TOKEN` e `PASSWORD`.
- B2 usa seleção opaca de pilar aprovado, sem exigir arquivo; B1/B3+ continuam com arquivos quando aplicável.
- Frescor é calculado pelo ciclo mais recente do bloco, independentemente do artefato.
- Ausência, divergência e ciclo obsoleto persistem `blocked`; o resume não reprocessa silenciosamente.
- `record_workflow_event` aceita apenas eventos de ciclo/revisão/falha bloqueados por estado; conclusões exigem APIs específicas.
- `record_workflow_event` rejeita `cycle_started` genérico após aprovação do ciclo, preservando `resume_round()` em `complete`.
- B7 é seleção humana sem aprovação de revisor; `workflow-human-complete` grava `human_completed` e libera B8.

## Verificação

`python3.12 -m pytest -q`: 178 passed, 40 subtests passed.

Também passaram `python3.12 -m compileall -q src tests`, `git diff --check` e `./contentctl --help`. O smoke manual em repositório temporário confirmou bloqueio do artefato e ausência do valor sensível no payload persistido.
