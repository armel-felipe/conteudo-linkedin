# Task 7 report

## Follow-up fixes

- The LinkedIn target now receives the configured `accountId` from
  `ZERNIO_ACCOUNT_ID`.
- Image URLs require both an `http`/`https` scheme and a host; `https:` is
  rejected before the client is called.
- SQLite has a migrated `posts.zernio_post_id` column. A successful scheduling
  result records that ID in SQLite and Markdown.
- Result persistence is independent per store. After a network attempt, a
  failed write creates a non-sensitive sidecar recovery marker. The next call
  reconciles the known result and exits without issuing a second POST, so a
  record cannot be silently retried while still shown as approved.
- HTTP failures always surface as the sanitized `SchedulingError`; persistence
  errors and remote error details are not exposed.

## Tests and verification

- Red run after adding the regressions: missing `account_id` argument and
  `Database.record_schedule_result` caused the focused scheduling tests to
  fail before implementation.
- Focused: `PYTHONPATH=src python3 -m unittest tests.test_scheduling -v` — 12 passed.
- Full: `PYTHONPATH=src python3 -m unittest discover -s tests -v` — 61 passed.
- `git diff --check` — passed.
- All POST behavior is exercised by `FakeClient`; no real Zernio POST was made.
