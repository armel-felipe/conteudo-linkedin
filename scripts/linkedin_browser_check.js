const os = require('node:os');
const path = require('node:path');

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
  if (mcp.mutation_confirmed) {
    return {
      attempted_routes: attemptedRoutes,
      effective_route: 'stop',
      reason: 'ambiguous_mutation',
      route_reasons: { mcp_chrome_devtools: 'ambiguous_mutation' },
      observed_state: mcp.observed_state || null,
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
  mcpAdapter = defaultMcpAdapter(),
  playwrightAdapterFactory = defaultPlaywrightAdapterFactory,
} = {}) {
  let mcpAttempt;
  try {
    mcpAttempt = await mcpAdapter.inspect();
  } catch (error) {
    mcpAttempt = { ok: false, reason: error.message, mutation_confirmed: false };
  }
  if (mcpAttempt.ok === true) {
    return {
      ...resolveBrowserRoute({ mcpAttempt }),
      report: mcpAttempt.report,
    };
  }
  if (mcpAttempt.mutation_confirmed) {
    return resolveBrowserRoute({ mcpAttempt });
  }

  let playwrightAttempt;
  let adapter;
  try {
    adapter = await playwrightAdapterFactory();
    playwrightAttempt = { ok: true, report: await adapter.inspect() };
  } catch (error) {
    playwrightAttempt = { ok: false, reason: error.message, mutation_confirmed: false };
  } finally {
    if (adapter?.close) await adapter.close();
  }
  const result = resolveBrowserRoute({ mcpAttempt, playwrightAttempt });
  if (playwrightAttempt.ok === true) result.report = playwrightAttempt.report;
  return result;
}

async function main() {
  const result = await runBrowserCheck();
  console.log(JSON.stringify(result));
  if (result.effective_route === 'stop') {
    throw new Error(`browser route stopped: ${result.reason}`);
  }
}

if (require.main === module) {
  main().catch((error) => {
    console.error(`linkedin browser check failed: ${error.message}`);
    process.exitCode = 1;
  });
}

module.exports = {
  browserRouteOrder,
  inspectPage,
  runBrowserCheck,
  resolveBrowserRoute,
  screenshotPathFromEnvironment,
  selectLinkedInPage,
  visualFallbackOrder,
};
