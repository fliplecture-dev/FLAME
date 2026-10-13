const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { stripTypeScriptTypes } = require('node:module');
const source = fs.readFileSync(path.join(__dirname, '../src/features/curriculum/learning-tree.ts'), 'utf8');
let firstBranchKeys, allBranchKeys, nodeKey;
test.before(async () => {
  const module = await import('data:text/javascript;base64,' + Buffer.from(stripTypeScriptTypes(source)).toString('base64'));
  ({ firstBranchKeys, allBranchKeys, nodeKey } = module);
});
test('adding a curriculum opens one path instead of every branch', () => {
  const topics = Array.from({ length: 400 }, (_, i) => ({ id: `topic-${i}`, categoryId: null, subtopics: [{ id: `subtopic-${i}` }] }));
  const curriculum = [{ id: 'curriculum', levels: Array.from({ length: 6 }, (_, i) => ({
    id: `level-${i}`, subjects: [{ id: `subject-${i}`, domains: [{ id: `domain-${i}`, topics }] }],
  })) }];
  assert(allBranchKeys(curriculum).length > 400);
  assert.deepEqual(firstBranchKeys(curriculum), [
    nodeKey('curriculum'), nodeKey('curriculum', 'level-0'),
    nodeKey('curriculum', 'level-0', 'subject-0'),
    nodeKey('curriculum', 'level-0', 'subject-0', 'domain-0'),
    nodeKey('curriculum', 'level-0', 'subject-0', 'domain-0', null, 'topic-0'),
  ]);
});