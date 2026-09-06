# Relatório da revisão final

## Escopo

Corrigidos os findings Critical/Important da revisão `39eefa5..d668ce7` sem
alterar `.gitignore`:

- `linkedin_browser_check.js` agora recebe um adapter MCP injetável, tenta MCP
  antes de construir Playwright e só faz fallback antes de mutação confirmada.
- O resultado persistível carrega `attempted_routes`, `effective_route`,
  `route_reasons`, `reason`, `observed_state` e o relatório observado.
- Reagendamento exige tentativa MCP, rota efetiva explícita e fallback/evidência
  coerentes quando Playwright é usado.
- Receipts aceitam `stop`, mas exigem evidência de tentativa MCP, rota tentada e
  verificação; receipts de fallback exigem falha MCP e motivo.
- Registro de timestamp não possui mais atalho booleano: exige receipt real,
  evidência pós-ação, timestamps coincidentes e todos os gates pós-ação.
- Dry-run aceita MCP-only e rejeita Playwright-only.

## Interface de teste

`runBrowserCheck({ mcpAdapter, playwrightAdapterFactory })` é a interface de
execução simulável. `mcpAdapter.inspect()` retorna `{ ok, report?, reason?,
mutation_confirmed?, observed_state? }`; o factory Playwright só é chamado após
uma falha MCP anterior à mutação. Os testes usam apenas adapters locais, sem
credenciais ou chamada MCP remota.

## Verificação

- `node --test tests/linkedin_browser_check.test.js`: 15 passed.
- `python3 -m pytest tests/test_scheduling_skill.py tests/test_browser_route_contract.py tests/test_browser_route_documentation.py -q`: 90 passed.
- `git diff --check`: passou.
- `npm test`: 15 passed.
- `python3 -m pytest tests -q`: 250 passed, 1 failed em
  `tests/test_run_contracts.py::test_runtime_runs_are_ignored_but_keep_file_is_tracked`.
  A falha é preexistente e fora do escopo: exige `runs/*` em `.gitignore`, que
  não foi alterado conforme solicitado.

## Concerns

- O adapter MCP padrão é deliberadamente não configurado neste script local;
  integração real deve fornecer o adapter pelo host OpenWork.
- A suíte completa mantém qualquer falha preexistente fora deste escopo e não
  autoriza alterar `.gitignore`.
