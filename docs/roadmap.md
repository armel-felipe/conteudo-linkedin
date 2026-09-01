# Roadmap

Ações futuras com status `[ ]` pendente / `[x]` feito.

- [ ] Configurar X na last30days (cookies do browser — grátis)
- [ ] Adicionar web key (Brave grátis) para elevar qualidade de imprensa/relatórios
- [ ] Scripts Python (scoring, cluster) quando o fluxo manual estabilizar
- [ ] Logs de execução
- [ ] Automação recorrente (Fase 6 da spec)
- [ ] Ajuste periódico das frentes conforme métricas de engajamento/posicionamento

## Contratos já aprovados

- [x] Lote editorial com fila congelada, checkpoints, retomada, eventos append-only e bloqueio individual (`run-editorial-batch`)
- [x] Gauntlet com executor/revisor isolados, até cinco ciclos, `coverage >= 0.99`, critérios `>=9/10` e `hard_failures` fail-closed (`gauntlet-loop`)
- [x] Brief com fontes e conexão do autor; post com duas passagens de `escrita-humana` e aprovação humana

O agendamento não faz parte deste fluxo documental. Ele permanece separado no plano de publicação do LinkedIn e só ocorre após aprovação humana.

## Verificação manual de agendamento

Matriz não sensível da Task 3. Na rodada 4, nenhum cenário mutante foi executado no browser.

| Caso | Resultado esperado | Status |
| --- | --- | --- |
| new schedule with different date and time | data e horário explícitos aparecem no resumo antes de Avançar | not_run: criação não executada por segurança |
| new schedule for today with explicit date and time | data de hoje e horário explícitos aparecem no resumo | not_run: agendamento não executado por segurança |
| reschedule existing post with same time and different date | inspecionar `... → Alterar agenda`, sem confirmar segunda mudança | not_run: alteração não executada por segurança |
| wrong summary detected before Avançar | summary divergence blocks Avançar; não agendar | simulated: contrato/teste |
| scheduled post missing from the scheduled list | confirmation/list absence blocks registration; não registrar timestamp | simulated: contrato/teste |

Regra adicional: never duplicate. Em qualquer falha de confirmação ou de presença na lista, interromper o fluxo e não criar uma segunda publicação.

### Receipt estruturada

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

## Rodada 4

- `evidence_status` agora separa rigorosamente `real_non_destructive`, `real_existing_post`, `simulated` e `not_run`.
- O protocolo browser dry-run seleciona data, seleciona novamente o horário, confirma o resumo e bloqueia antes de `Avançar`.
- Os cinco cenários acima foram classificados sem alegar evidência browser-real; criação, publicação, agendamento, exclusão e alteração não foram executados por segurança.
- O caminho da publicação existente `... → Alterar agenda` não foi confirmado para preservar o agendamento correto.
