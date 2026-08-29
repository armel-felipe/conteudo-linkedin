# Final Fix 3 Report

## Status

Corrected `contentctl posts sync` status messaging after a remote publication
sync maps a post to `failed`.

## Root cause and change

`sync_published_post` already persisted a remote `FAILED` response as local
`failed`, but retained its backwards-compatible boolean return value, where
both `scheduled` and `failed` evaluate as non-published. The CLI therefore
printed "remains scheduled" for both states.

The CLI now reads the persisted status after synchronization through the new
`Database.post_status` read helper and maps the three possible sync outcomes to
their explicit messages:

- `scheduled` → `Post <id> remains scheduled.`
- `published` → `Post <id> is published.`
- `failed` → `Post <id> failed.`

The public return contract of `sync_published_post` is unchanged.

## TDD evidence

Added the CLI end-to-end regression test for a remote `FAILED` response. Before
the implementation it failed with:

```text
Post 1 remains scheduled.
```

After the change, the focused command passed:

```sh
PYTHONPATH=src python -m unittest \
  tests.test_cli_end_to_end.EditorialCliEndToEndTests.test_posts_sync_reports_failed_when_remote_post_failed \
  tests.test_reporting
```

```text
Ran 9 tests
OK
```

## Full verification

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
```

```text
Ran 92 tests
OK
```

No real network request was made; the Zernio client was a test double.

## Follow-up reviewer fixes

The orchestration protocol now persists sanitized `blocked` events for completion
gates, cycle/order/round failures, unreadable artifacts during start or review,
and automatic B7 approval attempts. `resume_round` returns `blocked` for an
unknown round. `ReviewResult` feedback must be a non-empty list of objects with
non-empty `contract`, `problem`, and `required_change`; approved results must
have empty feedback.

Regression coverage was added in `tests/test_orchestration.py`, with existing
database fixtures updated to the stricter review schema.

Verification: `python3.12 -m pytest -q` passed with 188 tests and 40 subtests;
`python3.12 -m compileall -q src tests`, `git diff --check`, and
`./contentctl --help` also passed.

Concerns: an unknown round cannot receive an event because no valid foreign-key
target exists; its mutation error remains preserved while `resume_round`
returns `blocked`.
