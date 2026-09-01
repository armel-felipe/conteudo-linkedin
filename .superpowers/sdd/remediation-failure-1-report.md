# Remediation Failure 1 Report

## Status

Approved after the focused Gauntlet remediation.

## Root Cause

- `run_gauntlet` attempted to read `persistence_dir/state.yaml` before validating that `persistence_dir` was a directory, allowing `NotADirectoryError` to escape.
- A valid JSON state payload with an invalid terminal shape was handled inconsistently: malformed state paths could raise instead of returning a fail-closed `blocked` result.
- The quality gate used `coverage <= 0.99` as failure, contradicting the acceptance contract that allows `coverage >= 0.99`.
- Non-empty `hard_failures` already blocked approval; the contract was clarified to include unresolved critical questions in that blocking category.

## RED

Added regression tests for invalid persistence paths, malformed terminal state, inclusive `0.99` acceptance, and hard-failure/critical-question blocking.

Before the fix:

```text
2 failed, 35 passed
```

The failures were the expected `NotADirectoryError` and `coverage 0.99` being returned as `blocked`.

## GREEN

Implemented the minimum core changes:

- Validate an existing persistence path as a directory and convert filesystem errors to `blocked`.
- Reject malformed terminal state payloads fail-closed without replacing the persisted state.
- Change the quality retry condition from `coverage <= 0.99` to `coverage < 0.99`.
- Align the skill and review schema documentation with the inclusive coverage gate and critical-question blocking rule.

## Files

- `gauntlet_loop.py`
- `.agents/skills/gauntlet-loop/SKILL.md`
- `docs/schemas/gauntlet-review.json`
- `tests/test_gauntlet_skill.py`
- `.superpowers/sdd/remediation-failure-1-report.md`

## Verification

```text
PYTHONPATH=. pytest -q tests/test_gauntlet_skill.py
37 passed in 0.04s

PYTHONPATH=. pytest -q
120 passed in 0.68s
```

The existing documentation-integration behavior for syntactically corrupt JSON remains unchanged; semantic terminal-state malformation is now rejected fail-closed as requested.
