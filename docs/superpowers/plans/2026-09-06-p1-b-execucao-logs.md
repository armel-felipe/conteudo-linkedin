# P1-B — Logs estruturados de execução: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persistir eventos JSONL sanitizados para reconstruir execuções do pipeline sem expor segredos ou alterar ações editoriais.

**Architecture:** Um contrato de evento compartilhado será implementado por um logger Python e um adapter Node usado pelo smoke test de navegador. Ambos escrevem o mesmo envelope JSONL, com `run_id`, etapa, evento, rota, estado, duração, receipt e motivo. A integração inicial cobre navegador/receipts; não executa ações.

**Tech Stack:** Python 3.12+ standard library, Node.js CommonJS standard library, JSONL, pytest, Node test runner.

## Global Constraints

- Criar um `run_id` por execução.
- Emitir `started` no início e `completed`, `blocked` ou `fallback` no fim.
- Registrar MCP Chrome DevTools antes de Playwright fallback.
- Sanitizar recursivamente `AUTH_TOKEN`, `CT0`, cookies, API keys, authorization headers, senhas, identificadores de conta e conteúdo privado.
- Não registrar sucesso sem receipt/estado correspondente quando a etapa exigir confirmação.
- Os arquivos em `runs/` permanecem fora do Git; somente fixtures sanitizadas e testes podem ser versionados.
- O logger não executa navegador, publica, agenda ou cria posts.

---

### Task 1: Criar logger Python e contrato de sanitização

**Files:**
- Create: `execution_log.py`
- Test: `tests/test_execution_log.py`

**Interfaces:**
- `sanitize_log_value(value) -> JSON-compatible value`
- `ExecutionLogger(path, run_id=None, clock=None)`
- `ExecutionLogger.emit(stage, event, *, route_attempted=(), effective_route=None, state=None, duration_ms=None, receipt_ref=None, reason=None, details=None) -> dict`
- `ExecutionLogger.start(stage, **kwargs) -> dict`
- `ExecutionLogger.finish(stage, event, **kwargs) -> dict`

- [ ] **Step 1: Write failing tests**

```python
import json
from execution_log import ExecutionLogger, sanitize_log_value


def test_sanitizes_nested_secrets_and_writes_jsonl(tmp_path):
    path = tmp_path / "run.jsonl"
    logger = ExecutionLogger(path, run_id="run-1", clock=lambda: "2026-09-06T00:00:00Z")
    event = logger.emit(
        "browser", "fallback", route_attempted=["mcp_chrome_devtools", "playwright_fallback"],
        effective_route="playwright_fallback", state="confirmed", duration_ms=12,
        reason="mcp_unavailable", details={"headers": {"Authorization": "Bearer secret"}, "nested": [{"api_key": "key"}]},
    )
    saved = json.loads(path.read_text().strip())
    assert event == saved
    assert saved["run_id"] == "run-1"
    assert saved["route_attempted"] == ["mcp_chrome_devtools", "playwright_fallback"]
    assert saved["details"]["headers"]["Authorization"] == "[REDACTED]"
    assert saved["details"]["nested"][0]["api_key"] == "[REDACTED]"


def test_start_and_finish_emit_required_lifecycle_events(tmp_path):
    logger = ExecutionLogger(tmp_path / "run.jsonl", run_id="run-2", clock=lambda: "now")
    logger.start("research")
    logger.finish("research", "blocked", state="unconfigured", reason="source_unavailable")
    events = [json.loads(line) for line in (tmp_path / "run.jsonl").read_text().splitlines()]
    assert [event["event"] for event in events] == ["started", "blocked"]
```

- [ ] **Step 2: Run tests and verify failure**

Run: `python3 -m pytest tests/test_execution_log.py -q`

Expected: FAIL because `execution_log.py` does not exist.

- [ ] **Step 3: Implement the minimal logger**

Use only the standard library. Normalize tuples/sets to lists, preserve JSON scalar values, recursively sanitize dict keys and values, create the parent directory, append one compact JSON object per line, and flush after every event. Generate a UUID when `run_id` is omitted. Use the injected `clock` in tests and UTC ISO-8601 in production.

- [ ] **Step 4: Run focused tests**

Run: `python3 -m pytest tests/test_execution_log.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add execution_log.py tests/test_execution_log.py
git commit -m "feat: add sanitized execution logger"
```

---

### Task 2: Adicionar adapter Node e integrar o smoke test MCP-first

**Files:**
- Create: `scripts/execution_log.js`
- Modify: `scripts/linkedin_browser_check.js`
- Test: `tests/linkedin_browser_check.test.js`

**Interfaces:**
- `createExecutionLogger(filePath, { runId, clock }) -> { emit, start, finish }`
- `runBrowserCheck({ mcpAdapterFactory, playwrightAdapterFactory, logPath, runId }) -> Promise<result>` inclui `log_path` e `events` sanitizados no retorno.

- [ ] **Step 1: Write failing tests**

```javascript
test('logs MCP-first browser execution without calling Playwright', async () => {
  const result = await runBrowserCheck({
    mcpAdapterFactory: async () => ({ inspect: async () => ({ ok: true, report: { visual_state: 'public_page' } }) }),
    playwrightAdapterFactory: async () => { throw new Error('must not be called'); },
    logPath: path.join(os.tmpdir(), `browser-${Date.now()}.jsonl`),
    runId: 'browser-run-1',
  });
  assert.equal(result.effective_route, 'mcp_chrome_devtools');
  assert.equal(result.events[0].event, 'started');
  assert.equal(result.events.at(-1).event, 'completed');
});

test('logs fallback reason and never logs adapter secrets', async () => {
  const result = await runBrowserCheck({
    mcpAdapterFactory: async () => ({ inspect: async () => ({ ok: false, reason: 'mcp_unavailable', details: { api_key: 'secret' } }) }),
    playwrightAdapterFactory: async () => ({ inspect: async () => ({ ok: true, report: { visual_state: 'ok' } }) }),
    logPath: path.join(os.tmpdir(), `browser-${Date.now()}.jsonl`),
    runId: 'browser-run-2',
  });
  assert.equal(result.effective_route, 'playwright_fallback');
  assert.equal(result.route_reasons.mcp_chrome_devtools, 'mcp_unavailable');
  assert.equal(JSON.stringify(result.events).includes('secret'), false);
});
```

- [ ] **Step 2: Run tests to verify failure**

Run: `node --test tests/linkedin_browser_check.test.js`

Expected: FAIL because the execution result does not yet persist lifecycle events.

- [ ] **Step 3: Implement Node JSONL adapter and integration**

Implement the same envelope and redaction rules as Python. In `runBrowserCheck`, emit `started` before the MCP factory, `fallback` only after a safe pre-mutation MCP failure, `completed` for a confirmed route, and `blocked` for stop/ambiguous outcomes. Keep the existing MCP-first decision policy and never log raw adapter results.

- [ ] **Step 4: Run focused tests**

Run: `node --test tests/linkedin_browser_check.test.js`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/execution_log.js scripts/linkedin_browser_check.js tests/linkedin_browser_check.test.js
git commit -m "feat: log MCP-first browser executions"
```

---

### Task 3: Integrar receipts Python e documentar o formato

**Files:**
- Modify: `scheduling_contract.py`
- Modify: `docs/browser-route-contract.md`
- Modify: `docs/roadmap.md`
- Test: `tests/test_execution_log.py`
- Test: `tests/test_browser_route_documentation.py`

**Interfaces:**
- Consumes: `ExecutionLogger` da Task 1 e receipts existentes.
- Produces: eventos `receipt_validated`, `blocked` ou `completed` sem conteúdo privado.

- [ ] **Step 1: Write failing integration tests**

```python
def test_receipt_validation_can_emit_sanitized_log(tmp_path):
    logger = ExecutionLogger(tmp_path / "run.jsonl", run_id="receipt-1", clock=lambda: "now")
    logger.start("scheduling", receipt_ref="receipt-1")
    logger.finish("scheduling", "blocked", state="ambiguous_mutation", receipt_ref="receipt-1", reason="fail_closed")
    event = json.loads((tmp_path / "run.jsonl").read_text().splitlines()[-1])
    assert event["event"] == "blocked"
    assert event["state"] == "ambiguous_mutation"
    assert "cookie" not in json.dumps(event).lower()
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `python3 -m pytest tests/test_execution_log.py tests/test_browser_route_documentation.py -q`

Expected: FAIL until the integration and documentation examples use the logger contract.

- [ ] **Step 3: Integrate and document**

Add logger calls at receipt validation boundaries without changing validation decisions. Document the JSONL schema, lifecycle event meanings, canonical routes, sanitization guarantees and `runs/` exclusion. Update the roadmap P1-B line from pending only after the tests and full suite pass.

- [ ] **Step 4: Run all verification**

Run:

```bash
node --test tests/*.test.js
python3 -m pytest tests -q
python3 -m compileall -q *.py
git diff --check
```

Expected: all tests pass, compileall succeeds, and diff check has no output.

- [ ] **Step 5: Inspect and commit**

Confirm no `runs/` output, `.env`, token, cookie, authorization header or private page content is staged. Then run:

```bash
git add execution_log.py scripts/execution_log.js scripts/linkedin_browser_check.js scheduling_contract.py docs/browser-route-contract.md docs/roadmap.md tests
git commit -m "feat: add structured pipeline execution logs"
```

## Plan self-review

- Event envelope and lifecycle: Tasks 1–2.
- MCP-first route evidence and fallback reason: Task 2.
- Recursive sanitization: Tasks 1–2.
- Receipt integration and fail-closed states: Task 3.
- `runs/` exclusion and no secrets: Tasks 1 and 3.
- Tests and full verification: all tasks, with final suite in Task 3.
