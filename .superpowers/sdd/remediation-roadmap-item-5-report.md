# Remediation Roadmap Item 5 Report

## Status

Item 5 is limited to the timestamp-registration semantic-failure gate. Items 1-4
were not reopened. No LinkedIn browser session or mutating action was used.

## Root Cause

`can_register_timestamp` used `bool(confirmation and scheduled_list)`. Python
truthiness made non-empty failure strings such as `"fail"` pass the registration
gate. The helper also had no explicit validation boundary for receipt evidence,
summary status, timestamp equality, or failure states.

## TDD

RED added regressions for semantic failure strings, invalid types, empty and
inconsistent timestamps, invalid receipts, `simulated`/`not_run`/`blocked`
states, and a complete valid gate. The focused test run failed before the
implementation with the expected truthiness and unexpected-keyword failures.

GREEN changed only `scheduling_contract.py` and the scheduling contract tests:

- confirmation and scheduled-list flags require exact boolean `True`;
- the complete gate validates the structured receipt and requires real evidence;
- summary and timestamp values are explicit, non-empty, and equal;
- `timestamp_registered` requires exact boolean `True`;
- any failure state returns `False` without coercion.

## Contract Alignment

The scheduling checklist now declares summary/confirmation/receipt fields,
requested and displayed timestamps, and a nullable failure state. The publishing
skill documents the literal fail-closed gate and rejects truthy strings. The
roadmap records the semantic-failure sub-item as complete.

## Verification

The focused scheduling tests pass after GREEN. The full suite, `npm test`,
`compileall`, `git diff --check`, and the Loop Gauntlet are run as part of the
completion gate; their final output is recorded in the task response.

## Scope Concerns

- `gauntlet_loop.py`, `editorial_batch.py`, scheduled content, and LinkedIn
  actions were not changed.
- The simple two-argument helper remains available for existing boolean-only
  checks; supplying any evidence metadata activates the complete explicit gate.
