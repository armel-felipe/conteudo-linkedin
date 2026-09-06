# Task 3 Report: verificação de agendamento

## Status

BLOCKED conforme opção B: o contrato e o protocolo seguro da rodada 5 passam nos
testes automatizados, mas os cinco cenários não têm evidência browser-real.
Nenhuma ação foi executada no LinkedIn.

- SPEC: BLOCKED pela cobertura real ausente.
- QUALITY: BLOCKED para aprovação final; os gates automatizados passam, mas a
  preservação do timestamp existente não foi demonstrada por execução real.

## Receipt estruturada

```yaml
evidence_status: simulated
route: browser_cdp
fallback: native
requested_timestamp: ""
displayed_timestamp: ""
date_selected: not_run
time_selected: not_run
summary: not_run
preview: not_run
confirmation: not_run
scheduled_list: not_run
timestamp_registered: not_run
duplicate_created: false
```

O receipt acima é de contrato/teste (`simulated`), não de browser-real.
Os estados permitidos e distintos são `real_non_destructive`,
`real_existing_post`, `simulated` e `not_run`; esta rodada usou somente os
dois últimos.

## Casos executados

- `reschedule existing post with same time and different date`: `not_run`; não confirmar `... → Alterar agenda` para preservar a agenda correta.
- `new schedule with different date and time`: `not_run`; criação/agendamento não foram executados por segurança.
- `new schedule for today with explicit date and time`: `not_run`; criação/agendamento não foram executados por segurança.
- `wrong summary detected before Avançar`: `simulated`; o contrato bloqueia `Avançar`.
- `scheduled post missing from the scheduled list`: `simulated`; o contrato bloqueia o registro.

## Failure gates

- Resumo divergente do timestamp solicitado: bloquear Avançar.
- Confirmação ausente: bloquear registro local.
- Item ausente da lista de Publicações agendadas: bloquear registro local.
- Falha em qualquer verificação: não tentar corrigir criando uma duplicata.

## Verification

- A matriz não sensível foi adicionada em `docs/roadmap.md`.
- O teste puro de matriz/receipt foi adicionado em `tests/test_scheduling_skill.py`.

## Rodada 3

- `validate_receipt()` agora exige timestamps iguais, route/fallback em allowlist, gates `pass`, ausência de duplicata e rejeição de termos sensíveis em valores textuais.
- `validate_reschedule_events()` agora exige a sequência completa até `timestamp_registered` e rejeita fluxo parcial, `new_composer` e duplicatas.
- Foram adicionados testes para divergência, campo ausente, gate falho, route/fallback inválidos, dados sensíveis e sequência parcial.
- Evidência manual permanece a mesma: reagendamento real da publicação existente; os demais casos continuam identificados como simulações não destrutivas.

## Rodada 4

- `validate_receipt()` exige `evidence_status` em allowlist e impede receipts dry-run de alegarem confirmação, presença na lista ou timestamp registrado.
- `validate_dry_run_events()` exige seleção de data, seleção de horário, resumo confirmado e `blocked_before_advance`; rejeita eventos mutantes ou de conclusão.
- A rodada 4 não executou criação, publicação, agendamento, exclusão ou alteração de publicação por segurança. O caminho existente `... → Alterar agenda` também não foi confirmado.

## Rodada 5

- Nenhum dos cinco cenários tem evidência de execução real no browser nesta rodada; esse é o gap dos cinco cenários reais.
- `new schedule with different date and time`: `not_run`.
- `new schedule for today with explicit date and time`: `not_run`.
- `reschedule existing post with same time and different date`: `not_run`; o agendamento existente foi preservado e o timestamp existente não foi alterado.
- `wrong summary detected before Avançar`: `simulated`; contrato/teste, sem confirmação real.
- `scheduled post missing from the scheduled list`: `simulated`; contrato/teste, sem confirmação real.
- O dry-run termina em `blocked_before_advance` e não pode ser convertido em `confirmation`, `scheduled_list` ou `timestamp_registered`; esses campos permanecem `not_run`.
- O receipt permanece honesto: somente evidência registrada pode usar estado real; cenários não executados permanecem `not_run`.
