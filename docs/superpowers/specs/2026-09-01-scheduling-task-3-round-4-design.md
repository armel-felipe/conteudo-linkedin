# Scheduling Task 3 Round 4 Design

## Scope

Harden the scheduling receipt and test evidence for five scenarios without
performing any mutating LinkedIn action. The only permitted browser validation
is inspection of the existing scheduled post and, if needed, entering the
`... -> Alterar agenda` path without confirming a change.

## Evidence contract

Every scenario in the report has exactly one `evidence_status`:

- `real_non_destructive`: browser evidence from a dry-run that cannot mutate a
  publication.
- `real_existing_post`: browser evidence limited to the existing post path.
- `simulated`: contract/test-only behavior, with no browser claim.
- `not_run`: intentionally omitted for safety or unavailable evidence.

Receipts must include the status and may not claim `confirmation`,
`scheduled_list`, or `timestamp_registered` for a dry-run. Existing-post
evidence records navigation only; it does not record a second schedule change.

## Dry-run protocol

The protocol selects the requested date and time, verifies the displayed
summary, and stops before `Avançar`. It must explicitly record the stop and
reject any attempt to continue. Scenarios requiring creation, deletion,
publication, scheduling, or changing a publication are documented as
`not_run`, unless the existing-post navigation itself is being inspected.

## Verification

Pure tests cover status allowlisting, status-specific receipt gates, the
pre-`Avançar` dry-run sequence, and all five scenario classifications. The
round-4 report records actual execution and safety concerns without claiming
unperformed browser actions.
