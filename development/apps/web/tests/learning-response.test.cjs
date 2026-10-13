const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {stripTypeScriptTypes}=require('node:module');
let adapter;
test.before(async()=>{const source=fs.readFileSync(path.join(__dirname,'../src/lib/api/learning-response.ts'),'utf8');adapter=await import('data:text/javascript;base64,'+Buffer.from(stripTypeScriptTypes(source)).toString('base64'));});
test('legacy and composed recommendation payloads remain compatible',()=>{
  const legacy={status:'ok',resources:[{id:'media'}],teachers:[]};
  assert.equal(adapter.recommendationPayload(legacy,'answer'),legacy);
  const composed={...legacy,learning_response:{schema_version:1,message_id:'answer',recommendations:{status:'completed',data:legacy}}};
  assert.equal(adapter.recommendationPayload(composed,'answer'),legacy);
  assert.throws(()=>adapter.recommendationPayload(composed,'other'),/another answer/);
});
test('none and pending are distinct from unavailable suggestions',()=>{
  for(const status of ['none','pending']){const value={status:'no_results',resources:[],teachers:[],learning_response:{schema_version:1,message_id:'answer',recommendations:{status}}};assert.equal(adapter.recommendationPayload(value,'answer'),value);}
  assert.throws(()=>adapter.recommendationPayload({learning_response:{schema_version:1,message_id:'answer',recommendations:{status:'unavailable'}}},'answer'),/explanation is still available/);
});
test('answer composition preserves legacy rendering and rejects mismatched answers',()=>{
  const answer={message_id:'answer',blocks:[{kind:'text',text:'Explanation'}]};assert.equal(adapter.validateAnswerComposition(answer),answer);
  const composed={...answer,learning_response:{schema_version:1,message_id:'answer',answer:{status:'completed',blocks:answer.blocks},recommendations:{status:'pending'}}};assert.equal(adapter.validateAnswerComposition(composed),composed);
  assert.throws(()=>adapter.validateAnswerComposition({...composed,message_id:'other'}),/preserved/);
});
