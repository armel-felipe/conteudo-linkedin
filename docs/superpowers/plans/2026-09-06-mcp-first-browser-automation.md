# MCP-First Browser Automation Implementation Plan

> **Status documental:** obsoleto; substituído pela rota visual-first em `docs/browser-route-contract.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer todo o pipeline agentico tentar MCP Chrome DevTools antes de Playwright, usando Playwright apenas como fallback explícito e seguro.

**Architecture:** Um contrato textual e uma política pura de decisão definirão a ordem das rotas e as condições de fallback. As skills e documentos do pipeline consumirão o mesmo vocabulário; o smoke test exporá a política para validação sem executar mutações reais.

**Tech Stack:** Markdown, Node.js CommonJS, Node test runner, Python/pytest já usado pelo projeto, OpenWork MCP Chrome DevTools e Playwright/CDP como fallback.

## Global Constraints

- MCP Chrome DevTools é sempre a primeira tentativa para operações de navegador.
- Playwright só pode ser usado quando o MCP estiver indisponível, sem a capability necessária ou bloqueado por falha técnica antes de uma mutação confirmada.
- Resultado ambíguo após possível mutação exige verificação e fail-closed; nunca repetir cegamente.
- Reagendamento deve alterar a publicação existente; nunca abrir novo composer para corrigir horário.
- Timestamp local só pode ser persistido depois da confirmação pós-ação.
- Não armazenar cookies, credenciais, tokens, identificadores de conta ou conteúdo privado de sessão.
- O lote editorial continua sem publicação ou agendamento automático.

---

### Task 1: Criar o contrato central de rota de navegador

**Files:**
- Create: `docs/browser-route-contract.md`
- Test: `tests/test_browser_route_contract.py`

**Interfaces:**
- Produces: vocabulário normativo para qualquer skill/script que use navegador: `mcp_chrome_devtools`, `playwright_fallback`, `ambiguous_mutation`, `fail_closed`.

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


def test_browser_route_contract_declares_mcp_first_and_safe_fallback():
    text = Path("docs/browser-route-contract.md").read_text()
    assert text.index("MCP Chrome DevTools") < text.index("Playwright")
    for phrase in (
        "mcp_chrome_devtools",
        "playwright_fallback",
        "ambiguous_mutation",
        "fail-closed",
        "nunca abrir novo composer",
    ):
        assert phrase in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_browser_route_contract.py -q`

Expected: FAIL because `docs/browser-route-contract.md` does not exist.

- [ ] **Step 3: Write the contract**

Document the exact sequence below and define the permitted fallback boundary:

```text
MCP Chrome DevTools → Playwright (fallback) → stop
```

State that fallback is permitted only before a mutation is confirmed, that all operations record the effective route, and that ambiguous mutation results require state verification and fail-closed behavior. Include separate rules for read/inspect operations and publish/schedule/reschedule/delete operations.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_browser_route_contract.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/browser-route-contract.md tests/test_browser_route_contract.py
git commit -m "docs: define browser route contract"
```

---

### Task 2: Implement deterministic route selection in the browser smoke module

**Files:**
- Modify: `scripts/linkedin_browser_check.js`
- Test: `tests/linkedin_browser_check.test.js`

**Interfaces:**
- Produces: `browserRouteOrder()`, `resolveBrowserRoute({ mcpAvailable, capabilityAvailable, mutationConfirmed, errorBeforeMutation })` and `visualFallbackOrder()`.
- `resolveBrowserRoute` returns `{ route, reason }`, where `route` is `mcp_chrome_devtools`, `playwright_fallback` or `stop`.

- [ ] **Step 1: Write the failing tests**

```javascript
const {
  browserRouteOrder,
  resolveBrowserRoute,
} = require('../scripts/linkedin_browser_check.js');

test('declares MCP Chrome DevTools before Playwright', () => {
  assert.deepEqual(browserRouteOrder(), [
    'mcp_chrome_devtools',
    'playwright_fallback',
    'stop',
  ]);
});

test('uses Playwright fallback when MCP is unavailable before mutation', () => {
  assert.deepEqual(resolveBrowserRoute({
    mcpAvailable: false,
    capabilityAvailable: false,
    mutationConfirmed: false,
    errorBeforeMutation: true,
  }), {
    route: 'playwright_fallback',
    reason: 'mcp_unavailable',
  });
});

test('stops after an ambiguous possible mutation', () => {
  assert.deepEqual(resolveBrowserRoute({
    mcpAvailable: true,
    capabilityAvailable: true,
    mutationConfirmed: false,
    errorBeforeMutation: false,
  }), {
    route: 'stop',
    reason: 'ambiguous_mutation',
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/linkedin_browser_check.test.js`

Expected: FAIL because the new route-policy exports do not exist and the old visual order still starts with Playwright.

- [ ] **Step 3: Implement the pure policy**

Add the following behavior without connecting to or mutating a browser:

```javascript
function browserRouteOrder() {
  return ['mcp_chrome_devtools', 'playwright_fallback', 'stop'];
}

function resolveBrowserRoute({
  mcpAvailable,
  capabilityAvailable,
  mutationConfirmed,
  errorBeforeMutation,
}) {
  if (mcpAvailable && capabilityAvailable) {
    return { route: 'mcp_chrome_devtools', reason: 'mcp_ready' };
  }
  if (!mutationConfirmed && errorBeforeMutation) {
    return {
      route: 'playwright_fallback',
      reason: mcpAvailable ? 'capability_unavailable' : 'mcp_unavailable',
    };
  }
  return { route: 'stop', reason: 'ambiguous_mutation' };
}
```

Change `visualFallbackOrder()` so it describes the post-route visual fallback only: `screenshot+nativa`, `image-analyzer:native_failed`, `stop`. Export both new functions. Keep `inspectPage` non-mutating.

- [ ] **Step 4: Update the remaining route-policy assertions**

Replace tests that assert Playwright-first with assertions that MCP precedes Playwright and that visual fallback is downstream of the selected browser route.

- [ ] **Step 5: Run tests to verify they pass**

Run: `node --test tests/linkedin_browser_check.test.js`

Expected: PASS with all existing target-selection and screenshot-safety tests retained.

- [ ] **Step 6: Commit**

```bash
git add scripts/linkedin_browser_check.js tests/linkedin_browser_check.test.js
git commit -m "test: enforce MCP-first browser routing"
```

---

### Task 3: Update pipeline skills and operational documentation

**Files:**
- Modify: `.agents/skills/publicar-linkedin/SKILL.md`
- Modify: `README.md`
- Modify: `mapa.md`
- Modify: `docs/superpowers/plans/2026-09-01-linkedin-scheduling.md`
- Modify: `docs/superpowers/specs/2026-09-01-editorial-batch-gauntlet-design.md`
- Modify: `docs/roadmap.md`
- Test: `tests/test_browser_route_documentation.py`

**Interfaces:**
- Consumes: `docs/browser-route-contract.md`.
- Produces: consistent instructions for all browser-using pipeline stages.

- [ ] **Step 1: Write the failing documentation test**

```python
from pathlib import Path


FILES = (
    Path(".agents/skills/publicar-linkedin/SKILL.md"),
    Path("README.md"),
    Path("mapa.md"),
    Path("docs/superpowers/plans/2026-09-01-linkedin-scheduling.md"),
    Path("docs/superpowers/specs/2026-09-01-editorial-batch-gauntlet-design.md"),
    Path("docs/roadmap.md"),
)


def test_browser_docs_use_mcp_before_playwright():
    for path in FILES:
        text = path.read_text()
        assert "MCP Chrome DevTools" in text, path
        assert text.index("MCP Chrome DevTools") < text.index("Playwright"), path
        assert "playwright_fallback" in text or "fallback" in text.lower(), path


def test_docs_retain_critical_linkedin_safety_rules():
    text = Path(".agents/skills/publicar-linkedin/SKILL.md").read_text()
    assert "Alterar agenda" in text
    assert "Publicações agendadas" in text
    assert "novo composer" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_browser_route_documentation.py -q`

Expected: FAIL because the current documents still describe Playwright as the first route or omit MCP Chrome DevTools.

- [ ] **Step 3: Update the operational wording**

Replace every browser-route statement with the shared policy:

```text
MCP Chrome DevTools → Playwright (fallback) → screenshot + visão nativa → image-analyzer(native_failed) → stop
```

Clarify that screenshot/vision is a fallback after both browser-control routes, not a substitute for trying MCP. Add route/reason evidence requirements and repeat the fail-closed rules for mutating operations. Keep the editorial batch prohibition and LinkedIn existing-post `Alterar agenda` rule.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_browser_route_documentation.py -q`

Expected: PASS.

- [ ] **Step 5: Run repository documentation checks**

Run: `git diff --check`

Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add .agents/skills/publicar-linkedin/SKILL.md README.md mapa.md docs/superpowers/plans/2026-09-01-linkedin-scheduling.md docs/superpowers/specs/2026-09-01-editorial-batch-gauntlet-design.md docs/roadmap.md tests/test_browser_route_documentation.py
git commit -m "docs: make browser automation MCP-first"
```

---

### Task 4: Add regression coverage for mutation safety and run the full suite

**Files:**
- Modify: `tests/linkedin_browser_check.test.js`
- Modify: `tests/test_browser_route_contract.py`
- Modify: `docs/browser-route-contract.md`

**Interfaces:**
- Consumes: route policy and documentation contract from Tasks 1–3.
- Produces: regression coverage that prevents silent fallback or duplicate mutation behavior.

- [ ] **Step 1: Add failing regression cases**

Add tests asserting that:

```javascript
test('does not permit fallback after a confirmed mutation', () => {
  assert.deepEqual(resolveBrowserRoute({
    mcpAvailable: false,
    capabilityAvailable: false,
    mutationConfirmed: true,
    errorBeforeMutation: false,
  }), {
    route: 'stop',
    reason: 'ambiguous_mutation',
  });
});
```

And add a Python assertion that the contract contains both `timestamp` and `scheduled_list_confirmed` before local persistence.

- [ ] **Step 2: Run the focused tests**

Run: `node --test tests/linkedin_browser_check.test.js && python3 -m pytest tests/test_browser_route_contract.py tests/test_browser_route_documentation.py -q`

Expected: PASS after the regression behavior is represented by the policy and contract.

- [ ] **Step 3: Run the complete meaningful verification**

Run: `node --test tests/*.test.js && python3 -m pytest tests -q && git diff --check`

Expected: all Node and Python tests pass and `git diff --check` produces no output.

- [ ] **Step 4: Inspect the final diff**

Run: `git status --short && git diff --stat && git diff -- .agents/skills/publicar-linkedin/SKILL.md README.md mapa.md docs/browser-route-contract.md scripts/linkedin_browser_check.js tests`

Confirm that only intended files changed, no secrets or session data are present, and no document says Playwright is first.

- [ ] **Step 5: Commit**

```bash
git add docs/browser-route-contract.md scripts/linkedin_browser_check.js tests .agents/skills/publicar-linkedin/SKILL.md README.md mapa.md docs/superpowers/plans/2026-09-01-linkedin-scheduling.md docs/superpowers/specs/2026-09-01-editorial-batch-gauntlet-design.md docs/roadmap.md
git commit -m "feat: prioritize MCP Chrome DevTools in browser pipeline"
```

## Plan self-review

- MCP-first order: Tasks 1–3.
- Playwright fallback conditions: Tasks 1–2.
- Route evidence: Tasks 1 and 3.
- Ambiguous mutation fail-closed: Tasks 1, 2 and 4.
- Existing-post rescheduling without new composer: Task 3.
- Timestamp persistence only after confirmation: Tasks 1, 3 and 4.
- Full-pipeline documentation consistency: Task 3.
- No placeholders or unrelated editorial automation changes remain in scope.
