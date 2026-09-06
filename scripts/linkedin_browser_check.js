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
  mcpAvailable,
  capabilityAvailable,
  mutationConfirmed,
  errorBeforeMutation,
}) {
  if (mutationConfirmed) {
    return { route: 'stop', reason: 'ambiguous_mutation' };
  }
  if (!errorBeforeMutation) {
    return { route: 'stop', reason: 'ambiguous_mutation' };
  }
  if (mcpAvailable && capabilityAvailable) {
    return { route: 'mcp_chrome_devtools', reason: 'mcp_ready' };
  }
  if (errorBeforeMutation) {
    return {
      route: 'playwright_fallback',
      reason: mcpAvailable ? 'capability_unavailable' : 'mcp_unavailable',
    };
  }
  return { route: 'stop', reason: 'ambiguous_mutation' };
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

async function main() {
  const { chromium } = require('playwright');
  const browser = await chromium.connectOverCDP(
    process.env.OPENWORK_BROWSER_CDP_URL || DEFAULT_CDP_URL,
  );
  try {
    const pages = browser.contexts().flatMap((context) => context.pages());
    const linkedinPage = selectLinkedInPage(pages);
    console.log(JSON.stringify(await inspectPage(linkedinPage)));
  } finally {
    await browser.close();
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
  resolveBrowserRoute,
  screenshotPathFromEnvironment,
  selectLinkedInPage,
  visualFallbackOrder,
};
