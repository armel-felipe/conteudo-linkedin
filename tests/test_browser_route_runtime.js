const test = require('node:test');
const assert = require('node:assert/strict');

const {
  browserRouteOrder,
  runBrowserCheck,
  resolveBrowserRoute,
} = require('../scripts/linkedin_browser_check.js');

test('embedded browser is primary without requiring Playwright', async () => {
  const calls = [];
  const result = await runBrowserCheck({
    visualAdapter: {
      inspect: async () => {
        calls.push('visual');
        return { ok: true, report: { visual_state: 'native_confirmed' } };
      },
    },
    playwrightAdapter: {
      inspect: async () => {
        calls.push('playwright');
        throw new Error('must not run');
      },
    },
  });
  assert.deepEqual(calls, ['visual']);
  assert.equal(result.effective_route, 'browser_native');
});

test('route order keeps Playwright as read-only diagnostic fallback', () => {
  assert.deepEqual(browserRouteOrder(), [
    'browser_native',
    'image-analyzer',
    'playwright',
    'stop',
  ]);
});

test('Playwright result identifies mutation_allowed false', () => {
  const result = resolveBrowserRoute({
    visualAttempt: { ok: false, reason: 'native_failed' },
    playwrightAttempt: { ok: true, report: { visual_state: 'read_only' } },
  });
  assert.equal(result.effective_route, 'playwright');
  assert.equal(result.report.mutation_allowed, false);
});
