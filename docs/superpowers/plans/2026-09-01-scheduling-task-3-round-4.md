# Scheduling Task 3 Round 4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make scheduling evidence fail-closed and document/test a browser dry-run that stops before `Avançar`.

**Architecture:** Extend the pure Python contract with explicit evidence statuses and a dry-run event validator. Keep browser interaction documentation-only and update the existing report with truthful round-4 classifications; no LinkedIn mutation is permitted.

**Tech Stack:** Python 3, pytest, Markdown.

## Global Constraints

- Do not create, publish, schedule, delete, or alter any LinkedIn publication.
- `evidence_status` must be exactly one of `real_non_destructive`, `real_existing_post`, `simulated`, `not_run`.
- A dry-run must stop before `Avançar` and must not claim confirmation, scheduled-list, or timestamp registration.
- Existing-post validation may inspect `... -> Alterar agenda` only, without confirming a second change.

---

### Task 1: Harden Evidence Receipt Contract

**Files:**
- Modify: `scheduling_contract.py`
- Test: `tests/test_scheduling_skill.py`

**Interfaces:**
- Produces `validate_receipt(receipt)` accepting the required `evidence_status` field and enforcing status-specific gates.
- Produces `validate_dry_run_events(events)` for the explicit pre-`Avançar` sequence.

- [ ] **Step 1: Write failing tests**

Add tests for all four statuses, rejection of unknown status, dry-run stopping before `advance`, and rejection when dry-run includes `advance`, `schedule`, `confirmation`, `scheduled_list_confirmed`, or `timestamp_registered`.

- [ ] **Step 2: Run focused tests**

Run: `python3 -m pytest tests/test_scheduling_skill.py -q`

Expected: FAIL because `evidence_status` and `validate_dry_run_events` are not yet part of the contract.

- [ ] **Step 3: Implement minimal validation**

Add the four-status allowlist and require `evidence_status` in `_RECEIPT_FIELDS`. Permit `real_non_destructive` and `real_existing_post` receipts to represent observation only, while preserving strict success gates for receipts claiming a completed schedule. Add a dry-run sequence ending in `blocked_before_advance` and reject all mutating events.

- [ ] **Step 4: Run focused tests**

Run: `python3 -m pytest tests/test_scheduling_skill.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scheduling_contract.py tests/test_scheduling_skill.py
git commit -m "test: enforce scheduling evidence statuses"
```

### Task 2: Document Browser Dry-Run and Round 4 Evidence

**Files:**
- Modify: `.agents/skills/publicar-linkedin/SKILL.md`
- Modify: `.superpowers/sdd/scheduling-task-3-report.md`
- Modify: `docs/roadmap.md`
- Test: `tests/test_scheduling_skill.py`

**Interfaces:**
- Documentation defines a browser dry-run ending before `Avançar`.
- Report records all five scenarios with one exact evidence status each and explicit safety non-execution notes.

- [ ] **Step 1: Write failing documentation assertions**

Assert the skill and report contain `real_non_destructive`, `real_existing_post`, `simulated`, `not_run`, `blocked_before_advance`, and explicit statements that creation, deletion, scheduling, and alteration were not executed.

- [ ] **Step 2: Run focused tests**

Run: `python3 -m pytest tests/test_scheduling_skill.py -q`

Expected: FAIL until the protocol and report are updated.

- [ ] **Step 3: Update the protocol and report**

Describe selecting date, selecting time again, confirming the summary, and stopping before `Avançar`. Reclassify scenario evidence truthfully; do not call a simulation browser-real. Preserve the existing correct schedule and state that `Alterar agenda` was not confirmed.

- [ ] **Step 4: Run the full test suite**

Run: `python3 -m pytest -q`

Expected: PASS with no browser or LinkedIn mutation.

- [ ] **Step 5: Commit**

```bash
git add .agents/skills/publicar-linkedin/SKILL.md .superpowers/sdd/scheduling-task-3-report.md docs/roadmap.md tests/test_scheduling_skill.py
git commit -m "docs: attach scheduling evidence round four"
```
