# Relatório da correção final

## Findings corrigidos

- `runBrowserCheck()` preserva `mutation_confirmed` e `observed_state` quando o
  adapter Playwright retorna ambiguidade ou lança durante uma inspeção iniciada;
  esses caminhos terminam em `ambiguous_mutation` e não podem ser sucesso.
- `validate_receipt()` e `can_register_timestamp()` exigem tentativa MCP,
  histórico ordenado de rotas, motivo para cada rota, estado observado,
  evidência de verificação e confirmação pós-ação. Receipts reais exigem
  confirmação pós-ação diferente de `not_run`.
- O receipt do roadmap e o receipt do relatório usam o schema completo e YAML
  válido. A alegação de `real_existing_post` foi removida: não há prova de ação
  browser-real nesta rodada, portanto o cenário está como `not_run`.
- Os testes passaram a executar o fluxo com adapters injetados e a carregar os
  receipts documentados como YAML antes de validá-los semanticamente.

## Verificação

- `npm test`: 17 passed.
- `python3 -m pytest tests/test_scheduling_skill.py tests/test_browser_route_contract.py tests/test_browser_route_documentation.py -q`: 98 passed.
- `python3 -m pytest tests -q`: 258 passed, 1 failed em
  `tests/test_run_contracts.py::test_runtime_runs_are_ignored_but_keep_file_is_tracked`.
  A falha exige `runs/*` em `.gitignore`; `.gitignore` não foi alterado.
- `git diff --check`: passou.

## Concerns

- Não foi executada ação no LinkedIn nem foi inventada evidência browser-real.
- A falha restante da suíte completa é externa a esta correção e permanece
  explicitamente bloqueada pela instrução de preservar `.gitignore`.
