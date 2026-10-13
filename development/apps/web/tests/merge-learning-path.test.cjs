const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { stripTypeScriptTypes } = require('node:module');
const source = fs.readFileSync(path.join(__dirname, '../src/features/curriculum/merge-learning-path.ts'), 'utf8');
let mergeLearningPath, includesLearningPath;
test.before(async () => {
 const module = await import('data:text/javascript;base64,' + Buffer.from(stripTypeScriptTypes(source)).toString('base64'));
 ({ mergeLearningPath, includesLearningPath } = module);
});
const subtopic = (id, score=0) => ({ id, name:id, proficiency:score, status:score ? 'in-progress':'not-started', description:id });
const curriculum = (subtopics, id='c1', categoryId='hidden-category', topicId='forces') => ({
 id, name:'Curriculum', progress:0, levels:[{id:'g1',name:'Grade 1',progress:0,subjects:[{
  id:'science',name:'Science',progress:0,domains:[{id:'motion',name:'Motion',progress:0,topics:[
   {id:topicId,name:'Forces',categoryId,subtopics}
  ]}]
 }]}]
});
test('a subtopic creates its full ancestor path without mutating inputs',()=>{
 const incoming=[curriculum([subtopic('gravity')])];const before=structuredClone(incoming);const result=mergeLearningPath([],incoming);
 assert.deepEqual(result,incoming);assert.deepEqual(incoming,before);
 assert.equal(result[0].levels[0].subjects[0].domains[0].topics[0].subtopics.length,1);
 result[0].levels[0].subjects[0].name='Changed';assert.equal(incoming[0].levels[0].subjects[0].name,'Science');
});
test('broader additions preserve progress and are idempotent',()=>{
 const existing=[curriculum([subtopic('gravity',8)])];existing[0].progress=46;
 existing[0].levels[0].subjects[0].domains[0].progress=45;
 const incoming=[curriculum([subtopic('gravity'),subtopic('friction')])];const before=structuredClone(existing);
 const merged=mergeLearningPath(existing,incoming);
 assert.deepEqual(existing,before);assert.equal(merged[0].progress,46);
 assert.equal(merged[0].levels[0].subjects[0].domains[0].progress,45);
 assert.equal(merged[0].levels[0].subjects[0].domains[0].topics[0].subtopics[0].proficiency,8);
 assert.equal(merged[0].levels[0].subjects[0].domains[0].topics[0].subtopics.length,2);
 assert.deepEqual(mergeLearningPath(merged,incoming),merged);
 assert(!includesLearningPath(existing,incoming));assert(includesLearningPath(merged,incoming));
});
test('hidden category identity keeps same-named topics distinct',()=>{
 const existing=[curriculum([subtopic('gravity')])];
 const other=curriculum([subtopic('gravity')],'c1','other-hidden-category','other-forces');
 const merged=mergeLearningPath(existing,[other]);
 const topics=merged[0].levels[0].subjects[0].domains[0].topics;
 assert.equal(topics.length,2);
 assert.deepEqual(topics.map(t=>t.categoryId),['hidden-category','other-hidden-category']);
 assert(!includesLearningPath(existing,[other]));
});
test('partial branches retain unrelated subjects and separate curricula',()=>{
 const existing=[{...curriculum([]),levels:[{id:'g1',name:'Grade 1',progress:0,subjects:[{id:'math',name:'Math',progress:20,domains:[]}]}]}];
 const merged=mergeLearningPath(existing,[curriculum([subtopic('gravity')]),curriculum([subtopic('gravity')],'c2')]);
 assert.equal(merged.length,2);
 assert.deepEqual(merged[0].levels[0].subjects.map(s=>s.id),['math','science']);
 assert.equal(merged[1].levels[0].subjects.length,1);
});
