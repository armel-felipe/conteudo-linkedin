const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const {
  browserRouteOrder,
  inspectPage,
  main,
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

test('logs MCP-first browser execution without calling Playwright', async () => {
  const logPath = path.join(os.tmpdir(), `browser-${Date.now()}-mcp.jsonl`);
  const result = await runBrowserCheck({
    mcpAdapterFactory: async () => ({
      inspect: async () => ({ ok: true, report: { visual_state: 'public_page' } }),
    }),
    playwrightAdapterFactory: async () => {
      throw new Error('must not be called');
    },
    logPath,
    runId: 'browser-run-1',
  });
  assert.equal(result.effective_route, 'mcp_chrome_devtools');
  assert.equal(result.events[0].event, 'started');
  assert.equal(result.events.at(-1).event, 'completed');
});

test('logs fallback reason and never logs adapter secrets', async () => {
  const logPath = path.join(os.tmpdir(), `browser-${Date.now()}-fallback.jsonl`);
  const result = await runBrowserCheck({
    mcpAdapterFactory: async () => ({
      inspect: async () => ({
        ok: false,
        reason: 'mcp_unavailable',
        details: { api_key: 'secret' },
      }),
    }),
    playwrightAdapterFactory: async () => ({
      inspect: async () => ({ ok: true, report: { visual_state: 'ok' } }),
    }),
    logPath,
    runId: 'browser-run-2',
  });
  assert.equal(result.effective_route, 'playwright_fallback');
  assert.equal(result.route_reasons.mcp_chrome_devtools, 'mcp_unavailable');
  assert.equal(JSON.stringify(result.events).includes('secret'), false);
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
  const { log_path: logPath, events, ...core } = result;
  assert.deepEqual(core, {
    attempted_routes: ['mcp_chrome_devtools'],
    effective_route: 'mcp_chrome_devtools',
    reason: 'mcp_success',
    route_reasons: { mcp_chrome_devtools: 'mcp_success' },
    observed_state: report.visual_state,
    report,
  });
  assert.ok(logPath.endsWith('browser-check.jsonl'));
  assert.deepEqual(events.map((event) => event.event), ['started', 'completed']);
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
  const { log_path: logPath, events, ...core } = result;
  assert.deepEqual(core, {
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
  assert.ok(logPath.endsWith('browser-check.jsonl'));
  assert.deepEqual(events.map((event) => event.event), ['started', 'fallback', 'completed']);
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

test('fails closed on an ambiguous MCP exception without constructing Playwright', async () => {
  let playwrightConstructed = false;
  const error = Object.assign(new Error('MCP disconnected after action'), {
    ambiguous: true,
    observed_state: { mutation: 'possibly_sent' },
  });
  const result = await runBrowserCheck({
    mcpAdapter: { inspect: async () => { throw error; } },
    playwrightAdapterFactory: async () => {
      playwrightConstructed = true;
      throw new Error('must not construct Playwright');
    },
  });

  assert.equal(playwrightConstructed, false);
  assert.equal(result.effective_route, 'stop');
  assert.equal(result.reason, 'ambiguous_mutation');
  assert.equal(result.mutation_confirmed, true);
  assert.deepEqual(result.observed_state, error.observed_state);
});

test('fails closed on an ambiguous MCP return without constructing Playwright', async () => {
  let playwrightConstructed = false;
  const result = await runBrowserCheck({
    mcpAdapter: {
      inspect: async () => ({
        ok: false,
        ambiguous: true,
        reason: 'mcp_result_ambiguous',
        observed_state: { mutation: 'unknown' },
      }),
    },
    playwrightAdapterFactory: async () => {
      playwrightConstructed = true;
      return { inspect: async () => ({ ok: true }) };
    },
  });

  assert.equal(playwrightConstructed, false);
  assert.equal(result.reason, 'ambiguous_mutation');
  assert.deepEqual(result.observed_state, { mutation: 'unknown' });
});

test('fails closed on an MCP ambiguous_mutation reason without constructing Playwright', async () => {
  let playwrightConstructed = false;
  const result = await runBrowserCheck({
    mcpAdapter: {
      inspect: async () => ({
        ok: false,
        reason: 'ambiguous_mutation',
        observed_state: { mutation: 'unknown' },
      }),
    },
    playwrightAdapterFactory: async () => {
      playwrightConstructed = true;
      return { inspect: async () => ({ ok: true }) };
    },
  });

  assert.equal(playwrightConstructed, false);
  assert.equal(result.reason, 'ambiguous_mutation');
  assert.equal(result.effective_route, 'stop');
  assert.deepEqual(result.observed_state, { mutation: 'unknown' });
});

test('main accepts an injected MCP adapter through the operational entrypoint', async () => {
  const previousLog = console.log;
  const logs = [];
  console.log = (value) => logs.push(JSON.parse(value));
  try {
    const result = await main({
      mcpAdapter: {
        inspect: async () => ({ ok: true, report: { visual_state: { ready_state: 'complete' } } }),
      },
      playwrightAdapterFactory: async () => {
        throw new Error('must not construct Playwright');
      },
    });
    assert.equal(result.effective_route, 'mcp_chrome_devtools');
    assert.deepEqual(logs, [result]);
  } finally {
    console.log = previousLog;
  }
});

test('main accepts an injected MCP adapter factory through the operational entrypoint', async () => {
  let factoryCalls = 0;
  const result = await main({
    mcpAdapterFactory: async () => {
      factoryCalls += 1;
      return { inspect: async () => ({ ok: true }) };
    },
    playwrightAdapterFactory: async () => {
      throw new Error('must not construct Playwright');
    },
  });
  assert.equal(factoryCalls, 1);
  assert.equal(result.effective_route, 'mcp_chrome_devtools');
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
