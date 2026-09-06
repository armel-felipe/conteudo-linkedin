# Roadmap

Ações futuras com status `[ ]` pendente / `[x]` feito / `[~]` parcialmente validado / `[!]` bloqueado.

- [ ] Configurar X na last30days (cookies do browser — grátis)
- [ ] Adicionar web key (Brave grátis) para elevar qualidade de imprensa/relatórios
- [ ] Scripts Python (scoring, cluster) quando o fluxo manual estabilizar
- [ ] Logs de execução
- [ ] Automação recorrente (Fase 6 da spec)
- [ ] Ajuste periódico das frentes conforme métricas de engajamento/posicionamento

## Contratos e estado atual

- [~] Lote editorial com fila congelada, checkpoints, retomada, eventos append-only e bloqueio individual (`run-editorial-batch`)
- [~] Gauntlet com executor/revisor isolados, até cinco ciclos, `coverage >= 0.99`, critérios `>=9/10` e `hard_failures` fail-closed (`gauntlet-loop`)
- [x] Brief com fontes e conexão do autor; post com duas passagens de `escrita-humana` e aprovação humana
- [~] Contrato de rota `mcp_chrome_devtools` → `playwright_fallback` para localizar e inspecionar uma sessão LinkedIn; execução browser-real não comprovada nesta rodada

## Fila de remediação sequencial

Cada item só começa depois da aprovação do anterior pelo Loop Gauntlet. O gate exige `coverage >= 0.99`, nenhum hard failure e nenhuma questão crítica, importante ou alta em aberto.

1. [x] Núcleo do Gauntlet: boundaries de filesystem, estado terminal e fail-closed.
2. [x] Batch editorial: seleção, idempotência, paths, eventos, métricas e retomada.
3. [x] Integração/documentação: schemas, `result_path`, critérios e eventos válidos.
4. [x] Browser: pacote Playwright, conexão CDP, target LinkedIn e fallback visual.
5. [ ] Revisão final dos novos findings do batch:
   - [x] rejeitar `--topics 0`, seleção vazia e IDs duplicados;
   - [x] rejeitar seleção divergente de manifesto congelado;
   - [x] recuperar ou bloquear intents parciais sem sobrescrever estado;
    - [x] manter `completed` inconsistente em falha fechada;
    - [x] rejeitar valores semânticos de falha no registro de timestamp;
    - [x] tratar estado terminal sem stages restantes sem `StopIteration`.
   - validar o tipo raiz de `receipt` antes de usar operações de conjunto, evitando `TypeError` com entrada malformada.

O item 5 é o próximo passo. O agendamento só será considerado operacionalmente concluído depois da validação da publicação existente e dos cenários não mutantes restantes.

O agendamento não faz parte deste fluxo documental. Ele permanece separado no plano de publicação do LinkedIn e só ocorre após aprovação humana.

## Verificação manual de agendamento

Matriz não sensível da Task 3. Cenários mutantes só foram executados quando havia uma publicação existente e autorização explícita.

| Caso | Resultado esperado | Status |
| --- | --- | --- |
| new schedule with different date and time | data e horário explícitos aparecem no resumo antes de Avançar | not_run: criação não executada por segurança |
| new schedule for today with explicit date and time | data de hoje e horário explícitos aparecem no resumo | not_run: agendamento não executado por segurança |
| reschedule existing post with same time and different date | usar `... → Alterar agenda`, selecionar data e horário novamente e confirmar na lista | not_run: nenhuma ação browser-real executada |
| wrong summary detected before Avançar | summary divergence blocks Avançar; não agendar | simulated: contrato/teste |
| scheduled post missing from the scheduled list | confirmation/list absence blocks registration; não registrar timestamp | simulated: contrato/teste |

Regra adicional: never duplicate. Em qualquer falha de confirmação ou de presença na lista, interromper o fluxo e não criar uma segunda publicação.

O registro de timestamp usa um gate explícito: flags de confirmação são booleanos estritos, o receipt e o resumo são válidos, os timestamps solicitado e exibido coincidem, e nenhum estado de falha (`not_run`, `simulated`, `blocked` ou falha semântica) pode ser convertido em aprovação.

### Smoke test MCP Chrome DevTools / Playwright fallback

- [~] A rota contratual exige MCP Chrome DevTools primeiro e Playwright apenas como `playwright_fallback`.
- [ ] Nenhuma execução browser-real foi comprovada nesta rodada; não há evidência suficiente para afirmar descoberta de sessão.
- [x] Nenhuma ação de clique, preenchimento, publicação ou agendamento foi executada.
- A confirmação visual por screenshot ocorre somente depois das duas rotas de controle; não foi necessária nesta rodada.
- O motivo registrado para o estado `stop` é a ausência de execução browser-real comprovada.

### Receipt estruturada

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

## Histórico da verificação manual

- `evidence_status` agora separa rigorosamente `real_non_destructive`, `real_existing_post`, `simulated` e `not_run`.
- O protocolo browser dry-run seleciona data, seleciona novamente o horário, confirma o resumo e bloqueia antes de `Avançar`.
- Os cinco cenários acima foram classificados sem alegar evidência browser-real; criação, publicação, agendamento, exclusão e alteração não foram executados por segurança.
- O caminho da publicação existente `... → Alterar agenda` não foi executado nesta rodada; nenhum timestamp real foi confirmado ou alterado.
