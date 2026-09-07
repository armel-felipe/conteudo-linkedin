# Task 2 Report: Audit source quality

## Status

DONE for the Task 2 scope. The source-quality audit artifact and its contract test were created without changing the signals or topics files.

## Changes

- Created `research/audits/source-quality-2026-09-06.yaml`.
- Updated `tests/test_p2_3_audits.py` with `test_source_audit_classifies_every_sampled_signal`.
- Audited all four sources referenced by `topic_20260901_04`.
- Added a representative five-source sample covering panels, community discussion, primary research and a primary technical artifact.
- Classified each source with `source_id`, `type`, `independence`, `recency`, `verifiability`, `topic_connection`, `quality`, `justification`, `limitations` and `inference_risk`.
- Preserved the source title, URL and publication date from the signal records as each verification record, with exact-match tests.
- Reclassified `signal_20260901_006` and `signal_20260901_017` as `indirect_limited` connections to manufacturing and documented the limitation in each justification.
- Strengthened the audit test to require the four topic signals, the five representative signals, unique IDs and exact title/URL/date correspondence.

## TDD Evidence

### RED

Command:

```text
PYTHONPATH=. pytest -q tests/test_p2_3_audits.py::test_source_audit_classifies_every_sampled_signal
```

Result: failed because `research/audits/source-quality-2026-09-06.yaml` did not exist.

### GREEN

Command:

```text
PYTHONPATH=. pytest -q tests/test_p2_3_audits.py::test_source_audit_classifies_every_sampled_signal
```

Result: `1 passed`.

## Audit Method

- The audit uses only the existing signal metadata and recorded observations/evidence.
- Panels were kept separate from vendor marketing, secondary reporting, community discussion and primary research.
- Missing methodology, baseline, sample, participant details, transcript or measured outcome was recorded as a limitation.
- The artifact does not treat a signal observation as independent validation of the underlying claim.
- Risk labels are conservative: high or very high risk is used when the record is promotional, anecdotal, quantitatively unsupported or not directly connected to the manufacturing topic.

## Verification

Targeted test:

```text
PYTHONPATH=. pytest -q tests/test_p2_3_audits.py
```

Result: passed, `2 passed in 0.06s`.

Focused audit contract test:

```text
PYTHONPATH=. pytest -q tests/test_p2_3_audits.py::test_source_audit_classifies_every_sampled_signal
```

Result: passed, `1 passed in 0.06s`.

Full suite:

```text
PYTHONPATH=. pytest -q
```

Result: `285 passed, 2 failed`.

The two failures are outside this task's files and concern pre-existing scheduling work:

- `tests/test_scheduling_checklist.py::test_checklist_registration_gate_has_explicit_types_and_failure_state` because the existing checklist has `timestamp_registered: true` instead of `false`.
- `tests/test_scheduling_skill.py::test_manual_scheduling_matrix_and_receipt_are_non_sensitive_and_complete` because the existing roadmap lacks the expected phrase `não foram executados`.

## Concerns

- The audit is a classification of the evidence captured in signals, not an external fact-check or source-content re-fetch.
- Several sources lack methodology, baseline, sample, transcript or measured outcome; those gaps are explicitly recorded and increase inference risk.
- The full suite remains non-green due to the two unrelated scheduling failures listed above.
- No signals or topics were altered by this task.
