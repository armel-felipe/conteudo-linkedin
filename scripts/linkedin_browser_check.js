const os = require('node:os');
const path = require('node:path');
const { createExecutionLogger } = require('./execution_log.js');

const DEFAULT_CDP_URL = 'http://127.0.0.1:9223';

function selectLinkedInPage(pages) {
  const selected = pages.find((candidate) => {
    try {
      const hostname = new URL(candidate.url()).hostname;
      return hostname === 'linkedin.com' || hostname.endsWith('.linkedin.com');
    } catch {
      return false;
    }
  });

  if (!selected) {
    throw new Error('LinkedIn target not found (about:blank or no target)');
  }
  return selected;
}

function browserRouteOrder() {
  return ['playwright', 'screenshot+nativa', 'image-analyzer', 'stop'];
}

function resolveBrowserRoute({
  playwrightAttempt,
  visualAttempt = null,
}) {
  const attemptedRoutes = ['playwright'];
  const pw = playwrightAttempt || {};
  if (
    pw.mutation_confirmed
    || pw.ambiguous === true
    || pw.reason === 'ambiguous_mutation'
  ) {
    return {
      attempted_routes: attemptedRoutes,
      effective_route: 'stop',
      reason: 'ambiguous_mutation',
      route_reasons: { playwright: 'ambiguous_mutation' },
      observed_state: pw.observed_state || null,
      mutation_confirmed: true,
    };
  }
  if (pw.ok === true) {
    return {
      attempted_routes: attemptedRoutes,
      effective_route: 'playwright',
      reason: 'playwright_success',
      route_reasons: { playwright: 'playwright_success' },
      observed_state: pw.report?.visual_state || pw.observed_state || null,
    };
  }
  if (!visualAttempt) {
    return {
      attempted_routes: attemptedRoutes,
      effective_route: 'stop',
      reason: pw.reason || 'playwright_failed',
      route_reasons: { playwright: pw.reason || 'playwright_failed' },
      observed_state: pw.observed_state || null,
    };
  }
  attemptedRoutes.push('screenshot+nativa');
  if (visualAttempt.mutation_confirmed) {
    return {
      attempted_routes: attemptedRoutes,
      effective_route: 'stop',
      reason: 'ambiguous_mutation',
      route_reasons: {
        playwright: pw.reason || 'playwright_failed',
        'screenshot+nativa': 'ambiguous_mutation',
      },
      observed_state: visualAttempt.observed_state || null,
      mutation_confirmed: true,
    };
  }
  if (visualAttempt.ok === true) {
    return {
      attempted_routes: attemptedRoutes,
      effective_route: 'screenshot+nativa',
      reason: pw.reason || 'playwright_failed',
      route_reasons: {
        playwright: pw.reason || 'playwright_failed',
        'screenshot+nativa': 'visual_success',
      },
      observed_state: visualAttempt.report?.visual_state || visualAttempt.observed_state || null,
    };
  }
  // visualAttempt falhou -> tentar image-analyzer
  attemptedRoutes.push('image-analyzer');
  if (visualAttempt.image_analyzer_ok === true) {
    return {
      attempted_routes: attemptedRoutes,
      effective_route: 'image-analyzer',
      reason: visualAttempt.reason || 'native_failed',
      route_reasons: {
        playwright: pw.reason || 'playwright_failed',
        'screenshot+nativa': visualAttempt.reason || 'native_failed',
        'image-analyzer': 'image_analyzer_success',
      },
      observed_state: visualAttempt.observed_state || null,
    };
  }
  return {
    attempted_routes: attemptedRoutes,
    effective_route: 'stop',
    reason: visualAttempt.reason || 'image_analyzer_failed',
    route_reasons: {
      playwright: pw.reason || 'playwright_failed',
      'screenshot+nativa': visualAttempt.reason || 'native_failed',
      'image-analyzer': visualAttempt.reason || 'image_analyzer_failed',
    },
    observed_state: visualAttempt.observed_state || null,
  };
}

function normalizePlaywrightAttempt(value) {
  if (value && typeof value === 'object' && 'ok' in value) return value;
  return { ok: true, report: value };
}

function visualFallbackOrder() {
  return ['screenshot+nativa', 'image-analyzer', 'stop'];
}

function screenshotPathFromEnvironment(value = process.env.OPENWORK_BROWSER_SCREENSHOT_PATH) {
  if (!value) return null;
  const resolved = path.resolve(value);
  const temporaryRoot = path.resolve(os.tmpdir()) + path.sep;
  if (!resolved.startsWith(temporaryRoot)) {
    throw new Error('Screenshot path must be an explicit path inside the temporary directory');
  }
  return resolved;
}

async function inspectPage(page) {
  selectLinkedInPage([page]);
  const report = {
    url: page.url(),
    title: await page.title(),
    visual_state: await page.evaluate(() => ({
      visibility: document.visibilityState,
      ready_state: document.readyState,
      body_present: Boolean(document.body),
    })),
  };

  const screenshotPath = screenshotPathFromEnvironment();
  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath });
    report.screenshot_path = screenshotPath;
  }
  return report;
}

async function defaultPlaywrightAdapterFactory() {
  const { chromium } = require('playwright');
  const browser = await chromium.connectOverCDP(
    process.env.OPENWORK_BROWSER_CDP_URL || DEFAULT_CDP_URL,
  );
  try {
    const pages = browser.contexts().flatMap((context) => context.pages());
    const linkedinPage = selectLinkedInPage(pages);
    return {
      inspect: async () => inspectPage(linkedinPage),
      close: async () => browser.close(),
    };
  } catch (error) {
    await browser.close();
    throw error;
  }
}

/**
 * Playwright adapter contract: inspect() returns { ok, report?, reason?,
 * mutation_confirmed?, observed_state? }. It is injected so tests never need
 * credentials or a remote connection.
 */
async function runBrowserCheck({
  playwrightAdapter,
  playwrightAdapterFactory = defaultPlaywrightAdapterFactory,
  visualAdapter = null,
  logPath = path.resolve('runs', 'browser-check.jsonl'),
  runId,
} = {}) {
  const logger = createExecutionLogger(logPath, { runId });
  logger.start('browser');
  let playwrightAttempt;
  let adapter;
  try {
    adapter = playwrightAdapter || await playwrightAdapterFactory();
    playwrightAttempt = normalizePlaywrightAttempt(await adapter.inspect());
    if (playwrightAttempt.ambiguous === true) {
      playwrightAttempt.mutation_confirmed = true;
    }
  } catch (error) {
    playwrightAttempt = {
      ok: false,
      reason: error.mutation_confirmed || error.ambiguous ? 'ambiguous_mutation' : error.message,
      mutation_confirmed: Boolean(adapter) || error.mutation_confirmed === true || error.ambiguous === true,
      observed_state: error.observed_state || null,
    };
  } finally {
    if (adapter?.close) await adapter.close();
  }

  if (playwrightAttempt.ok === true) {
    const result = {
      ...resolveBrowserRoute({ playwrightAttempt }),
      report: playwrightAttempt.report,
    };
    logger.finish('browser', 'completed', {
      route_attempted: result.attempted_routes,
      effective_route: result.effective_route,
      state: result.observed_state,
      reason: result.reason,
    });
    return { ...result, log_path: logger.path, events: logger.events };
  }
  if (
    playwrightAttempt.mutation_confirmed
    || playwrightAttempt.ambiguous === true
    || playwrightAttempt.reason === 'ambiguous_mutation'
  ) {
    const result = resolveBrowserRoute({ playwrightAttempt });
    logger.finish('browser', 'blocked', {
      route_attempted: result.attempted_routes,
      effective_route: result.effective_route,
      state: result.observed_state,
      reason: result.reason,
    });
    return { ...result, log_path: logger.path, events: logger.events };
  }

  // Playwright falhou antes de mutação -> tentar fallback visual (screenshot + visão nativa)
  logger.finish('browser', 'fallback', {
    route_attempted: ['playwright', 'screenshot+nativa'],
    reason: playwrightAttempt.reason || 'playwright_failed',
  });

  let visualAttempt;
  if (visualAdapter) {
    try {
      const raw = await visualAdapter.inspect();
      visualAttempt = normalizePlaywrightAttempt(raw);
      if (visualAttempt.ambiguous === true) {
        visualAttempt.mutation_confirmed = true;
      }
    } catch (error) {
      visualAttempt = {
        ok: false,
        reason: error.mutation_confirmed || error.ambiguous ? 'ambiguous_mutation' : error.message,
        mutation_confirmed: error.mutation_confirmed === true || error.ambiguous === true,
        observed_state: error.observed_state || null,
      };
    }
  } else {
    visualAttempt = { ok: false, reason: 'no_visual_adapter' };
  }

  const result = resolveBrowserRoute({ playwrightAttempt, visualAttempt });
  if (visualAttempt.ok === true) result.report = visualAttempt.report;
  logger.finish('browser', result.effective_route === 'stop' ? 'blocked' : 'completed', {
    route_attempted: result.attempted_routes,
    effective_route: result.effective_route,
    state: result.observed_state,
    reason: result.reason,
  });
  return { ...result, log_path: logger.path, events: logger.events };
}

async function main(options = {}) {
  const result = await runBrowserCheck(options);
  console.log(JSON.stringify(result));
  if (result.effective_route === 'stop') {
    throw new Error(`browser route stopped: ${result.reason}`);
  }
  return result;
}

if (require.main === module) {
  main().catch((error) => {
    console.error(`linkedin browser check failed: ${error.message}`);
    process.exitCode = 1;
  });
}

module.exports = {
  browserRouteOrder,
  createExecutionLogger,
  inspectPage,
  runBrowserCheck,
  main,
  resolveBrowserRoute,
  screenshotPathFromEnvironment,
  selectLinkedInPage,
  visualFallbackOrder,
};
