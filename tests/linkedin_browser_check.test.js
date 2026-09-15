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

test('declares the visual route as primary and Playwright as the last fallback', () => {
  assert.deepEqual(browserRouteOrder(), [
    'browser_native',
    'image-analyzer',
    'playwright',
    'stop',
  ]);
});

test('executes the visual OpenWork route before Playwright fallback', async () => {
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
        return { ok: true, report: { visual_state: 'playwright_confirmed' } };
      },
    },
  });

  assert.deepEqual(calls, ['visual']);
  assert.equal(result.effective_route, 'browser_native');
});

test('logs Playwright execution after unavailable visual routes', async () => {
  const logPath = path.join(os.tmpdir(), `browser-${Date.now()}-pw.jsonl`);
  const result = await runBrowserCheck({
    playwrightAdapter: {
      inspect: async () => ({ ok: true, report: { visual_state: 'public_page' } }),
    },
    logPath,
    runId: 'browser-run-1',
  });
  assert.equal(result.effective_route, 'playwright');
  assert.deepEqual(result.attempted_routes, [
    'browser_native',
    'playwright',
  ]);
  assert.equal(result.events[0].event, 'started');
  assert.equal(result.events.at(-1).event, 'completed');
});

test('logs fallback reason and never logs adapter secrets', async () => {
  const logPath = path.join(os.tmpdir(), `browser-${Date.now()}-fallback.jsonl`);
  const result = await runBrowserCheck({
    playwrightAdapter: {
      inspect: async () => ({
        ok: false,
        reason: 'playwright_unavailable',
        details: { api_key: 'secret' },
      }),
    },
    visualAdapter: {
      inspect: async () => ({ ok: true, report: { visual_state: 'ok' } }),
    },
    logPath,
    runId: 'browser-run-2',
  });
  assert.equal(result.effective_route, 'browser_native');
  assert.deepEqual(result.attempted_routes, ['browser_native']);
  assert.equal(JSON.stringify(result.events).includes('secret'), false);
});

test('selects the visual route without consulting Playwright', () => {
  assert.deepEqual(resolveBrowserRoute({
    playwrightAttempt: { ok: false, reason: 'playwright_unavailable' },
    visualAttempt: { ok: true, report: { visual_state: {} } },
  }), {
    attempted_routes: ['browser_native'],
    effective_route: 'browser_native',
    reason: 'browser_native_success',
    route_reasons: {
      'browser_native': 'browser_native_success',
    },
    observed_state: {},
    report: { visual_state: {} },
  });
});

test('stops after an ambiguous possible mutation', () => {
  assert.deepEqual(resolveBrowserRoute({
    playwrightAttempt: { ok: false, reason: 'playwright_failed' },
  }), {
    attempted_routes: ['playwright'],
    effective_route: 'stop',
    reason: 'playwright_failed',
    route_reasons: { playwright: 'playwright_failed' },
    observed_state: null,
  });
});

test('does not permit fallback after a confirmed mutation', () => {
  assert.deepEqual(resolveBrowserRoute({
    playwrightAttempt: { ok: false, reason: 'playwright_failed', mutation_confirmed: true },
  }), {
    attempted_routes: ['playwright'],
    effective_route: 'stop',
    reason: 'ambiguous_mutation',
    route_reasons: { playwright: 'ambiguous_mutation' },
    observed_state: null,
    mutation_confirmed: true,
  });
});

test('runs an injected Playwright adapter only after visual routes are unavailable', async () => {
  const calls = [];
  const report = { mutation_allowed: false, url: 'https://www.linkedin.com/feed/', visual_state: { ready_state: 'complete' } };
  const result = await runBrowserCheck({
    playwrightAdapter: {
      inspect: async () => {
        calls.push('playwright');
        return { ok: true, report };
      },
    },
  });

  assert.deepEqual(calls, ['playwright']);
  const { log_path: logPath, events, ...core } = result;
  assert.deepEqual(core, {
    attempted_routes: ['browser_native', 'playwright'],
    effective_route: 'playwright',
    reason: 'playwright_success',
    route_reasons: {
      'browser_native': 'no_visual_adapter',
      playwright: 'playwright_success',
    },
    observed_state: report.visual_state,
    report,
  });
  assert.ok(logPath.endsWith('browser-check.jsonl'));
  assert.deepEqual(events.map((event) => event.event), ['started', 'fallback', 'completed']);
});

test('uses visual route before an injected Playwright adapter', async () => {
  const calls = [];
  const report = { mutation_allowed: false, url: 'https://www.linkedin.com/feed/', visual_state: { ready_state: 'complete' } };
  const result = await runBrowserCheck({
    playwrightAdapter: {
      inspect: async () => {
        calls.push('playwright');
        return { ok: false, reason: 'playwright_unavailable', mutation_confirmed: false };
      },
    },
    visualAdapter: {
      inspect: async () => { calls.push('visual'); return report; },
    },
  });

  assert.deepEqual(calls, ['visual']);
  const { log_path: logPath, events, ...core } = result;
  assert.deepEqual(core, {
    attempted_routes: ['browser_native'],
    effective_route: 'browser_native',
    reason: 'browser_native_success',
    route_reasons: {
      'browser_native': 'browser_native_success',
    },
    observed_state: report.visual_state,
    report,
  });
  assert.ok(logPath.endsWith('browser-check.jsonl'));
  assert.deepEqual(events.map((event) => event.event), ['started', 'completed']);
});

test('uses image-analyzer before Playwright when native vision fails', async () => {
  const calls = [];
  const result = await runBrowserCheck({
    visualAdapter: {
      inspect: async () => {
        calls.push('visual');
        return { ok: false, reason: 'native_failed' };
      },
    },
    imageAnalyzerAdapter: {
      inspect: async () => {
        calls.push('image-analyzer');
        return { ok: true, report: { visual_state: 'analyzer_confirmed' } };
      },
    },
    playwrightAdapter: {
      inspect: async () => {
        calls.push('playwright');
        return { ok: true };
      },
    },
  });

  assert.deepEqual(calls, ['visual', 'image-analyzer']);
  assert.equal(result.effective_route, 'image-analyzer');
  assert.deepEqual(result.attempted_routes, ['browser_native', 'image-analyzer']);
});

test('stops and preserves ambiguous state when Playwright inspection returns it', async () => {
  const observedState = { mutation: 'possibly_sent', composer: 'unknown' };
  const result = await runBrowserCheck({
    playwrightAdapter: {
      inspect: async () => ({
        ok: false,
        reason: 'post_action_state_unknown',
        mutation_confirmed: true,
        observed_state: observedState,
      }),
    },
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
    playwrightAdapter: { inspect: async () => { throw error; } },
  });

  assert.equal(result.effective_route, 'stop');
  assert.equal(result.reason, 'ambiguous_mutation');
  assert.equal(result.mutation_confirmed, true);
  assert.deepEqual(result.observed_state, error.observed_state);
});

test('fails closed on an ambiguous Playwright exception without visual fallback', async () => {
  let visualConstructed = false;
  const error = Object.assign(new Error('Playwright disconnected after action'), {
    ambiguous: true,
    observed_state: { mutation: 'possibly_sent' },
  });
  const result = await runBrowserCheck({
    playwrightAdapter: { inspect: async () => { throw error; } },
    visualAdapter: {
      inspect: async () => {
        visualConstructed = true;
        return { ok: false, reason: 'native_failed' };
      },
    },
  });

  assert.equal(visualConstructed, true);
  assert.equal(result.effective_route, 'stop');
  assert.equal(result.reason, 'ambiguous_mutation');
  assert.equal(result.mutation_confirmed, true);
  assert.deepEqual(result.observed_state, error.observed_state);
});

test('fails closed on an ambiguous Playwright return without visual fallback', async () => {
  let visualConstructed = false;
  const result = await runBrowserCheck({
    playwrightAdapter: {
      inspect: async () => ({
        ok: false,
        ambiguous: true,
        reason: 'playwright_result_ambiguous',
        observed_state: { mutation: 'unknown' },
      }),
    },
    visualAdapter: {
      inspect: async () => {
        visualConstructed = true;
        return { ok: false, reason: 'native_failed' };
      },
    },
  });

  assert.equal(visualConstructed, true);
  assert.equal(result.reason, 'ambiguous_mutation');
  assert.deepEqual(result.observed_state, { mutation: 'unknown' });
});

test('fails closed on an ambiguous_mutation reason without visual fallback', async () => {
  let visualConstructed = false;
  const result = await runBrowserCheck({
    playwrightAdapter: {
      inspect: async () => ({
        ok: false,
        reason: 'ambiguous_mutation',
        observed_state: { mutation: 'unknown' },
      }),
    },
    visualAdapter: {
      inspect: async () => {
        visualConstructed = true;
        return { ok: false, reason: 'native_failed' };
      },
    },
  });

  assert.equal(visualConstructed, true);
  assert.equal(result.reason, 'ambiguous_mutation');
  assert.equal(result.effective_route, 'stop');
  assert.deepEqual(result.observed_state, { mutation: 'unknown' });
});

test('main accepts an injected Playwright adapter through the operational entrypoint', async () => {
  const previousLog = console.log;
  const logs = [];
  console.log = (value) => logs.push(JSON.parse(value));
  try {
    const result = await main({
      playwrightAdapter: {
        inspect: async () => ({ ok: true, report: { visual_state: { ready_state: 'complete' } } }),
      },
    });
    assert.equal(result.effective_route, 'playwright');
    assert.deepEqual(logs, [result]);
  } finally {
    console.log = previousLog;
  }
});

test('main accepts an injected Playwright adapter factory through the operational entrypoint', async () => {
  let factoryCalls = 0;
  const result = await main({
    playwrightAdapterFactory: async () => {
      factoryCalls += 1;
      return { inspect: async () => ({ ok: true }) };
    },
  });
  assert.equal(factoryCalls, 1);
  assert.equal(result.effective_route, 'playwright');
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
      mutation_allowed: false,
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
    'browser_native',
    'image-analyzer',
    'stop',
  ]);
});
