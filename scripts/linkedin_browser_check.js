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
  return ['browser_native', 'image-analyzer', 'playwright', 'stop'];
}

function resolveBrowserRoute({
  visualAttempt = null,
  imageAnalyzerAttempt = null,
  playwrightAttempt = null,
}) {
  const attempts = [
    ['browser_native', visualAttempt],
    ['image-analyzer', imageAnalyzerAttempt],
    ['playwright', playwrightAttempt],
  ].filter(([, attempt]) => attempt);
  const attemptedRoutes = [];
  const routeReasons = {};

  for (const [route, attempt] of attempts) {
    attemptedRoutes.push(route);
    const reason = attempt.ok === true
      ? `${route === 'playwright' ? route : route.replace('-', '_')}_success`
      : attempt.reason || `${route}_failed`;
    routeReasons[route] = reason;

    if (
      attempt.mutation_confirmed
      || attempt.ambiguous === true
      || attempt.reason === 'ambiguous_mutation'
    ) {
      return {
        attempted_routes: attemptedRoutes,
        effective_route: 'stop',
        reason: 'ambiguous_mutation',
        route_reasons: { ...routeReasons, [route]: 'ambiguous_mutation' },
        observed_state: attempt.observed_state || null,
        mutation_confirmed: true,
      };
    }
    if (attempt.ok === true) {
      let report = attempt.report;
      if (route === 'playwright') {
        report = { mutation_allowed: false, ...(report || {}) };
      }
      return {
        attempted_routes: attemptedRoutes,
        effective_route: route,
        reason,
        route_reasons: routeReasons,
        observed_state: attempt.report?.visual_state || attempt.observed_state || null,
        report,
      };
    }
  }

  const lastAttempt = attempts.at(-1)?.[1] || {};
  return {
    attempted_routes: attemptedRoutes,
    effective_route: 'stop',
    reason: lastAttempt.reason || 'browser_routes_failed',
    route_reasons: routeReasons,
    observed_state: lastAttempt.observed_state || null,
  };
}

function normalizePlaywrightAttempt(value) {
  if (value && typeof value === 'object' && 'ok' in value) return value;
  return { ok: true, report: value };
}

function visualFallbackOrder() {
  return ['browser_native', 'image-analyzer', 'stop'];
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
    mutation_allowed: false,
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

async function runBrowserCheck({
  playwrightAdapter,
  playwrightAdapterFactory = defaultPlaywrightAdapterFactory,
  visualAdapter = null,
  imageAnalyzerAdapter = null,
  logPath = path.resolve('runs', 'browser-check.jsonl'),
  runId,
} = {}) {
  const logger = createExecutionLogger(logPath, { runId });
  logger.start('browser');
  let visualAttempt;
  try {
    visualAttempt = normalizePlaywrightAttempt(
      visualAdapter ? await visualAdapter.inspect() : { ok: false, reason: 'no_visual_adapter' },
    );
    if (visualAttempt.ambiguous === true) visualAttempt.mutation_confirmed = true;
  } catch (error) {
    visualAttempt = {
      ok: false,
      reason: error.mutation_confirmed || error.ambiguous ? 'ambiguous_mutation' : error.message,
      mutation_confirmed: error.mutation_confirmed === true || error.ambiguous === true,
      observed_state: error.observed_state || null,
    };
  }
  if (visualAttempt.mutation_confirmed || visualAttempt.reason === 'ambiguous_mutation') {
    const result = resolveBrowserRoute({ visualAttempt });
    logger.finish('browser', 'blocked', { route_attempted: result.attempted_routes, effective_route: result.effective_route, state: result.observed_state, reason: result.reason });
    return { ...result, log_path: logger.path, events: logger.events };
  }
  if (visualAttempt.ok === true) {
    const result = resolveBrowserRoute({ visualAttempt });
    logger.finish('browser', 'completed', { route_attempted: result.attempted_routes, effective_route: result.effective_route, state: result.observed_state, reason: result.reason });
    return { ...result, log_path: logger.path, events: logger.events };
  }

  let imageAnalyzerAttempt;
  if (imageAnalyzerAdapter) {
    try {
      imageAnalyzerAttempt = normalizePlaywrightAttempt(await imageAnalyzerAdapter.inspect());
      if (imageAnalyzerAttempt.ambiguous === true) imageAnalyzerAttempt.mutation_confirmed = true;
    } catch (error) {
      imageAnalyzerAttempt = {
        ok: false,
        reason: error.mutation_confirmed || error.ambiguous ? 'ambiguous_mutation' : error.message,
        mutation_confirmed: error.mutation_confirmed === true || error.ambiguous === true,
        observed_state: error.observed_state || null,
      };
    }
    if (imageAnalyzerAttempt.mutation_confirmed || imageAnalyzerAttempt.reason === 'ambiguous_mutation') {
      const result = resolveBrowserRoute({ visualAttempt, imageAnalyzerAttempt });
      logger.finish('browser', 'blocked', { route_attempted: result.attempted_routes, effective_route: result.effective_route, state: result.observed_state, reason: result.reason });
      return { ...result, log_path: logger.path, events: logger.events };
    }
    if (imageAnalyzerAttempt.ok === true) {
      const result = resolveBrowserRoute({ visualAttempt, imageAnalyzerAttempt });
      logger.finish('browser', 'completed', { route_attempted: result.attempted_routes, effective_route: result.effective_route, state: result.observed_state, reason: result.reason });
      return { ...result, log_path: logger.path, events: logger.events };
    }
  }

  logger.finish('browser', 'fallback', {
    route_attempted: ['browser_native', ...(imageAnalyzerAttempt ? ['image-analyzer'] : []), 'playwright'],
    reason: visualAttempt.reason || 'native_failed',
  });
  let playwrightAttempt;
  let adapter;
  try {
    adapter = playwrightAdapter || await playwrightAdapterFactory();
    playwrightAttempt = normalizePlaywrightAttempt(await adapter.inspect());
    if (playwrightAttempt.ambiguous === true) playwrightAttempt.mutation_confirmed = true;
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

  const result = resolveBrowserRoute({ visualAttempt, imageAnalyzerAttempt, playwrightAttempt });
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
