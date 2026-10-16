const test=require('node:test'),assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs');
let math,rich,restore;
const definitions=require('../src/features/learning/math-templates.json');
const block=template=>({id:template,kind:'math_visual',version:1,template,title:'Explore mathematics',description:'An illustrative activity.',parameters:Object.fromEntries(Object.entries(definitions[template].parameters).map(([key,spec])=>[key,spec.default]))});
test.before(async()=>{
  const load=require('./load-local-typescript.cjs').loadTs;
  math=await load(path.join(__dirname,'../src/features/learning/math-spec.ts'));
  rich=await load(path.join(__dirname,'../src/features/learning/rich-blocks.ts'));
  restore=await load(path.join(__dirname,'../src/features/learning/restore-saved-session.ts'));
});
test('all 17 trusted templates select the registered engine and survive live/history adapters',()=>{
  assert.equal(Object.keys(definitions).length,17);
  for(const template of Object.keys(definitions)){
    const value=block(template);assert(math.isMathVisualBlock(value),template);
    assert.deepEqual(rich.responseBlock(value,'fallback'),value);
    const turns=restore.restoredTurns([{role:'user',turn_number:1,blocks:[{kind:'text',text:'Explore'}]},{id:'saved',role:'assistant',turn_number:1,blocks:[value]}]);
    assert.deepEqual(turns[0].blocks,[value]);
  }
});
test('frontend registry matches independently deployed backend registry',()=>{
  const backend=JSON.parse(fs.readFileSync(path.join(__dirname,'../../flame-api/app/contracts/math_templates.json'),'utf8'));
  assert.deepEqual(definitions,backend);
});
test('malformed, executable and out-of-bounds specifications fall back locally',()=>{
  for(const override of [{version:2},{template:'constructor'},{engine:'script'},{parameters:{numerator:1,denominator:0}},{parameters:{numerator:5,denominator:4}},{parameters:{numerator:true,denominator:4}},{parameters:{numerator:1,denominator:4,code:'alert(1)'}}]){
    const value={...block('fraction_bar'),...override};assert.equal(math.isMathVisualBlock(value),false);assert.equal(rich.responseBlock(value,'f').kind,'text');
  }
});
test('fractions, number lines, functions and geometry retain mathematical invariants',()=>{
  assert.equal(math.changeMathParameter('fraction_bar',{numerator:3,denominator:4},'denominator',2).numerator,2);
  assert.equal(math.changeMathParameter('number_line',{start:0,end:10,value:8},'end',5).value,5);
  assert.equal(math.functionValue('linear_function',{m:2,b:3},4),11);
  assert.equal(math.functionValue('quadratic_function',{a:1,b:0,c:0},3),9);
  const trig={function:'sin',a:2,k:1,h:0,d:1,x:0};
  assert.equal(math.functionValue('trigonometric_function',trig,0),1);
  assert(Math.abs(math.functionValue('trigonometric_function',trig,Math.PI/2)-3)<1e-10);
  assert.equal(math.functionValue('trigonometric_function',{...trig,function:'cos'},0),3);
  const triangle={ax:0,ay:0,bx:4,by:0,cx:0,cy:3};assert.equal(math.triangleArea(triangle),6);
  assert.match(math.mathState('triangle_angles',triangle),/90°.*Sum 180°/);
  assert.match(math.mathState('triangle_angles',{...triangle,cx:2,cy:0}),/collinear/);
  assert.match(math.mathState('segment_geometry',{ax:1,ay:1,bx:1,by:1}),/coincide/);
});
