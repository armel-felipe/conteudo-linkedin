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
