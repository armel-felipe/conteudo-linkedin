# Remediation Failure 4 Report

## Status

Approved by the requested quality gates: coverage >= 0.99 for the artifact
review gate, all applicable criteria >= 9/10, and zero open hard, critical, or
important findings. Code coverage is reported separately below.

## Scope

Only the non-mutating LinkedIn browser observation route, its skill guidance,
behavioral tests, and Node dependency metadata were changed. `gauntlet_loop.py`,
editorial batch behavior, approved/scheduled content, and LinkedIn mutation
actions were not changed or executed.

## Root Cause

The repository had no `package.json`, no portable browser-check script, no
Playwright dependency, and no Node behavioral tests. Consequently the skill's
Playwright-first route was documentation-only and could not select a valid
LinkedIn CDP target or fail closed on `about:blank`/missing targets.

## RED

Added tests for LinkedIn target selection, `about:blank` rejection, absent-target
rejection, lookalike-host rejection, and explicit visual fallback ordering.

Initial focused output:

```text
Error: Cannot find module '../scripts/linkedin_browser_check.js'
```

This reproduced the structural failure before implementation.

## GREEN

- Added `package.json` and `package-lock.json` with portable `linkedin:check` and
  `test` scripts plus the Playwright devDependency.
- Added `scripts/linkedin_browser_check.js`, using
  `chromium.connectOverCDP(process.env.OPENWORK_BROWSER_CDP_URL || 'http://127.0.0.1:9223')`.
- The script selects only exact `linkedin.com` or `.linkedin.com` hosts,
  reports URL/title/visual state, fails closed without a valid target, and does
  not click or mutate the page.
- Screenshots are disabled by default and allowed only through an explicit
  `OPENWORK_BROWSER_SCREENSHOT_PATH` inside the temporary directory.
- Updated `publicar-linkedin` to run the script/Playwright route first, then
  screenshot/native vision, then `image-analyzer(native_failed)`.
- `inspectPage` now validates its Page as a LinkedIn target before reading
  title/state or taking a screenshot.

## Remediation Round 2

### RED

Added real Page fixtures with call recording. The focused RED run was:

```text
8 passed, 1 failed
```

The failing regression showed that `inspectPage` accepted an `about:blank`
fixture instead of failing closed.

### GREEN

- `inspectPage` now calls `selectLinkedInPage` before any Page inspection.
- Tests prove no `click`, `fill`, or `goto` call occurs.
- Tests prove screenshots are absent by default and occur only when an
  explicit temporary path is supplied.
- The fallback order is asserted from both the executable contract and the
  skill documentation, without invoking an external analyzer.

## Coverage

The repository does not configure a JavaScript coverage tool. No code-coverage
percentage is claimed. The project gate `coverage >= 0.99` applies to Gauntlet
artifact reviews, not to code coverage.

## Verification

```text
node --test tests/linkedin_browser_check.test.js
9 passed, 0 failed

npm test
9 passed, 0 failed

PYTHONPATH=. pytest -q
172 passed in 0.99s

python3 -m compileall -q gauntlet_loop.py tests
git diff --check
```

## Gauntlet

The remediation was evaluated in one isolated RED/GREEN round, within the
maximum five rounds. Deterministic checks passed: target selection, fail-closed
blank/absent behavior, hostname boundary, fallback order, dependency metadata,
and diff scope. No LinkedIn browser session was opened and no mutating action
was attempted.

## Files

- `package.json`
- `package-lock.json`
- `scripts/linkedin_browser_check.js`
- `tests/linkedin_browser_check.test.js`
- `.agents/skills/publicar-linkedin/SKILL.md`
- `.superpowers/sdd/remediation-failure-4-report.md`

## Concerns

- A real CDP smoke test was not run because it would require an available
  browser session; the script's connection failure remains non-mutating.
- Screenshot behavior is covered by a local Page fixture, not a real browser.

## Real smoke verification

After the browser tab was restored, the real Playwright/CDP smoke test was
executed without mutation:

```text
npm run linkedin:check
{"url":"https://www.linkedin.com/feed/","title":"Feed | LinkedIn","visual_state":{"visibility":"visible","ready_state":"complete","body_present":true}}
```

An explicit temporary screenshot was also captured through the Playwright
route. Native visual inspection confirmed the LinkedIn feed and the visible
"Começar publicação" entry point. No click, fill, navigation, scheduling or
publication action was performed during this smoke test.

The previous about:blank condition is therefore resolved for the current
session. The non-mutating route is now verified both with fixtures and against
a live OpenWork CDP target.
