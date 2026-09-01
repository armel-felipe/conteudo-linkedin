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
- [x] Gauntlet com executor/revisor isolados, até cinco ciclos, `coverage > 0.99`, critérios `>=9/10` e `hard_failures` fail-closed (`gauntlet-loop`)
- [x] Brief com fontes e conexão do autor; post com duas passagens de `escrita-humana` e aprovação humana

O agendamento não faz parte deste fluxo documental. Ele permanece separado no plano de publicação do LinkedIn e só ocorre após aprovação humana.

## Verificação manual de agendamento

Matriz não sensível da Task 3. O reagendamento foi executado realmente nesta sessão; os demais casos foram simulados de forma não destrutiva.

| Caso | Resultado esperado | Status |
| --- | --- | --- |
| new schedule with different date and time | data e horário explícitos aparecem no resumo antes de Avançar | cenário |
| new schedule for today with explicit date and time | data de hoje e horário explícitos aparecem no resumo | cenário |
| reschedule existing post with same time and different date | re-selecionar data e horário, confirmar prévia e lista | executado: real |
| wrong summary detected before Avançar | summary divergence blocks Avançar; não agendar | simulado: não destrutivo |
| scheduled post missing from the scheduled list | confirmation/list absence blocks registration; não registrar timestamp | simulado: não destrutivo |

Regra adicional: never duplicate. Em qualquer falha de confirmação ou de presença na lista, interromper o fluxo e não criar uma segunda publicação.

### Receipt estruturada

```yaml
route: browser
fallback: CDP
requested_timestamp: "01/09/2026 10:00"
displayed_timestamp: "01/09/2026 10:00"
date_selected: pass
time_selected: pass
summary: pass
preview: pass
confirmation: pass
scheduled_list: pass
duplicate_created: false
```
