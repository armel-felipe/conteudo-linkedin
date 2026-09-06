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
  return ['mcp_chrome_devtools', 'playwright_fallback', 'stop'];
}

function resolveBrowserRoute({
  mcpAttempt,
  playwrightAttempt = null,
}) {
  const attemptedRoutes = ['mcp_chrome_devtools'];
  const mcp = mcpAttempt || {};
  if (
    mcp.mutation_confirmed
    || mcp.ambiguous === true
    || mcp.reason === 'ambiguous_mutation'
  ) {
    return {
      attempted_routes: attemptedRoutes,
      effective_route: 'stop',
      reason: 'ambiguous_mutation',
      route_reasons: { mcp_chrome_devtools: 'ambiguous_mutation' },
      observed_state: mcp.observed_state || null,
      mutation_confirmed: true,
    };
  }
  if (mcp.ok === true) {
    return {
      attempted_routes: attemptedRoutes,
      effective_route: 'mcp_chrome_devtools',
      reason: 'mcp_success',
      route_reasons: { mcp_chrome_devtools: 'mcp_success' },
      observed_state: mcp.report?.visual_state || mcp.observed_state || null,
    };
  }
  if (!playwrightAttempt) {
    return {
      attempted_routes: attemptedRoutes,
      effective_route: 'stop',
      reason: mcp.reason || 'mcp_failed',
      route_reasons: { mcp_chrome_devtools: mcp.reason || 'mcp_failed' },
      observed_state: mcp.observed_state || null,
    };
  }
  attemptedRoutes.push('playwright_fallback');
  if (playwrightAttempt.mutation_confirmed) {
    return {
      attempted_routes: attemptedRoutes,
      effective_route: 'stop',
      reason: 'ambiguous_mutation',
      route_reasons: {
        mcp_chrome_devtools: mcp.reason || 'mcp_failed',
        playwright_fallback: 'ambiguous_mutation',
      },
      observed_state: playwrightAttempt.observed_state || null,
      mutation_confirmed: true,
    };
  }
  if (playwrightAttempt.ok === true) {
    return {
      attempted_routes: attemptedRoutes,
      effective_route: 'playwright_fallback',
      reason: mcp.reason || 'mcp_failed',
      route_reasons: {
        mcp_chrome_devtools: mcp.reason || 'mcp_failed',
        playwright_fallback: 'playwright_success',
      },
      observed_state: playwrightAttempt.report?.visual_state || playwrightAttempt.observed_state || null,
    };
  }
  return {
    attempted_routes: attemptedRoutes,
    effective_route: 'stop',
    reason: playwrightAttempt.reason || 'playwright_failed',
    route_reasons: {
      mcp_chrome_devtools: mcp.reason || 'mcp_failed',
      playwright_fallback: playwrightAttempt.reason || 'playwright_failed',
    },
    observed_state: playwrightAttempt.observed_state || null,
  };
}

function normalizePlaywrightAttempt(value) {
  if (value && typeof value === 'object' && 'ok' in value) return value;
  return { ok: true, report: value };
}

function visualFallbackOrder() {
  return ['screenshot+nativa', 'image-analyzer:native_failed', 'stop'];
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

function defaultMcpAdapter() {
  return {
    async inspect() {
      return {
        ok: false,
        reason: 'mcp_adapter_unconfigured',
        mutation_confirmed: false,
      };
    },
  };
}

function defaultMcpAdapterFactory() {
  return defaultMcpAdapter();
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
 * MCP adapter contract: inspect() returns { ok, report?, reason?,
 * mutation_confirmed?, observed_state? }. It is injected so tests never need
 * credentials or a remote MCP connection.
 */
async function runBrowserCheck({
  mcpAdapter,
  mcpAdapterFactory = defaultMcpAdapterFactory,
  playwrightAdapterFactory = defaultPlaywrightAdapterFactory,
  logPath = path.resolve('runs', 'browser-check.jsonl'),
  runId,
} = {}) {
  const logger = createExecutionLogger(logPath, { runId });
  logger.start('browser');
  let mcpAttempt;
  try {
    const adapter = mcpAdapter || await mcpAdapterFactory();
    mcpAttempt = await adapter.inspect();
  } catch (error) {
    mcpAttempt = {
      ok: false,
      reason: error.ambiguous || error.mutation_confirmed
        ? 'ambiguous_mutation'
        : error.message,
      ambiguous: error.ambiguous === true,
      mutation_confirmed: error.mutation_confirmed === true || error.ambiguous === true,
      observed_state: error.observed_state || null,
    };
  }
  if (mcpAttempt.ok === true) {
    const result = {
      ...resolveBrowserRoute({ mcpAttempt }),
      report: mcpAttempt.report,
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
    mcpAttempt.mutation_confirmed
    || mcpAttempt.ambiguous === true
    || mcpAttempt.reason === 'ambiguous_mutation'
  ) {
    const result = resolveBrowserRoute({ mcpAttempt });
    logger.finish('browser', 'blocked', {
      route_attempted: result.attempted_routes,
      effective_route: result.effective_route,
      state: result.observed_state,
      reason: result.reason,
    });
    return { ...result, log_path: logger.path, events: logger.events };
  }

  logger.finish('browser', 'fallback', {
    route_attempted: ['mcp_chrome_devtools', 'playwright_fallback'],
    reason: mcpAttempt.reason || 'mcp_failed',
  });

  let playwrightAttempt;
  let adapter;
  try {
    adapter = await playwrightAdapterFactory();
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
  const result = resolveBrowserRoute({ mcpAttempt, playwrightAttempt });
  if (playwrightAttempt.ok === true) result.report = playwrightAttempt.report;
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
