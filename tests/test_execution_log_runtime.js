const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { createExecutionLogger } = require('../scripts/execution_log.js');

test('records optional token usage and model', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'token-log-'));
  const file = path.join(dir, 'run.jsonl');
  const logger = createExecutionLogger(file);
  const event = logger.emit('write-post', 'completed', {
    model: 'test-model', input_tokens: 120, output_tokens: 35,
    cached_input_tokens: 80,
  });
  assert.equal(event.input_tokens, 120);
  assert.equal(event.output_tokens, 35);
  assert.equal(event.cached_input_tokens, 80);
  assert.equal(JSON.parse(fs.readFileSync(file, 'utf8')).model, 'test-model');
});

test('rejects invalid token usage', () => {
  const logger = createExecutionLogger(path.join(os.tmpdir(), `token-log-${Date.now()}.jsonl`));
  assert.throws(() => logger.emit('research', 'completed', { input_tokens: -1 }), /non-negative/);
  assert.throws(() => logger.emit('research', 'completed', { output_tokens: true }), /non-negative/);
});
