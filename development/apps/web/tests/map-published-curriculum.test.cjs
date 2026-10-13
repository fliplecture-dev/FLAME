const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { stripTypeScriptTypes } = require('node:module');
const source = fs.readFileSync(path.join(__dirname, '../src/features/curriculum/map-published-curriculum.ts'), 'utf8');
let mapPublishedCurriculum;
test.before(async () => {
 const module = await import('data:text/javascript;base64,' + Buffer.from(stripTypeScriptTypes(source)).toString('base64'));
 ({ mapPublishedCurriculum } = module);
});
const subtopic = (id) => ({ id, name: id, display_order: 0 });
const topic = (id, subtopics=[subtopic('signal')]) => ({ id, name: 'Signals', subtopics, display_order: 0 });
const tree = () => ({ id: 'fliplecture', name: 'Fliplecture', levels: [{ id: 'g1', name: 'Grade 1', subjects: [{ id: 'science', name: 'Science', domains: [{
 id: 'light', name: 'Light', topics: [topic('uncategorized')], categories: [
  { id: 'cat-a', name: 'Hidden A', topics: [topic('topic-a')] },
  { id: 'cat-b', name: 'Hidden B', topics: [topic('topic-b')] },
 ]
 }] }] }] });
test('student tree hides category labels but retains category IDs for each subtopic path', () => {
 const mapped = mapPublishedCurriculum(tree());
 const topics = mapped.levels[0].subjects[0].domains[0].topics;
 assert.deepEqual(topics.map(t => t.categoryId), [null, 'cat-a', 'cat-b']);
 assert.equal(topics[1].subtopics[0].id, 'signal');
 assert(!JSON.stringify(mapped).includes('Hidden A'));
 assert(!JSON.stringify(mapped).includes('Hidden B'));
 assert.equal(topics[1].subtopics[0].proficiency, null);
});
test('published topic with no subtopic is rejected', () => {
 const input = tree(); input.levels[0].subjects[0].domains[0].categories[0].topics[0].subtopics = [];
 assert.throws(() => mapPublishedCurriculum(input), /requires a subtopic/);
});
