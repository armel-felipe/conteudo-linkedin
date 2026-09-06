# Task 3 Report: verificação de agendamento

## Status

PASS para o contrato e o protocolo seguro da rodada 5; BLOCKED para evidência
browser-real. Nenhuma ação foi executada no LinkedIn.

## Receipt estruturada

```yaml
evidence_status: simulated
route: mcp_chrome_devtools
fallback: none
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

## Correção da revisão da Task 3

- `validate_schedule_events()` agora exige `mcp_chrome_devtools_attempt` antes de
  `playwright_fallback` ou de qualquer evento Playwright em fluxos mutantes.
- A rota Playwright válida registra `playwright_fallback` e preserva
  `playwright_attempt` depois da tentativa MCP; um fluxo Playwright-only é
  rejeitado.
- `validate_receipt()` exige `mcp_failure: true` e `fallback_reason` não vazio
  quando a rota efetiva é `playwright_fallback`; a combinação canônica é
  `route: playwright_fallback` e `fallback: playwright_fallback`.
- A rota primária exige `route: mcp_chrome_devtools` e `fallback: none`, sem
  campos de falha MCP; relações entre rota e fallback são rejeitadas.
- `validate_dry_run_events()` rejeita a sequência Playwright-only e exige a
  tentativa MCP antes de qualquer evento Playwright.
- Foram adicionados testes para ordem MCP/Playwright, fluxo Playwright-only e
  consistência dos campos de fallback.
- Verificação direcionada: `python3 -m pytest tests/test_scheduling_skill.py -q`
  — 74 passed.
- Verificação relacionada: `python3 -m pytest tests/test_browser_route_documentation.py tests/test_scheduling_skill.py -q`
  — 79 passed.
- Verificação completa: `python3 -m pytest tests -q` — 245 passed, 1 failed. A
  falha é preexistente e fora do escopo: `tests/test_run_contracts.py::test_runtime_runs_are_ignored_but_keep_file_is_tracked`
  espera `runs/*` em `.gitignore`; `.gitignore` não foi alterado.
- `git diff --check` — passou sem saída.

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
