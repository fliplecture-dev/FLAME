const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { stripTypeScriptTypes } = require('node:module');
let restoredTurns;
test.before(async () => {
  const source = fs.readFileSync(path.join(__dirname, '../src/features/learning/restore-saved-session.ts'), 'utf8')
    .replace(/^import type .*;\r?\n/gm, '');
  ({ restoredTurns } = await import('data:text/javascript;base64,' + Buffer.from(stripTypeScriptTypes(source)).toString('base64')));
});
test('restored pairs keep server request references and tolerate older messages', () => {
  const reference = '550e8400-e29b-41d4-a716-446655440000';
  const user = { id: 'u', role: 'user', turn_number: 1, blocks: [{ kind: 'text', text: 'Why?' }] };
  const assistant = { id: 'a', role: 'assistant', turn_number: 1, request_id: reference, blocks: [{ kind: 'text', text: 'Because.' }] };
  const [turn] = restoredTurns([assistant, user], 'owned-session');
  assert.equal(turn.requestId, reference);
  assert.equal(turn.sessionId, 'owned-session');
  assert.equal(turn.messageId, 'a');
  assert.equal(restoredTurns([user, { ...assistant, request_id: null }])[0].requestId, undefined);
  assert.equal(restoredTurns([user, { ...assistant, request_id: '<unsafe>' }])[0].requestId, undefined);
});
