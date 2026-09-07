# P2.3 Whole-Branch IMPORTANT Fix Report

Date: 2026-09-06

## Changes

- `score_opportunities.py`: extracted shared weight-map validation and made
  `run_scoring(topics, weights)` reject empty/invalid maps, negative or
  non-numeric values, sums different from `1.0`, and criteria that differ from
  the topic sample. The persisted `scores.total` field is excluded from the
  criteria comparison.
- `tests/test_score_opportunities.py`: added invalid-map regression coverage.
- `research/audits/scoring-parallel-2026-09-06.yaml`: added the explicit
  alternative hypothesis, evidence references to existing audits, and the
  explicit diagnostic-only/rejected-as-operational-change decision.
- `docs/roadmap.md`: replaced the claim of observed post results with the
  formulation that decisions and observed quality were compared and predictive
  results remain inconclusive.

No active weights, signals, posts, schedules, or metrics were changed by this
fix.

## Verification

Command:

```text
PYTHONPATH=. pytest -q tests/test_score_opportunities.py::test_run_scoring_rejects_invalid_weight_maps
```

Output before implementation (expected RED):

```text
FFFF                                                                     [100%]
4 failed in 0.04s
```

Command:

```text
PYTHONPATH=. pytest -q tests/test_p2_3_audits.py tests/test_score_opportunities.py
```

Output:

```text
.............                                                            [100%]
13 passed in 0.07s
```

Command:

```text
PYTHONPATH=. pytest -q
```

Output:

```text
292 passed, 2 failed in 3.88s
```

The two failures are:

```text
tests/test_scheduling_checklist.py::test_checklist_registration_gate_has_explicit_types_and_failure_state
tests/test_scheduling_skill.py::test_manual_scheduling_matrix_and_receipt_are_non_sensitive_and_complete
```

They concern existing scheduling changes outside this fix: the checklist has
`timestamp_registered: True`, and the current roadmap does not contain the
expected `"não foram executados"` wording. Neither was changed here.

Command:

```text
git diff --check
```

Output: no output; exit code `0`.

Command:

```text
git diff -- config/scoring.yaml; shasum -a 256 config/scoring.yaml
```

Output:

```text
4db37649eef7ce7e1e29cfd18db9e3e8d471b337173308eb4ec3ddbe7b9f08ef  config/scoring.yaml
```

## Status

P2.3 IMPORTANT findings addressed. Focused tests pass. Full suite is not fully
green because of the two unrelated pre-existing scheduling test failures above.
