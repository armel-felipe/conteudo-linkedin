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

## Remediation Round 2

### Scope

Only terminal-state validation in `gauntlet_loop.py` was hardened, with the approved-state producer updated to persist the required empty `failed_criteria` list. Batch, integration, and scheduling code were not touched.

### Root Cause

`_validate_terminal_state()` checked required-key presence, artifact/review identity, and the SHA-256 value, but trusted the types and semantics of persisted `cycles`, `cycle_count`, `feedback`, and `failed_criteria`. It also reused an `approved` state without reapplying the approval gates.

### RED

Added a parameterized regression test covering string, negative, and boolean cycle values plus invalid feedback and failed-criteria entries. Each case persisted an otherwise valid state and asserted `blocked` without overwriting it.

Focused RED output:

```text
8 failed, 37 deselected
```

The failures showed invalid persisted values being reused as `approved`.

### GREEN

`_validate_terminal_state()` now requires:

- `approved` or `blocked` status;
- integer, non-boolean `cycles` and `cycle_count`, each in `1..5` and equal;
- relative `last_artifact` equal to the expected artifact;
- contract-valid `last_review`;
- valid state `feedback` matching the review;
- string `failed_criteria` matching the review's failed criteria;
- exact SHA-256 fingerprint;
- approval gates on approved states: approved decision, coverage `>= 0.99`, no failed criteria, no hard failures, and no feedback.

Focused GREEN output:

```text
PYTHONPATH=. pytest -q tests/test_gauntlet_skill.py -k 'terminal_state or persistence or 099'
13 passed, 32 deselected
```

Full verification:

```text
PYTHONPATH=. pytest -q tests/test_gauntlet_skill.py
45 passed in 0.07s

PYTHONPATH=. pytest -q
128 passed in 0.66s
```

## Remediation Round 3

### Scope

Hardened only the Gauntlet core plus the requested acceptance wording in `AGENTS.md`, `docs/roadmap.md`, and the editorial plan. Falha 2, batch behavior, integration behavior, and scheduling were not changed.

### Root Cause

`_blocked()` did not produce a complete terminal checkpoint: it omitted `artifact_fingerprint`, could emit cycle `0`, and could leave `last_review` as `None`. Terminal-state resume also compared failed criteria in insertion order and allowed persistence read/write exceptions to escape from `state.yaml` and `events.yaml`.

### RED

Added regressions for:

- blocked checkpoint production and resume without rerunning callbacks;
- multiple failed criteria persisted in a different order;
- invalid UTF-8 bytes in `state.yaml` without overwriting the original file.

Focused RED output:

```text
3 failed
```

The failures showed a non-resumable blocked payload, order-sensitive criteria validation, and an uncaught `UnicodeDecodeError`.

### GREEN

- `_blocked()` now emits coherent terminal fields, normalizes cycles to `1..5`, creates a valid blocked review when needed, and computes `sha256:<64 hex>` whenever the artifact is readable.
- Terminal validation compares `failed_criteria` canonically and accepts blocked payloads with complete review/feedback data.
- `UnicodeDecodeError` and `OSError` from persistence reads/writes return `blocked` without replacing the affected file.
- Acceptance wording now consistently states `coverage >=0.99` / `coverage >= 0.99` in the three requested documents.

Focused GREEN output:

```text
PYTHONPATH=. pytest -q tests/test_gauntlet_skill.py -k 'blocked_result_is_persisted or failed_criteria_in_different_order or invalid_persistence_bytes'
3 passed, 45 deselected
```

Full verification:

```text
PYTHONPATH=. pytest -q tests/test_gauntlet_skill.py
48 passed in 0.05s

PYTHONPATH=. pytest -q
131 passed in 0.63s

python3 -m compileall -q gauntlet_loop.py
git diff --check
```

## Remediation Round 4

### Scope

Updated the acceptance wording in the Gauntlet, batch, research, writing, `AGENTS.md`, roadmap, and editorial specification documents. Hardened only terminal-resume artifact validation in `gauntlet_loop.py`; Falha 2 logic was not changed.

### Root Cause

Terminal resume called `_validate_terminal_state()` through a path where artifact fingerprint reads could raise `OSError`, `PermissionError`, or `UnicodeDecodeError`, instead of becoming a fail-closed blocked result. Several relevant documents also still described the superseded strict gate (`>0.99` or `>99%`).

### RED

Added a parameterized regression that makes artifact reads raise `OSError`, `PermissionError`, and `UnicodeDecodeError` during terminal resume, then asserts `blocked` and an untouched `state.yaml`.

Focused RED output:

```text
3 failed, 48 deselected
```

The failures exposed fingerprint divergence/uncaught decoding behavior rather than an artifact-read failure result.

### GREEN

- Artifact fingerprint reads during terminal validation now convert the three requested read failures to a clear artifact-read validation error; the existing fail-closed resume path returns `blocked` without writing state.
- `_blocked()` fingerprint fallback also handles `UnicodeDecodeError`.
- All relevant documents now state `coverage >=0.99` or `coverage >=99%`.

Focused GREEN output:

```text
PYTHONPATH=. pytest -q tests/test_gauntlet_skill.py -k terminal_resume_artifact_read_errors
3 passed, 48 deselected
```

Full verification:

```text
PYTHONPATH=. pytest -q tests/test_gauntlet_skill.py
51 passed in 0.08s

PYTHONPATH=. pytest -q
134 passed in 0.65s

python3 -m compileall -q gauntlet_loop.py
git diff --check
```

Documentation scan:

```text
No files found for >0.99, > 0.99, >99%, > 99%, superior a 99, or maior que 99.
```

## Remediation Round 5 (Final)

### Scope

Closed the final P1/P2 findings in the Gauntlet core and normalized the relevant acceptance wording to the single form `coverage >= 0.99`. Falha 2 and scheduling logic were not changed.

### Root Cause

Terminal artifact validation protected fingerprint reads but not the complete metadata sequence (`exists`, `is_file`, and `stat`). Terminal state validation also did not require `failure_reasons`, allowing an incomplete checkpoint to be reused as approved.

### RED

Added regressions for `OSError` from artifact `exists`, `is_file`, and `stat`, plus a terminal state with missing `failure_reasons`. Each regression verifies `blocked` and preserves the original `state.yaml`.

Focused RED output:

```text
4 failed, 51 deselected
```

### GREEN

- Wrapped the full artifact metadata and fingerprint validation sequence in fail-closed handling for `OSError`, `PermissionError`, and `UnicodeDecodeError`.
- Required non-empty string `failure_reasons` in terminal state and persisted `failure_reasons: ["approved"]` for approved checkpoints.
- Updated relevant Gauntlet, batch, research, writing, agent, roadmap, plan, and spec documentation to use `coverage >= 0.99`.
- Updated the multi-criterion terminal-state fixture to include the required failure reason.

Focused GREEN output:

```text
PYTHONPATH=. pytest -q tests/test_gauntlet_skill.py -k 'metadata_errors or without_failure_reasons'
4 passed, 51 deselected
```

Final verification:

```text
PYTHONPATH=. pytest -q tests/test_gauntlet_skill.py
55 passed in 0.11s

PYTHONPATH=. pytest -q
138 passed in 0.69s

python3 -m compileall -q gauntlet_loop.py
git diff --check
```
