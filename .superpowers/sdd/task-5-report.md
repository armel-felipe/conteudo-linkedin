# Task 5 synchronization hardening

## Changes

- Approval locates the exact `## <pillar>` section and changes only its own `approved` field. Repeating approval is idempotent and cannot cross into a later section.
- Markdown is staged in a temporary file in the target directory, `fsync`ed, and published with `replace`; a failed staging write leaves the visible document untouched.
- SQLite write transactions use `BEGIN IMMEDIATE`, serializing the approval-count read and update so concurrent approvals cannot both consume the final available slot.
- The protocol deliberately does not claim cross-store atomicity. It publishes staged Markdown before committing SQLite and, if the SQLite commit fails, restores the exact prior Markdown document before returning the failure.
- Reproposal removes obsolete pillars from both SQLite and Markdown. Before removal, it safely detaches linked ideas by setting `ideas.pillar_id` to `NULL`, preserving the idea and foreign-key integrity.

## Regression coverage

- Repeated approval changes only the targeted section, including when another pillar follows it.
- A simulated `fsync` failure after temporary-file writing leaves both the original Markdown and SQLite approval unchanged.
- A simulated SQLite commit failure after Markdown publication restores the original Markdown and leaves SQLite unapproved.
- The transaction test verifies that approval work starts with the serialized SQLite write lock.
- Reproposal of a pillar referenced by an idea detaches the idea and completes the synchronized removal.

## Verification

- `PYTHONPATH=src python3 -m unittest discover -s tests -v` — 39 tests passed.

## Final synchronization fixes

- A directory `fsync` failure after `os.replace` now carries an internal
  "published" signal, so the synchronization protocol restores the original
  Markdown before re-raising the original durability error; SQLite rolls back.
- The Markdown snapshot and document transformation now occur only after the
  serialized `BEGIN IMMEDIATE` lock is acquired. Concurrent approvals therefore
  compose from the latest committed Markdown rather than overwriting each other.
- Regression tests force the post-replace directory `fsync` failure and use a
  barrier that reproduces stale pre-lock reads in the old protocol.

## Final verification

- `PYTHONPATH=src python3 -m unittest tests.test_pillars.PillarPersistenceTests.test_approval_restores_markdown_when_directory_fsync_fails_after_replace tests.test_pillars.PillarPersistenceTests.test_concurrent_approvals_preserve_both_markdown_changes -v` — 2 tests passed.
- `PYTHONPATH=src python3 -m unittest discover -s tests -v` — 41 tests passed.
- `git diff --check` — passed.
