const {test}=require('node:test');
const assert=require('node:assert/strict');
const path=require('node:path');
const {loadTs}=require('./load-local-typescript.cjs');

test('mathematical fences use accessible display-math nodes instead of syntax highlighting',async()=>{
  const {remarkMathFences}=await loadTs(path.resolve(__dirname,'../src/features/learning/remark-math-fences.ts'));
  for(const lang of ['math','latex','tex','katex','LaTeX']){
    const equation={type:'code',lang,value:'\\frac{1}{2} + x^2 = 3'};
    const tree={type:'root',children:[{type:'blockquote',children:[equation]}]};
    remarkMathFences()(tree);
    assert.equal(equation.type,'math');
    assert.equal(equation.lang,undefined);
    const code=equation.data.hChildren[0];
    assert.deepEqual(code.properties.className,['language-math','math-display']);
    assert.equal(code.children[0].value,'\\frac{1}{2} + x^2 = 3');
  }
});

test('math fences tolerate redundant delimiters without reclassifying programming or inline code',async()=>{
  const {remarkMathFences}=await loadTs(path.resolve(__dirname,'../src/features/learning/remark-math-fences.ts'));
  for(const value of ['$$x^2=4$$','\\[x^2=4\\]','\\(x^2=4\\)']){
    const node={type:'code',lang:'latex',value};remarkMathFences()(node);
    assert.equal(node.value,'x^2=4');
  }
  for(const node of [{type:'code',lang:'python',value:'x = 2 ** 3'}, {type:'code',lang:'javascript',value:'const x = 2;'}, {type:'code',lang:'json',value:'{"x":2}'}, {type:'code',lang:'',value:'x = 2'}, {type:'inlineCode',value:'x=2'}, {type:'text',value:'$5 and $10'}]){
    const original=structuredClone(node);remarkMathFences()(node);assert.deepEqual(node,original);
  }
});
