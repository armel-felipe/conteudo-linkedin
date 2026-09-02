const test = require('node:test');
const assert = require('node:assert/strict');

const {
  selectLinkedInPage,
  visualFallbackOrder,
} = require('../scripts/linkedin_browser_check.js');

const page = (url) => ({ url: () => url });

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

test('keeps the visual fallback order explicit', () => {
  assert.deepEqual(visualFallbackOrder(), [
    'playwright',
    'screenshot+nativa',
    'image-analyzer:native_failed',
    'stop',
  ]);
});
