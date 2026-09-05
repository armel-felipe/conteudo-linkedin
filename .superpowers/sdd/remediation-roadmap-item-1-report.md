# Remediation Roadmap Item 1 Report

## Status

Approved by the requested gate: `coverage >= 0.99`, no hard failures, and no
open critical, important, or high findings.

## Scope

Only batch topic-selection validation, its focused tests, and the selection
contract documentation were changed. `gauntlet_loop.py`, integrations, and
scheduling were not changed or executed.

## Root Cause

`load_and_select_topics` treated every digit string as a valid numeric count,
so `0` returned an empty list. Empty strings and comma-only explicit selections
also produced an empty list because blank tokens were filtered out. Explicit
IDs were trimmed but never checked for duplicates. `N > eligible` already used
safe list slicing and therefore correctly selected all available eligible
topics.

## RED

Added focused tests for numeric zero (`0` and `00`), empty/whitespace
selection, `N > eligible`, explicit duplicate IDs with and without spaces, and
`all` with no eligible topics.

Initial focused result after the tests, before the implementation change:

```text
8 failed, 44 passed
```

The failures were the expected missing validation failures; the larger-than-
eligible selection test passed, confirming that behavior was preserved.

## GREEN

- Reject numeric zero before slicing with a positive-count error.
- Reject an empty resolved selection, covering empty input and `all` with no
  eligible topics.
- Reject explicit duplicate IDs after trimming whitespace.
- Preserve numeric slicing, including selecting all topics when `N` exceeds the
  eligible count.
- Updated `run-editorial-batch`, the roadmap, and the batch design spec.

## Gauntlet

One isolated remediation round was sufficient and stayed within the maximum of
five rounds. Deterministic checks covered the requested selection cases, scope
exclusion of Gauntlet core/integration/scheduling, and documentation alignment.
The review gate passed with coverage 1.0, all applicable criteria at 10/10,
empty `hard_failures`, and no open critical, important, or high findings.

## Verification

```text
PYTHONPATH=. pytest -q tests/test_batch_skill.py
52 passed in 0.67s
```

The full-suite, compile, and diff checks are recorded by the final verification
run associated with this report.

## Concerns

- The public batch entry point is the skill contract rather than a CLI module;
  validation is therefore enforced at the shared selector boundary.
- No negative numeric string test was added because the existing accepted
  selection grammar is digits, `all`, or explicit IDs; negative values remain
  invalid as explicit IDs.
