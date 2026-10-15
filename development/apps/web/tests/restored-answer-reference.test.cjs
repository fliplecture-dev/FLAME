const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { stripTypeScriptTypes } = require('node:module');
let restoredTurns;
test.before(async () => {
  ({ restoredTurns } = await require('./load-local-typescript.cjs').loadTs(path.join(__dirname, '../src/features/learning/restore-saved-session.ts')));
});

test('restored rich content survives reload alongside legacy and unknown blocks', () => {
  const blocks = [{kind:'markdown',id:'m',text:'**Answer**'}, {kind:'chart',id:'c',chartType:'bar',title:'Example',description:'Example data',xKey:'name',illustrative:true,series:[{key:'n',label:'Count'}],data:[{name:'A',n:2}]}, {kind:'future-block'}];
  const [turn] = restoredTurns([{role:'user',turn_number:1,blocks:[{kind:'text',text:'Why?'}]},{id:'answer',role:'assistant',turn_number:1,blocks}]);
  assert.deepEqual(turn.blocks.slice(0,2),blocks.slice(0,2));
  assert.match(turn.blocks[2].text,/could not be displayed/);
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
