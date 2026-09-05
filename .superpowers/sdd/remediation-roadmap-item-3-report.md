# Remediation Roadmap Item 3 Report

## Status

Approved by the requested gate: `coverage >= 0.99`, zero hard failures, and no
open critical, important, or high findings. Scope was limited to partial batch
cycle recovery in `editorial_batch.py`, its tests, and the batch persistence
contract. `gauntlet_loop.py`, scheduling, and publishing were not changed.

## Root Cause

`persist_stage` treated interrupted cycles as a binary exception path. It could
not distinguish a recoverable intent with complete evidence from an orphan or
divergent set of files, and the recovery path rewrote files even after their
contents had been validated. Commit events also did not prove that a matching
intent existed, while temporary files were ignored.

## RED

Added regressions for artifact-only intent, result-only and review-only orphan
files, review-without-commit recovery, intent-without-commit recovery,
commit-without-intent, temporary files, and preservation of valid payload bytes.
The focused RED run was:

```text
5 failed, 0 passed
```

The failures showed the existing `ValueError`/manifest behavior and the
unconditional artifact/result/review writes during recovery.

## GREEN

- Recovery now requires complete artifact, result, review, and the SHA-256
  `artifact_fingerprint` recorded by the intent.
- Complete intents recover by writing only missing files; valid existing
  payloads are not overwritten.
- Incomplete intents, orphan payloads, commits without intents, and temporary
  files return `blocked` with structured `failure_reasons` and preserve data.
- Commit events remain canonical and do not inherit intent-only metadata.
- Atomic writes and persistence ordering remain unchanged.
- The skill and editorial-run schema document the recovery contract.

## Gauntlet

One isolated Loop Gauntlet round was sufficient and stayed within the maximum
of five rounds. Deterministic checks covered all requested partial states,
payload/fingerprint validation, atomic persistence, ordering, idempotency,
resume behavior, and non-overwrite guarantees. Review result: `coverage: 1.0`,
all 14 criteria `10/10`, empty `hard_failures`, and empty actionable feedback.

## Verification

```text
PYTHONPATH=. pytest -q tests/test_batch_skill.py tests/test_run_contracts.py tests/test_documentation_consistency.py
74 passed

PYTHONPATH=. pytest -q
193 passed in 1.28s

python3 -m compileall -q editorial_batch.py gauntlet_loop.py tests
exit 0

git diff --check
exit 0
```

## Concerns

- A blocked partial cycle is terminal until an operator resolves the preserved
  files and starts an explicit recovery path; the runtime never deletes or
  guesses which payload should win.
- Temporary-file detection covers `.tmp` files in the cycle payload
  directories; unrelated temporary files elsewhere in the workspace are not
  considered part of this cycle.
