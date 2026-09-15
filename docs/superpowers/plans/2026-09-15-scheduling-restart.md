# Scheduling Restart Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild LinkedIn scheduling around a real visual-first browser route, persistent receipts, and local/LinkedIn reconciliation.

**Architecture:** The CUA embedded browser is the only route allowed to mutate LinkedIn. A Python CLI validates approved Markdown, creates a run receipt, records visual evidence after the scheduled list is confirmed, moves the post, and reconciles local state. Playwright is restricted to non-mutating inspection.

**Tech Stack:** Python 3.12, pytest, PyYAML, existing execution logger, CUA embedded browser for visual inspection, Node test runner.

**Spec:** User-approved QA design from 2026-09-15: visual-first scheduling, fail-closed receipts, CLI validation, reconciliation, and cleanup of legacy scripts.

## Execution record

**Status:** concluído em 2026-09-15.

- Contratos ativos e rota visual-first atualizados; documentos anteriores foram
  identificados como históricos/obsoletos.
- Agendamento real de `topic_20260914_04` confirmado visualmente no LinkedIn para
  `2026-09-16T10:00 America/Sao_Paulo`, com receipt e reconciliação sem problemas.
- Scripts legados de mutação removidos; CLI, receipts, movimentação pós-confirmação
  e testes de consistência documental estão ativos.
- Correção P1 aplicada no schema de receipts: `image_analyzer_failure` é campo
  permitido e obrigatório quando a rota efetiva é `image-analyzer`, com teste
  regressivo dedicado.

## Global Constraints

- Approved posts must be in `content/drafts/` and contain `## Fontes`.
- Only the human approval workflow marks `approved`; this system records that state but never creates it.
- Visual route is: embedded browser → screenshot/AX → visual confirmation → mutation → scheduled-list confirmation.
- Playwright may inspect only; it must not click publish, schedule, reschedule, or delete.
- On ambiguous mutation, stop, do not repeat, do not open a new composer, and never register a timestamp.
- Timestamp registration requires `confirmation`, `scheduled_list`, `summary`, `preview`, and `scheduled_list_confirmed` to be explicit successful values.
- Receipts and progress must be persisted before reporting success.
- Tests must run with plain `pytest -q` and `npm test` from the repository root.

---

### Task 1: Test Bootstrap and Roadmap Integration

**Files:**
- Create: `conftest.py`
- Modify: `package.json`
- Modify: `docs/roadmap.md`
- Test: `tests/test_test_runtime.py`

**Interfaces:**
- Consumes: existing root-level Python modules.
- Produces: `pytest -q` import behavior and `npm run test:python`.

- [ ] **Step 1: Write failing test**

```python
from pathlib import Path

import scheduling_contract


def test_plain_pytest_can_import_root_modules():
    assert Path("scheduling_contract.py").is_file()
    assert scheduling_contract.__file__.endswith("scheduling_contract.py")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_test_runtime.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'scheduling_contract'`.

- [ ] **Step 3: Add root bootstrap**

```python
ROOT = Path(__file__).resolve().parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_test_runtime.py -q`

Expected: PASS.

- [ ] **Step 5: Add npm command and update roadmap progress**

Add `"test:python": "pytest -q"` to scripts. Update the roadmap item progress to `1 de 8`.

### Task 2: Visual Scheduling Contract

**Files:**
- Modify: `scheduling_contract.py`
- Test: `tests/test_scheduling_skill.py`

**Interfaces:**
- Consumes: existing receipt validation.
- Produces: `validate_schedule_events(events, route)`, `validate_reschedule_events(events, route, effective_route, fallback)`, and receipts where `browser_attempted: true`.

- [ ] **Step 1: Write failing tests**

```python
def test_visual_first_schedule_is_valid_without_playwright():
    events = [
        "approved_file", "markdown_converted", "browser_attempt", "screenshot",
        "visual_route", "date_selected", "time_selected", "summary_confirmed",
        "advance", "final_preview_confirmed", "schedule", "confirmation",
        "scheduled_list_confirmed", "timestamp_registered",
    ]
    assert validate_schedule_events(events, "browser_native") is True


def test_receipt_accepts_browser_first_route():
    gate = valid_registration_gate()
    gate["receipt"].update({
        "route": "browser_native",
        "fallback": "none",
        "route_attempted": ["browser_native"],
        "playwright_attempted": False,
    })
    gate["receipt"]["route_reasons"] = {"browser_native": "visual inspection confirmed"}
    assert can_register_timestamp(**gate) is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_scheduling_skill.py -q`

Expected: FAIL because only Playwright-first routes are accepted.

- [ ] **Step 3: Implement visual-first validation**

Replace `_COMMON` with `("approved_file", "markdown_converted", "browser_attempt", "screenshot",)`. Accept effective routes `browser_native`, `image-analyzer`, `playwright`, and `stop`. Make `playwright` a fallback branch only. Replace `playwright_attempted` with `browser_attempted`, and keep `playwright_attempted` accepted only as `False` when it exists.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scheduling_skill.py -q`

Expected: PASS.

### Task 3: Scheduling CLI

**Files:**
- Create: `linkedin_scheduling.py`
- Test: `tests/test_linkedin_scheduling_cli.py`

**Interfaces:**
- Consumes: `scheduling_registry.scan_posts()` and `find_conflicts()`.
- Produces: `validate_scheduling_request(file_path, requested_timestamp)`, `prepare_run(request, run_id=None)`, `load_receipt(path)`, `record_confirmed_receipt(path, *, displayed_timestamp, browser_state, events)`, and `move_after_confirmation(file_path, receipt_path)`.

- [ ] **Step 1: Write failing tests**

```python
def test_validate_rejects_unapproved_draft(tmp_path):
    post = tmp_path / "post.md"
    post.write_text("Texto\n\n## Fontes\n- Fonte\n")
    with pytest.raises(ValueError, match="approved"):
        validate_scheduling_request(post, "2026-09-20T10:00 America/Sao_Paulo")


def test_validate_converts_markdown_without_cru_markup(tmp_path):
    post = tmp_path / "post.md"
    post.write_text("## Título\n**Negrito** #tag\n\n## Fontes\n- Fonte\n")
    request = validate_scheduling_request(
        post,
        "2026-09-20T10:00 America/Sao_Paulo",
        approved=True,
    )
    assert request["linkedin_text"] == "Título\nNegrito #tag\n\nFontes\n- Fonte"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_linkedin_scheduling_cli.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'linkedin_scheduling'`.

- [ ] **Step 3: Implement validation and receipt persistence**

Validation must check location, approval, sources, timezone timestamp, registry conflicts, and absent `agendado` marker. `prepare_run` writes a receipt under `runs/scheduling/<run_id>/receipt.yaml` with all browser gates `not_run`. `record_confirmed_receipt` fails unless `summary_confirmed`, `confirmation_received`, `scheduled_list_confirmed`, and `timestamp_registered` are booleans, timestamps match, browser state is real, and the event sequence is valid. `move_after_confirmation` validates first, then uses `git mv` or `mv`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_linkedin_scheduling_cli.py -q`

Expected: PASS.

### Task 4: Reconciliation

**Files:**
- Create: `scheduling_reconciliation.py`
- Test: `tests/test_scheduling_reconciliation.py`
- Modify: `scheduling_registry.py`

**Interfaces:**
- Consumes: content files, topic YAML, and scheduling registry.
- Produces: `reconcile_local_state()` returning `problems` and `actions`, plus `cli_reconcile(argv=None)` with `--output`.

- [ ] **Step 1: Write failing tests**

```python
def test_reconcile_detects_published_file_without_publication_marker(tmp_path):
    content = make_content_tree(tmp_path)
    post = content / "published" / "post.md"
    post.write_text("Texto\n\n## Fontes\n- Fonte\n")
    problems = reconcile_local_state(content, now=datetime(2026, 9, 16, 10))
    assert {"type": "published_without_publication_marker", "topic_id": "post"} in problems


def test_reconcile_reports_mismatched_topic_status(tmp_path):
    content, topics = make_content_tree(tmp_path)
    set_topic_status(topics, "topic_20260901_02", "drafted")
    problems = reconcile_local_state(content, topic_files=[topics])
    assert any(p["type"] == "topic_status_mismatch" for p in problems)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_scheduling_reconciliation.py -q`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement reconciliation**

Rules:
- `published/` requires a publication marker.
- `drafts/` must not have an `agendado` marker.
- `archived/` markers are historical only.
- `published/` topic status must be `published`.
- `drafts/` topic status must be `drafted`.
- Unknown or orphaned statuses are reported, not silently repaired.
- Output YAML includes `problems`, `actions`, and `safe_actions_only`.

- [ ] **Step 4: Run tests and generate the first reconciliation report**

Run: `pytest tests/test_scheduling_reconciliation.py -q` and `python scheduling_reconciliation.py --output runs/scheduling-reconciliation-2026-09-15.yaml`

Expected: tests PASS and report exists.

### Task 5: Browser Runtime Contract

**Files:**
- Modify: `scripts/linkedin_browser_check.js`
- Modify: `tests/linkedin_browser_check.test.js`
- Remove: `linkedin_schedule.mjs`
- Remove: `linkedin_reschedule.mjs`
- Remove: `linkedin_check.mjs`
- Remove: `close_tab.mjs`

**Interfaces:**
- Consumes: `resolveBrowserRoute` adapter contract.
- Produces: `browserRouteOrder()` equal `["browser_native", "image-analyzer", "playwright", "stop"]`, plus default visual route unavailable.

- [ ] **Step 1: Write failing tests**

```js
test('visual browser route is primary without requiring Playwright', async () => {
  const result = await runBrowserCheck({
    visualAdapter: {
      inspect: async () => ({ ok: true, report: { visual_state: 'native_confirmed' } }),
    },
    playwrightAdapter: { inspect: async () => { throw new Error('must not run'); } },
  });
  assert.equal(result.effective_route, 'browser_native');
});

test('Playwright is only a non-mutating diagnostic fallback', async () => {
  const calls = [];
  const result = await runBrowserCheck({
    visualAdapter: {
      inspect: async () => { calls.push('visual'); return { ok: false, reason: 'native_failed' }; },
    },
    playwrightAdapter: {
      inspect: async () => { calls.push('playwright'); return { ok: true, report: { visual_state: 'read_only' } }; },
    },
  });
  assert.deepEqual(calls, ['visual', 'playwright']);
  assert.equal(result.effective_route, 'playwright');
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -- tests/linkedin_browser_check.test.js`

Expected: FAIL for `browser_native`.

- [ ] **Step 3: Implement embedded-browser route**

Replace `screenshot+nativa` with `browser_native`. The default adapter remains unavailable until CUA supplies one, so the script can inspect but cannot mutate. Playwright reports `mutation_allowed: false`. Delete the four legacy mutation scripts.

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test`

Expected: PASS.

### Task 6: Documentation and Real Visual Dry-Run

**Files:**
- Modify: `docs/browser-route-contract.md`
- Modify: `.agents/skills/publicar-linkedin/SKILL.md`
- Modify: `AGENTS.md`
- Modify: `README.md`
- Test: `tests/test_browser_route_documentation.py`

**Interfaces:**
- Consumes: final CLI and browser route names.
- Produces: one documented mutation protocol.

- [ ] **Step 1: Write failing documentation test**

```python
def test_publication_contract_names_real_embedded_browser_route():
    text = Path("docs/browser-route-contract.md").read_text()
    assert "CUA embedded browser" in text
    assert "browser_native" in text
    assert "read-only diagnostic" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_browser_route_documentation.py -q`

Expected: FAIL.

- [ ] **Step 3: Document the exact operator protocol**

Update every browser reference to `CUA embedded browser`, `browser_native`, real screenshot/AX evidence, and Playwright as read-only diagnostic. Remove references to the deleted legacy scripts. Document that a human must explicitly confirm a real LinkedIn mutation.

- [ ] **Step 4: Run the visual dry-run**

In the embedded browser: open `https://www.linkedin.com/feed/`, open “Começar publicação”, open the scheduling popover, select the requested date/time, verify the displayed summary, and stop before `Avançar`. Save the receipt with `blocked_before_advance`.

Expected: no LinkedIn mutation and no duplicate composer.

- [ ] **Step 5: Update roadmap progress**

Set progress to `6 de 8`.

### Task 7: Current State Reconciliation

**Files:**
- Modify: `content/published/topic_20260914_08.md`
- Modify: `research/topics/topics_2026-09-14.yaml`
- Modify: `docs/roadmap.md`
- Test: `tests/test_content_state_consistency.py`

**Interfaces:**
- Consumes: reconciliation rules.
- Produces: consistent local state for the post already published today.

- [ ] **Step 1: Write failing state test**

```python
def test_today_published_post_has_publication_marker():
    text = Path("content/published/topic_20260914_08.md").read_text()
    assert "<!-- publicado: " in text
    assert "<!-- agendado: 2026-09-15T10:00 America/Sao_Paulo -->" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_content_state_consistency.py -q`

Expected: FAIL.

- [ ] **Step 3: Record observed state**

Keep the scheduled timestamp and add a publication marker only because the LinkedIn activity list visually confirmed publication. Set `topic_20260914_08` to `published`. Do not invent an exact LinkedIn publication time; record `observed_relative_time: "4 horas"` in the reconciliation report.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scheduling_reconciliation.py tests/test_content_state_consistency.py -q`

Expected: PASS.

- [ ] **Step 5: Update roadmap progress**

Set progress to `7 de 8`.

### Task 8: Final Verification and Roadmap Completion

**Files:**
- Modify: `docs/roadmap.md`

**Interfaces:**
- Consumes: all previous tasks.
- Produces: verified completion evidence.

- [ ] **Step 1: Run the complete Python suite**

Run: `pytest -q`

Expected: all tests PASS without `PYTHONPATH`.

- [ ] **Step 2: Run the Node suite**

Run: `npm test`

Expected: all tests PASS.

- [ ] **Step 3: Verify working-tree hygiene**

Run: `git diff --check`

Expected: exit code 0 with no whitespace errors.

- [ ] **Step 4: Mark the roadmap item complete**

Remove the active item from “Pendências ativas” and update the operational state with the route, CLI commands, and fresh test counts.
