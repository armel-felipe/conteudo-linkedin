const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const {
  browserRouteOrder,
  inspectPage,
  runBrowserCheck,
  resolveBrowserRoute,
  selectLinkedInPage,
  visualFallbackOrder,
} = require('../scripts/linkedin_browser_check.js');

const page = (url) => ({ url: () => url });

test('declares MCP Chrome DevTools before Playwright', () => {
  assert.deepEqual(browserRouteOrder(), [
    'mcp_chrome_devtools',
    'playwright_fallback',
    'stop',
  ]);
});

test('uses Playwright fallback when MCP is unavailable before mutation', () => {
  assert.deepEqual(resolveBrowserRoute({
    mcpAttempt: { ok: false, reason: 'mcp_unavailable' },
    playwrightAttempt: { ok: true, report: { visual_state: {} } },
  }), {
    attempted_routes: ['mcp_chrome_devtools', 'playwright_fallback'],
    effective_route: 'playwright_fallback',
    reason: 'mcp_unavailable',
    route_reasons: {
      mcp_chrome_devtools: 'mcp_unavailable',
      playwright_fallback: 'playwright_success',
    },
    observed_state: {},
  });
});

test('stops after an ambiguous possible mutation', () => {
  assert.deepEqual(resolveBrowserRoute({
    mcpAttempt: { ok: false, reason: 'mcp_failed' },
  }), {
    attempted_routes: ['mcp_chrome_devtools'],
    effective_route: 'stop',
    reason: 'mcp_failed',
    route_reasons: { mcp_chrome_devtools: 'mcp_failed' },
    observed_state: null,
  });
});

test('does not permit fallback after a confirmed mutation', () => {
  assert.deepEqual(resolveBrowserRoute({
    mcpAttempt: { ok: false, reason: 'mcp_failed', mutation_confirmed: true },
  }), {
    attempted_routes: ['mcp_chrome_devtools'],
    effective_route: 'stop',
    reason: 'ambiguous_mutation',
    route_reasons: { mcp_chrome_devtools: 'ambiguous_mutation' },
    observed_state: null,
    mutation_confirmed: true,
  });
});

test('runs an injected MCP adapter before the Playwright fallback', async () => {
  const calls = [];
  const report = { url: 'https://www.linkedin.com/feed/', visual_state: { ready_state: 'complete' } };
  const result = await runBrowserCheck({
    mcpAdapter: {
      inspect: async () => {
        calls.push('mcp');
        return { ok: true, report };
      },
    },
    playwrightAdapterFactory: async () => {
      calls.push('playwright-factory');
      throw new Error('Playwright must not be constructed');
    },
  });

  assert.deepEqual(calls, ['mcp']);
  assert.deepEqual(result, {
    attempted_routes: ['mcp_chrome_devtools'],
    effective_route: 'mcp_chrome_devtools',
    reason: 'mcp_success',
    route_reasons: { mcp_chrome_devtools: 'mcp_success' },
    observed_state: report.visual_state,
    report,
  });
});

test('uses a controlled Playwright fallback only after an injected MCP failure', async () => {
  const calls = [];
  const report = { url: 'https://www.linkedin.com/feed/', visual_state: { ready_state: 'complete' } };
  const result = await runBrowserCheck({
    mcpAdapter: {
      inspect: async () => {
        calls.push('mcp');
        return { ok: false, reason: 'mcp_unavailable', mutation_confirmed: false };
      },
    },
    playwrightAdapterFactory: async () => {
      calls.push('playwright-factory');
      return { inspect: async () => { calls.push('playwright'); return report; } };
    },
  });

  assert.deepEqual(calls, ['mcp', 'playwright-factory', 'playwright']);
  assert.deepEqual(result, {
    attempted_routes: ['mcp_chrome_devtools', 'playwright_fallback'],
    effective_route: 'playwright_fallback',
    reason: 'mcp_unavailable',
    route_reasons: {
      mcp_chrome_devtools: 'mcp_unavailable',
      playwright_fallback: 'playwright_success',
    },
    observed_state: report.visual_state,
    report,
  });
});

test('stops and preserves ambiguous state when Playwright inspection returns it', async () => {
  const observedState = { mutation: 'possibly_sent', composer: 'unknown' };
  const result = await runBrowserCheck({
    mcpAdapter: { inspect: async () => ({ ok: false, reason: 'mcp_unavailable' }) },
    playwrightAdapterFactory: async () => ({
      inspect: async () => ({
        ok: false,
        reason: 'post_action_state_unknown',
        mutation_confirmed: true,
        observed_state: observedState,
      }),
    }),
  });

  assert.equal(result.effective_route, 'stop');
  assert.equal(result.reason, 'ambiguous_mutation');
  assert.equal(result.mutation_confirmed, true);
  assert.deepEqual(result.observed_state, observedState);
});

test('stops and preserves ambiguous state when Playwright adapter throws', async () => {
  const error = Object.assign(new Error('connection lost after submit'), {
    mutation_confirmed: true,
    observed_state: { mutation: 'possibly_sent' },
  });
  const result = await runBrowserCheck({
    mcpAdapter: { inspect: async () => ({ ok: false, reason: 'mcp_unavailable' }) },
    playwrightAdapterFactory: async () => ({ inspect: async () => { throw error; } }),
  });

  assert.equal(result.effective_route, 'stop');
  assert.equal(result.reason, 'ambiguous_mutation');
  assert.equal(result.mutation_confirmed, true);
  assert.deepEqual(result.observed_state, error.observed_state);
});

function fixturePage(url) {
  const calls = [];
  return {
    calls,
    url: () => url,
    title: async () => {
      calls.push('title');
      return 'LinkedIn fixture';
    },
    evaluate: async () => {
      calls.push('evaluate');
      return { visibility: 'visible', ready_state: 'complete', body_present: true };
    },
    screenshot: async ({ path: screenshotPath }) => {
      calls.push(['screenshot', screenshotPath]);
      fs.writeFileSync(screenshotPath, 'fixture');
    },
    click: () => { throw new Error('click must not be called'); },
    fill: () => { throw new Error('fill must not be called'); },
    goto: () => { throw new Error('navigate must not be called'); },
  };
}

test('selects a LinkedIn target and ignores unrelated pages', () => {
  const selected = selectLinkedInPage([
    page('https://example.test/'),
    page('https://www.linkedin.com/feed/'),
  ]);

  assert.equal(selected.url(), 'https://www.linkedin.com/feed/');
});

test('fails closed when every target is about:blank', () => {
  assert.throws(
    () => selectLinkedInPage([page('about:blank')]),
    /LinkedIn target not found/,
  );
});

test('fails closed when no target exists', () => {
  assert.throws(() => selectLinkedInPage([]), /LinkedIn target not found/);
});

test('does not mistake a lookalike hostname for LinkedIn', () => {
  assert.throws(
    () => selectLinkedInPage([page('https://evillinkedin.com/')]),
    /LinkedIn target not found/,
  );
});

test('inspects a real Page fixture without mutating it or taking an unrequested screenshot', async () => {
  const target = fixturePage('https://www.linkedin.com/feed/');
  const previous = process.env.OPENWORK_BROWSER_SCREENSHOT_PATH;
  delete process.env.OPENWORK_BROWSER_SCREENSHOT_PATH;

  try {
    const report = await inspectPage(target);
    assert.deepEqual(report, {
      url: 'https://www.linkedin.com/feed/',
      title: 'LinkedIn fixture',
      visual_state: { visibility: 'visible', ready_state: 'complete', body_present: true },
    });
    assert.deepEqual(target.calls, ['title', 'evaluate']);
  } finally {
    if (previous === undefined) delete process.env.OPENWORK_BROWSER_SCREENSHOT_PATH;
    else process.env.OPENWORK_BROWSER_SCREENSHOT_PATH = previous;
  }
});

test('takes a requested screenshot only in the temporary directory', async () => {
  const target = fixturePage('https://www.linkedin.com/feed/');
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'linkedin-check-'));
  const screenshotPath = path.join(directory, 'state.png');
  const previous = process.env.OPENWORK_BROWSER_SCREENSHOT_PATH;
  process.env.OPENWORK_BROWSER_SCREENSHOT_PATH = screenshotPath;

  try {
    const report = await inspectPage(target);
    assert.equal(report.screenshot_path, screenshotPath);
    assert.equal(fs.readFileSync(screenshotPath, 'utf8'), 'fixture');
    assert.deepEqual(target.calls, [
      'title',
      'evaluate',
      ['screenshot', screenshotPath],
    ]);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
    if (previous === undefined) delete process.env.OPENWORK_BROWSER_SCREENSHOT_PATH;
    else process.env.OPENWORK_BROWSER_SCREENSHOT_PATH = previous;
  }
});

test('inspectPage fails closed for an about:blank Page fixture', async () => {
  await assert.rejects(
    () => inspectPage(fixturePage('about:blank')),
    /LinkedIn target not found/,
  );
});

test('documents visual fallback downstream of the selected browser route', () => {
  const skill = fs.readFileSync(
    path.join(__dirname, '..', '.agents', 'skills', 'publicar-linkedin', 'SKILL.md'),
    'utf8',
  );
  assert.ok(skill.indexOf('capturar screenshot e usar visão nativa') < skill.indexOf('delegar ao `image-analyzer`'));
  assert.ok(skill.indexOf('reason: native_failed') >= 0);
});

test('keeps the visual fallback order explicit', () => {
  assert.deepEqual(visualFallbackOrder(), [
    'screenshot+nativa',
    'image-analyzer:native_failed',
    'stop',
  ]);
});
