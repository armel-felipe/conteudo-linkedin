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
