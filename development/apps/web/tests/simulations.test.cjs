const {test}=require('node:test');
const assert=require('node:assert/strict');
const {compileSimulation}=require('../src/lib/simulations/compiler.cjs');
test('compiler accepts selected runtime and rejects remote/host/package imports',async()=>{
  const good=await compileSimulation('matter','import Matter from "matter-js";export default api=>({update(dt){Matter.Engine.update(Matter.Engine.create(),dt*1000)}})');
  assert(good.length>1000);
  for(const dependency of ['node:fs','https://example.test/x.js','three','../../lib/api/auth-bff']){
    await assert.rejects(compileSimulation('matter',`import x from ${JSON.stringify(dependency)};export default ()=>x`));
  }
  await assert.rejects(compileSimulation('matter','export default ()=>import("matter-js")'));
  await assert.rejects(compileSimulation('unknown','export default ()=>({})'));
  await assert.rejects(compileSimulation('matter','export default = syntax error'));
});
