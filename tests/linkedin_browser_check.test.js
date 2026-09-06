const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const {
  browserRouteOrder,
  inspectPage,
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
    mcpAvailable: false,
    capabilityAvailable: false,
    mutationConfirmed: false,
    errorBeforeMutation: true,
  }), {
    route: 'playwright_fallback',
    reason: 'mcp_unavailable',
  });
});

test('stops after an ambiguous possible mutation', () => {
  assert.deepEqual(resolveBrowserRoute({
    mcpAvailable: true,
    capabilityAvailable: true,
    mutationConfirmed: false,
    errorBeforeMutation: false,
  }), {
    route: 'stop',
    reason: 'ambiguous_mutation',
  });
});

test('does not permit fallback after a confirmed mutation', () => {
  assert.deepEqual(resolveBrowserRoute({
    mcpAvailable: true,
    capabilityAvailable: true,
    mutationConfirmed: true,
    errorBeforeMutation: false,
  }), {
    route: 'stop',
    reason: 'ambiguous_mutation',
  });
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
