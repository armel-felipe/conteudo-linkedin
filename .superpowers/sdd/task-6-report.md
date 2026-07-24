# Task 6 report

## Implemented

- Added verbatim Last30days stdout capture, with no report written on a nonzero exit.
- Added persisted research-backed ideas that reject non-approved pillars.
- Added traceable Markdown drafts with non-approved metadata and required editorial fields.
- Added `research discover`, `ideas create`, and `draft create` commands to `contentctl`.
- Documented the no-synthesis and approved-pillar rules in `AGENTS.md`.

## TDD evidence

- Initial focused run: 5 errors caused by missing `content_ops.research` and
  `content_ops.workflow` modules.
- Green run: `PYTHONPATH=src python3 -m unittest tests.test_workflow -v` — 5 passed.
- Regression suite: `PYTHONPATH=src python3 -m unittest discover -s tests -v` — 46 passed.

## Notes

- Tests mock subprocess execution; no real Last30days command is run.
- `LAST30DAYS_COMMAND` remains local environment configuration and is never stored.

## Follow-up hardening

- `capture_research` now invokes the configured command with byte output and
  persists `stdout` via `write_bytes`, retaining newline, NUL, and non-UTF-8
  bytes exactly as emitted. Errors remain a concise exit-code exception and
  never rewrite or create a report.
- `Database.create_idea` enforces `pillars.approved = 1` in its own query, so
  callers cannot bypass the workflow check.
- `Database.create_draft_for_idea` validates the persisted idea, requires its
  pillar to remain approved, and rejects a requested pillar that differs from
  the idea before creating the draft post. `workflow.create_draft` delegates to
  that method and renders only persisted idea data.
- Regression coverage includes byte-exact output containing newline, NUL, and
  non-UTF-8 data, direct database idea creation with an unapproved pillar, and
  cross-pillar draft attempts through both workflow and database interfaces.

## Follow-up verification

- Focused: `PYTHONPATH=src python3 -m unittest tests.test_workflow -v` — 8 passed.
- Full: `PYTHONPATH=src python3 -m unittest discover -s tests -v` — 49 passed.
