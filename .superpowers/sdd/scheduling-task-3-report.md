# Task 3 Report: verificação de agendamento

## Status atual

PASS para o contrato e o protocolo seguro da rodada 5; BLOCKED para evidência
browser-real. Nenhuma ação foi executada no LinkedIn.

O contrato MCP-first exige `MCP Chrome DevTools → Playwright (fallback) →
visão nativa → image-analyzer(native_failed) → stop`. O receipt
permanece honesto: somente evidência registrada pode usar estado real; cenários
não executados permanecem `not_run`.

## Receipt estruturada

```yaml
evidence_status: simulated
route: stop
fallback: none
route_attempted:
  - mcp_chrome_devtools
mcp_attempted: true
route_reasons:
  mcp_chrome_devtools: execução não realizada; receipt apenas simulado
observed_state:
  status: not_run
verification_evidence: contrato e testes locais; nenhuma evidência browser-real
post_action_confirmation: not_run
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

## Correção da revisão da Task 3

- `validate_schedule_events()` exige `mcp_chrome_devtools_attempt` antes de
  `playwright_fallback` ou de qualquer evento Playwright em fluxos mutantes.
- A rota Playwright válida registra `playwright_fallback` e preserva
  `playwright_attempt` depois da tentativa MCP; um fluxo Playwright-only é
  rejeitado.
- `validate_receipt()` exige `mcp_failure: true` e `fallback_reason` não vazio
  quando a rota efetiva é `playwright_fallback`.
- A rota primária exige `route: mcp_chrome_devtools` e `fallback: none`; relações
  entre rota e fallback são rejeitadas.
- `validate_dry_run_events()` rejeita a sequência Playwright-only e exige a
  tentativa MCP antes de qualquer evento Playwright.
- Foram adicionados testes para ordem MCP/Playwright, fluxo Playwright-only e
  consistência dos campos de fallback.

## Casos executados

- `reschedule existing post with same time and different date`: `not_run`; não
  confirmar `... → Alterar agenda` para preservar a agenda correta.
- `new schedule with different date and time`: `not_run`; criação/agendamento
  não foram executados por segurança.
- `new schedule for today with explicit date and time`: `not_run`; não executado.
- `wrong summary detected before Avançar`: `simulated`; o contrato bloqueia
  `Avançar`.
- `scheduled post missing from the scheduled list`: `simulated`; o contrato
  bloqueia o registro.

## Failure gates

- Resumo divergente do timestamp solicitado: bloquear Avançar.
- Confirmação ausente: bloquear registro local.
- Item ausente da lista de Publicações agendadas: bloquear registro local.
- Falha ou mutação ambígua: parar, sem repetir e sem criar duplicata.

## Rodada 4

- `evidence_status` permanece limitado a `real_non_destructive`,
  `real_existing_post`, `simulated` e `not_run`.
- Em qualquer divergência, não confirmar a ação nem registrar sucesso.
- O dry-run exige arquivo aprovado, conversão, tentativa MCP, rota visual,
  seleção de data e horário, resumo confirmado e `blocked_before_advance`.
- Nenhuma confirmação, presença na lista ou timestamp registrado é alegada sem
  execução correspondente.

## Rodada 5

- Nenhum dos cinco cenários reais tem evidência browser-real nesta rodada.
- Os cenários mutantes permanecem `not_run`; os dois cenários de falha são
  `simulated` e bloqueiam o avanço ou o registro.
- O dry-run termina em `blocked_before_advance`; o agendamento existente não foi
  alterado, o timestamp existente não foi alterado e nenhuma duplicata foi criada.

## Histórico preservado do checkpoint `fdce350`

O checkpoint registrava os mesmos cinco cenários como não executados ou
simulados, exigia timestamps iguais, route/fallback em allowlist, gates `pass`,
ausência de duplicata e rejeição de termos sensíveis. Também registrava que o
dry-run termina em `blocked_before_advance` e não pode alegar confirmação,
presença na lista ou timestamp registrado. Essas garantias permanecem no
contrato MCP-first e foram reforçadas com evidência de rota e estado observado.
