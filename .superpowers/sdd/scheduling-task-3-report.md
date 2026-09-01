# Task 3 Report: verificação de agendamento

## Status

PASS para a evidência real fornecida nesta sessão. A publicação existente foi reagendada pelo caminho `... → Alterar agenda`, com re-seleção explícita de data e horário.

## Receipt estruturada

```yaml
route: browser_cdp
fallback: native
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

Playwright não estava disponível no runtime. Browser/CDP foi a rota real usada, com visão nativa bem-sucedida. Nenhuma publicação nova foi criada, publicada ou agendada.

## Casos executados

- `reschedule existing post with same time and different date`: executado realmente; a publicação existente seguiu `... → Alterar agenda`.
- `new schedule with different date and time`: simulado de forma não destrutiva.
- `new schedule for today with explicit date and time`: simulado de forma não destrutiva.
- `wrong summary detected before Avançar`: simulado de forma não destrutiva; bloqueia Avançar.
- `scheduled post missing from the scheduled list`: simulado de forma não destrutiva; bloqueia o registro.

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
