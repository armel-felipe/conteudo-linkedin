# Task 1 Report — Contrato central de rota de navegador

Status: DONE_WITH_CONCERNS

## Files

- `docs/browser-route-contract.md`
- `tests/test_browser_route_contract.py`

## Implementation

- Defined the exact normative sequence `MCP Chrome DevTools → Playwright (fallback) → stop`.
- Defined `mcp_chrome_devtools`, `playwright_fallback`, `ambiguous_mutation` and `fail_closed`.
- Restricted fallback to only before a mutation is confirmed.
- Required effective-route and state-verification records for every operation.
- Added separate rules for read/inspect operations and publish/schedule/reschedule/delete mutations.
- Required fail-closed behavior for ambiguous mutations and prohibited opening a new composer.
- Expanded the contract tests for fallback boundaries, ambiguous mutations, state verification, fail-closed behavior, route records, and separate read/mutation rules.
- Tests read the contract with `encoding="utf-8"`.

## Tests

- Initial review regression check: `python3 -m pytest tests/test_browser_route_contract.py -q`
  - Result: FAIL, 2 failed and 4 passed; it exposed the missing literal Unicode route sequence and the exact fallback-boundary wording.
- Final check: `python3 -m pytest tests/test_browser_route_contract.py -q`
  - Result: PASS, 6 passed.

## Commit

- Review correction commit created after the final test run.

## Concerns

- The pre-existing `.gitignore` failure was not corrected or modified.
- The report preserves the concern about the unrelated `.gitignore` failure and records only the focused Task 1 contract test result requested for this correction.
