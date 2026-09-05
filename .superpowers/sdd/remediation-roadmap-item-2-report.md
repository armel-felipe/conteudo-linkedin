# Remediation Roadmap Item 2 Report

## Status

Approved by the requested gate: `coverage >= 0.99`, no hard failures, and no
open critical, important, or high findings. The requested scope was limited to
rejecting a new selection that diverges from an existing frozen manifest.

## Scope

Changed only the shared manifest boundary, its focused tests, the editorial-run
schema comment, and the roadmap checkbox. `gauntlet_loop.py`, scheduling, and
approved-post files were not changed.

## Root Cause

`freeze_manifest` loaded and validated an existing manifest, then returned it
without comparing the newly requested `selection` or `topics`. A caller could
therefore resume a run with a different selection or queue while the old frozen
manifest remained authoritative.

## RED

Added tests proving that an existing valid manifest accepts the identical
selection and queue, while rejecting a different selection string, reordered
topic IDs, changed queue score/content, divergent queue fingerprint, and
`queue_frozen: false`. Every rejection asserts that `manifest.yaml` bytes are
unchanged.

Focused RED result before the implementation change:

```text
3 failed, 3 passed, 52 deselected
```

The three failures were the missing selection/order/queue comparisons. Existing
fingerprint and `queue_frozen` validation already rejected the other two cases.

## GREEN

The existing-manifest branch now compares the literal selection and the
fingerprint of the canonical immutable queue projection (`topic_id`, position,
and score). It raises structured `ValueError` messages and performs no write on
divergence. Mutable queue execution fields remain outside the comparison.

## Gauntlet

One isolated Loop Gauntlet round was sufficient and stayed within the maximum of
five rounds. The review returned `coverage: 1.0`, all 14 criteria at `10/10`,
empty `hard_failures`, and empty actionable feedback.

## Verification

```text
PYTHONPATH=. pytest -q tests/test_batch_skill.py -k 'existing_manifest'
6 passed, 52 deselected

PYTHONPATH=. pytest -q
187 passed in 1.16s

python -m compileall -q editorial_batch.py gauntlet_loop.py tests
exit 0

git diff --check
exit 0
```

The initial full-suite run exposed one stale expectation in the pre-existing
idempotency test: it changed a queued score while expecting the old manifest to
be accepted. The test was corrected to repeat the unchanged queue; the final
suite result above is after that correction.

## Concerns

- The public batch entry point is the shared `freeze_manifest` boundary rather
  than a separate CLI module.
- Queue status and current stage are intentionally excluded from the immutable
  comparison because the batch updates them while retaining the frozen queue.
