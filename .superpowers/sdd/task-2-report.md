# Task 2 Report

## Status

Complete. Task 3 was not started.

## Commits

- `3fb8ee2 fix: close orchestration database bypasses`
- A correction commit and a separate report-only commit contain the final changes.

## Changes

- Routed public database cycle, review, completion, and validation writes through the fail-closed orchestration guards.
- Rejected unscoped or arbitrary `block_completed` persistence, including closed rounds and out-of-order blocks.
- Counted `human_completed` as a completed workflow block so B7 releases B8 without automatic reviewer approval.
- Persisted the artifact in completion event payloads.
- Updated fixtures and direct API coverage for contextual artifacts, cycles, reviews, and legacy `bloco-ok` rejection.
- Rejected all generic `record_workflow_event()` writes so cycle, review, automatic completion, and human completion events can only be persisted by domain APIs.
- Required `record_human_completion()` to match an existing B7 cycle and persist round/block plus artifact, cycle, and selection context, without a reviewer receipt.
- Made `close_round()` fail closed until every required block, including human B7, is complete.
- Made compatibility persistence atomic: `record_block_validation()` now uses one domain transaction for `block_completed` and `block_validations`, with rollback coverage when the compatibility insert fails.

## Commands and Results

- `python3.12 -m pytest tests/test_orchestration.py tests/test_cli_smoke.py tests/test_db.py -v` -> `51 passed, 37 subtests passed`
- `python3.12 -m pytest -q` -> `145 passed, 40 subtests passed`
- The atomic compatibility rollback regression is included in the Task 2 suite.
- Required final verification is run after this report is committed.

## Concerns

- `record_block_validation` remains a compatibility API and writes the legacy `block_validations` row after the central completion gate; new workflow callers should use `workflow-block-complete` or the contextual orchestration API.
