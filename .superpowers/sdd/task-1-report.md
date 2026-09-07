# Task 1 Report

## Status

Implemented. `score_opportunities.py` contains the executable scoring formula, while `config/scoring.yaml` contains the scoring weights. The scoring formula inventory and frozen sample artifact were created without changing active weights, original signals, or posts.

## Files

- Created `research/audits/scoring-inventory-2026-09-06.yaml`.
  - Records `score_opportunities.py` as the executable formula path and `config/scoring.yaml` as the weights source.
  - Records the seven criteria and their active weights.
  - Lists the frozen topic and signal sample paths in ordered hashing sequence.
  - Records `sha256:98c55232bb92331e1875912b06890cc3b0ad08afc7d4b8cf14829c3e4b87044b`.
  - Records missing criteria/data limitations and the fingerprint method.
- Created `tests/test_p2_3_audits.py` with the required inventory contract test.

## Tests

- RED: `PYTHONPATH=. pytest -q tests/test_p2_3_audits.py::test_scoring_inventory_has_formula_weights_and_fingerprint` failed because the inventory artifact did not exist.
- GREEN: the same targeted test passed: `1 passed`.
- Independent fingerprint verification passed and matched the recorded digest.
- Full suite: `284 passed, 2 failed`.

## Concerns

- The full-suite failures are unrelated pre-existing worktree changes, not caused by Task 1:
  - `tests/test_scheduling_checklist.py::test_checklist_registration_gate_has_explicit_types_and_failure_state` fails because `docs/schemas/linkedin-scheduling-checklist.yaml` has `timestamp_registered: true`.
  - `tests/test_scheduling_skill.py::test_manual_scheduling_matrix_and_receipt_are_non_sensitive_and_complete` fails because the existing `docs/roadmap.md` lacks the expected phrase `não foram executados`.
- The sample fingerprint is defined as SHA-256 over the raw bytes of the ordered sample files concatenated without separators; changing either source file invalidates it.

## Review Corrections — 2026-09-06

- `research/audits/scoring-inventory-2026-09-06.yaml` now records `score_opportunities.py` as `formula_path`, with the executable formula referenced at `score_opportunities.py:30-46 (score_topic)`. `config/scoring.yaml` remains explicitly recorded as `weights_source`.
- Added the audit date, complete input list, reproduction instructions, explicit conclusion, expected weights, existing sample paths, and the unchanged sample fingerprint.
- Strengthened `tests/test_p2_3_audits.py` to verify the formula path/reference, weight mapping, input/sample paths and file existence, and recompute the fingerprint from ordered raw sample bytes.
- No weights, signals, topics, posts, or unrelated pre-existing changes were rewritten.

## Verification — Review Corrections

- Command: `PYTHONPATH=. pytest -q tests/test_p2_3_audits.py tests/test_score_opportunities.py`
- Output: `5 passed in 0.15s`

## Workspace Scope Note

- The global workspace diff contains pre-existing changes outside Task 1. Review of Task 1 must consider only the inventory YAML, its test, and this report.

## Verification — Requested Command

- Command: `PYTHONPATH=. pytest -q tests/test_p2_3_audits.py tests/test_score_opportunities.py`
- Output:

```text
.....                                                                    [100%]
5 passed in 0.04s
```
