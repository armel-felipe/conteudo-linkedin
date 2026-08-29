# Whole-Branch Review Report

## Status

Os sete achados da revisão whole-branch e os quatro achados de follow-up foram
corrigidos no orquestrador híbrido.

## Correções

- Artefatos e eventos bloqueiam e redigem atribuições com formato de credencial para `API_KEY`, `TOKEN`, `CT0`, `AUTH_TOKEN` e `PASSWORD`.
- B2 usa seleção opaca de pilar aprovado, sem exigir arquivo; B1/B3+ continuam com arquivos quando aplicável.
- Frescor é calculado pelo ciclo mais recente do bloco, independentemente do artefato.
- Ausência, divergência e ciclo obsoleto persistem `blocked`; o resume não reprocessa silenciosamente.
- `record_workflow_event` aceita apenas eventos de ciclo/revisão/falha bloqueados por estado; conclusões exigem APIs específicas.
- `record_workflow_event` rejeita `cycle_started` genérico após aprovação do ciclo, preservando `resume_round()` em `complete`.
- `record_review` rejeita qualquer nova review após aprovação no mesmo ciclo; `resume_round()` não regride para feedback ou novo ciclo.
- `record_workflow_event` rejeita reinício quando o ciclo já tem qualquer receipt de review, inclusive feedback.
- B2 identifica seleção de pilar pelo contrato do bloco, aceitando nomes aprovados com `/` e `\\`; blocos de arquivo continuam validando artefatos.
- B7 é seleção humana sem aprovação de revisor; `workflow-human-complete` grava `human_completed` e libera B8.
- Os executores B6, B8, B10 e B11 declaram saída obrigatória somente em JSON com `artifact_path` e `cycle`, preservando seus contratos editoriais.
- Falhas de resolução, existência, leitura ou decodificação de artefato são convertidas em bloqueio genérico; `record_review` e `complete_block` persistem o evento sem vazar conteúdo e `resume_round()` permanece bloqueado.
- A cobertura de aceitação inclui contratos dos executores e bloqueio persistido para artefatos ilegíveis.
- `start_block_cycle` rejeita qualquer novo ciclo após o último estado `blocked` ou `failed`; a recuperação exige intervenção explícita separada.
- `Database.record_workflow_event('cycle_started')` também rejeita blocos cujo último estado é `blocked` ou `failed`; nenhum dos dois caminhos públicos reabre um bloco terminal.
- Um ciclo com `review_approved`, `cycle_started` aprovado ou `block_completed`/`human_completed` não pode ser substituído por outro ciclo.
- Feedback repetido persiste `blocked` antes de retornar o erro, e `resume_round()` permanece em `blocked` sem reprocessamento.
- `record_human_completion` valida o ciclo B7 mais recente por `round_id`/`block`, exige correspondência explícita do artefato e persiste bloqueio para artefato ausente ou ilegível.
- `record_review` e `record_workflow_event` rejeitam toda mutação após `blocked`/`failed`, incluindo aprovação genérica; falhas de parsing não acrescentam eventos terminais.
- `_persist_blocked` é idempotente e preserva estados `blocked`, `failed`, `block_completed` e `human_completed`, evitando regressão após conclusão.
- A detecção de artefatos cobre atribuições `NAME=value`, chaves JSON/YAML de `api_key`, `token` e `password`, e `Authorization: Bearer`; valores são redigidos antes de qualquer persistência e a aprovação é bloqueada.

## Verificação

`python3.12 -m pytest -q`: 198 passed, 53 subtests passed.

Também passaram `python3.12 -m compileall -q src tests`, `git diff --check` e `./contentctl --help`. O smoke manual em repositório temporário confirmou bloqueio do artefato e ausência do valor sensível no payload persistido.
