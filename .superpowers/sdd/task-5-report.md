# Task 5 review fixes

## Changes

- SQLite now persists each pillar's `name`, `approved`, `count`, and JSON-encoded `evidence_ids`.
- Reproposal synchronizes SQLite with the proposed set and renders the same set to Markdown.
- Approval policy: a matching re-proposed name retains its approval; a name omitted by the new proposal is deleted, even when approved, because approvals apply only to the current editorial set.
- Fallback naming ranks terms by their actual token frequency with deterministic alphabetical tie-breaking.

## Regression coverage

- Persistence test asserts all four pillar fields after proposal and approval.
- Reproposal test verifies evidence/count refresh, removal from both SQLite and Markdown, and preservation of a matching approved pillar.

## Verification

- `PYTHONPATH=src python3 -m unittest tests.test_pillars -v` — 9 tests passed.
- `PYTHONPATH=src python3 -m unittest discover -s tests -v` — 32 tests passed.
