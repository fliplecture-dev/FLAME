const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {stripTypeScriptTypes}=require('node:module');let adapter;
test.before(async()=>{let source=fs.readFileSync(path.join(__dirname,'../src/lib/api/auth-bff.ts'),'utf8');source=source.replace(/^import .*next.*;\r?\n/gm,'');adapter=await import('data:text/javascript;base64,'+Buffer.from(stripTypeScriptTypes(source)).toString('base64'));});
test('learning timeout messages identify the failed stage without claiming a curriculum conflict',()=>{
 assert.match(adapter.upstreamTimeoutMessage('sessions/fixture/ask'),/Retry on this question/);
 assert.doesNotMatch(adapter.upstreamTimeoutMessage('sessions/fixture/ask'),/curriculum/);
 assert.match(adapter.upstreamTimeoutMessage('sessions/fixture/capability-check'),/has not been requested yet/);
 assert.match(adapter.upstreamTimeoutMessage('sessions'),/completion could not be confirmed/);
 assert.match(adapter.upstreamTimeoutMessage('admin/curriculum/curriculum/fixture/publish'),/curriculum status/);
});
test('BFF timeout returns an operation-specific 504 and safe reference without exposing payload',async()=>{
 const original=global.fetch,originalWarn=console.warn,logs=[];const previous=process.env.FLAME_BFF_SHARED_KEY;process.env.FLAME_BFF_SHARED_KEY='isolated-test-secret';
 global.fetch=async()=>{throw new DOMException('Timed out','TimeoutError');};console.warn=text=>logs.push(JSON.parse(text));
 try{const result=await adapter.apiRequest('sessions/550e8400-e29b-41d4-a716-446655440000/ask?ignored=private','POST',{question:'private student text'},'private session');const data=await result.json();assert.equal(result.status,504);assert.equal(data.error.code,'upstream_timeout');assert.match(data.request_id,/^[0-9a-f-]{36}$/);assert.doesNotMatch(data.error.message,/curriculum/);assert.equal(logs[0].route,'sessions/:id/ask');assert.doesNotMatch(JSON.stringify(logs),/private|isolated-test-secret/);}
 finally{global.fetch=original;console.warn=originalWarn;if(previous===undefined)delete process.env.FLAME_BFF_SHARED_KEY;else process.env.FLAME_BFF_SHARED_KEY=previous;}
});
