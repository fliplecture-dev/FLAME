const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { loadTs } = require('./load-local-typescript.cjs');

test('question quota rejection explains the rolling window instead of an interrupted stream', async () => {
  const { answerErrorMessage } = await loadTs(path.resolve(__dirname, '../src/lib/api/answer-errors.ts'));
  assert.match(answerErrorMessage('daily_limit_reached'), /question limit.*24 hours/);
  assert.doesNotMatch(answerErrorMessage('daily_limit_reached'), /Retry to check its saved status/);
  assert.match(answerErrorMessage('unavailable_context'), /Select the topic again/);
  assert.match(answerErrorMessage('provider_budget_exceeded'), /spending limit/);
  assert.doesNotMatch(answerErrorMessage('private server detail'), /private server detail/);
});
