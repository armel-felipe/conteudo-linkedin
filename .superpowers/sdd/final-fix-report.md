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

## Correções deste review

- Exceções e retornos MCP ambíguos preservam estado observado, terminam em
  `ambiguous_mutation`/`stop` e não constroem nem executam Playwright.
- `main` aceita adapter MCP ou factory injetados; o default registra
  `mcp_adapter_unconfigured` e não contém credenciais.
- `can_register_timestamp` aceita somente `real_existing_post`, exige gates pós-
  ação completos e compara os timestamps recebidos com os valores do receipt.
- O filtro de dados sensíveis percorre recursivamente dicionários, chaves,
  listas, tuplas e conjuntos.
- A cobertura documental verifica regras comportamentais de mutação, incluindo
  `fail_closed`, não repetição, não avanço e ausência de duplicata.

## Verificação desta correção

- `npm test`: 21 passed.
- `python3 -m pytest tests/test_scheduling_skill.py tests/test_browser_route_contract.py tests/test_browser_route_documentation.py -q`: 105 passed.
- `python3 -m pytest tests -q`: 265 passed, 1 failed em
  `tests/test_run_contracts.py::test_runtime_runs_are_ignored_but_keep_file_is_tracked`,
  que exige `runs/*` em `.gitignore`; `.gitignore` foi preservado.
- `git diff --check`: passou.
