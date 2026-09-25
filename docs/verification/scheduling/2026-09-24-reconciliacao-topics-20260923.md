# Reconciliação de agendamento — topics 20260923_06 e 20260923_10

Data: 2026-09-24
Autor: humano (confirmado em sessão) + agente (registro)

## Motivo

Os posts `topic_20260923_06` e `topic_20260923_10` foram agendados no LinkedIn em
uma sessão anterior (CLI, via MCP chrome-devtools) e movidos para
`content/published/` com marker `<!-- agendado: ... -->`. Essa sessão **não
deixou receipt** em `runs/scheduling/`, diferente dos agendamentos anteriores.

Este documento registra a reconciliação de forma explícita. Ele **não é um
receipt** e não substitui a evidência de execução do Bloco 3: é o registro de
que a evidência não foi capturada e de que o estado local foi alinhado ao fato
confirmado pelo autor.

## Estado confirmado

| Topic | Arquivo | Agendado para | Status do topic |
|---|---|---|---|
| `topic_20260923_06` | `content/published/topic_20260923_06.md` | 2026-09-28 10:30 America/Sao_Paulo | `published` |
| `topic_20260923_10` | `content/published/topic_20260923_10.md` | 2026-09-25 10:00 America/Sao_Paulo | `published` |

Ambos constam em `runs/scheduling-registry.yaml` e passam em
`scheduling_registry.py --check` (sem conflito de horário ou de conteúdo, dentro
da regra de slot).

## Evidência ausente

Não existe, para nenhum dos dois:

- `receipt.yaml` nem `audit-receipt.yaml` em `runs/scheduling/`;
- screenshots da execução de agendamento;
- entrada em log JSONL de execução.

O único vestígio é o marker no arquivo e a entrada no registry — ambos derivados
do próprio marker. **Não foi criado receipt retroativo**: um receipt válido exige
`evidence_status: real_existing_post`, `scheduled_list_confirmed` e
`verification_evidence` observada, e fabricá-lo violaria a regra de
rastreabilidade do projeto.

## Ações aplicadas

- `topic_20260923_06`: status `approved` → `published`.
- `topic_20260923_10`: status `ready_for_research` → `published`.

O `_10` estava em `ready_for_research` mesmo com o post já em `published/`, o que
o deixava elegível para reprocessamento pelo Bloco 2 e risco de post duplicado.
A correção alinha o status à convenção dos demais posts publicados.

## Pendência

Se o agendamento precisar ser auditado com evidência, a verificação deve ser
refeita na lista de "Publicações agendadas" do LinkedIn e registrada como
receipt novo — não reconstruída a partir do marker.
