const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { stripTypeScriptTypes } = require('node:module');
const source = fs.readFileSync(path.join(__dirname, '../src/features/learning/recent-sessions.ts'), 'utf8');
let groupRecentSessions, recentTitle;
test.before(async () => {
  const module = await import('data:text/javascript;base64,' + Buffer.from(stripTypeScriptTypes(source)).toString('base64'));
  ({ groupRecentSessions, recentTitle } = module);
});
const context = { curriculum_id: 'c', level_id: 'l', subject_id: 's', domain_id: 'd', category_id: null, topic_id: 't', subtopic_id: 'st', names: { subtopic: 'Gravity' } };
test('Study conversations for one topic appear as one Recent item', () => {
  const rows = [
    { id: 'new', mode: 'study', context, pinned: false, updated_at: '2026-10-02T00:00:00Z' },
    { id: 'old', mode: 'study', context, pinned: true, updated_at: '2026-10-01T00:00:00Z' },
    { id: 'other', mode: 'study', context: { ...context, subtopic_id: 'other' }, pinned: false, updated_at: '2026-09-30T00:00:00Z' },
  ];
  const groups = groupRecentSessions(rows);
  assert.deepEqual(groups.map(group => group.map(row => row.id)), [['new', 'old'], ['other']]);
  assert.equal(recentTitle(rows[0]), 'Gravity');
});
test('Curiosity conversations use their first question as separate titles', () => {
  const rows = [
    { id: 'a', mode: 'curiosity', context: null, pinned: false, first_question: 'Why is the sky blue?', updated_at: '2026-10-01T00:00:00Z' },
    { id: 'b', mode: 'curiosity', context: null, pinned: false, first_question: 'How do planes fly?', updated_at: '2026-09-30T00:00:00Z' },
  ];
  assert.equal(groupRecentSessions(rows).length, 2);
  assert.equal(recentTitle(rows[0]), 'Why is the sky blue?');
});