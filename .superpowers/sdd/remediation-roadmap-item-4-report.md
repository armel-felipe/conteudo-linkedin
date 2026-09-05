# Remediation Roadmap Item 4 Report

## Status

Approved by the requested gates: coverage >= 0.99, all criteria >= 9/10, and
zero hard, critical, important, or high findings.

## Root Cause

`checkpoint_valid` exposed only a boolean and terminal paths did not validate a
completed state's checkpoint against its manifest entry and canonical commit.
The final batch state also remained `running` while the manifest entry was
`completed`, leaving a dangerous ambiguity for recovery code.

## Contract and Fix

- `approval_humana` now persists both `state.yaml` and the queue entry as
  `completed` with `current_stage: null`.
- A completed state must have convergent checkpoint, result, review, fingerprint,
  paths, manifest entry, and canonical commit evidence.
- Missing or divergent terminal evidence raises structured
  `completed_state_integrity` through `TerminalIntegrityError`.
- The error is raised before transition, callback-equivalent stage work, event
  writes, manifest writes, or metric updates. The original completed state and
  manifest remain unchanged and are never reclassified as `blocked`.
- `blocked` remains reserved for execution, review, and recoverable cycle
  failures.

## TDD and Gauntlet

RED reproduced a completed state with incomplete paths and showed that recovery
did not fail. GREEN added the terminal validator and final-state transition.
Regression coverage exercises divergent or absent checkpoint result, review
file, commit event, fingerprint, paths, and result file, plus immutability of
state, manifest, events, and metrics. The Loop Gauntlet completed in one round;
the five-round maximum was not exceeded.

## Verification

```text
PYTHONPATH=. pytest -q
200 passed in 3.73s
python3 -m compileall -q editorial_batch.py gauntlet_loop.py tests
```

`gauntlet_loop.py`, scheduling behavior, and publication behavior were not
changed.

## Concerns

- Existing persisted runs are not rewritten or auto-repaired. A corrupt
  `completed` state now requires explicit human remediation because fail-closed
  behavior forbids silently changing terminal evidence or status.
