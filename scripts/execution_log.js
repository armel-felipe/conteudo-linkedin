const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const SENSITIVE_KEY = /auth(?:entication)?[_ -]?token|ct0|cookie|api[_ -]?key|authorization|password|passwd|secret|account[_ -]?id|private/i;

function sanitizeLogValue(value, sensitive = false) {
  if (sensitive) return '[REDACTED]';
  if (Array.isArray(value)) return value.map((item) => sanitizeLogValue(item));
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [
        key,
        sanitizeLogValue(item, SENSITIVE_KEY.test(key)),
      ]),
    );
  }
  if (value === null || ['string', 'number', 'boolean'].includes(typeof value)) return value;
  return String(value);
}

function createExecutionLogger(filePath, { runId = crypto.randomUUID(), clock = () => new Date().toISOString() } = {}) {
  const resolvedPath = path.resolve(filePath);
  const events = [];

  function emit(stage, event, options = {}) {
    const record = {
      run_id: runId,
      timestamp: clock(),
      stage,
      event,
      route_attempted: options.route_attempted || [],
      effective_route: options.effective_route,
      state: options.state,
      duration_ms: options.duration_ms,
      receipt_ref: options.receipt_ref,
      reason: options.reason,
      details: options.details,
    };
    const compact = sanitizeLogValue(
      Object.fromEntries(Object.entries(record).filter(([, value]) => value !== undefined)),
    );
    fs.mkdirSync(path.dirname(resolvedPath), { recursive: true });
    fs.appendFileSync(resolvedPath, `${JSON.stringify(compact)}\n`, 'utf8');
    events.push(compact);
    return compact;
  }

  return {
    emit,
    start: (stage, options = {}) => emit(stage, 'started', options),
    finish: (stage, event, options = {}) => {
      if (!['completed', 'blocked', 'fallback'].includes(event)) {
        throw new Error('finish event must be completed, blocked or fallback');
      }
      return emit(stage, event, options);
    },
    events,
    path: resolvedPath,
  };
}

module.exports = { createExecutionLogger, sanitizeLogValue };
