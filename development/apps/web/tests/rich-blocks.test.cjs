const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { stripTypeScriptTypes } = require('node:module');
let rich;
test.before(async () => {
  rich = await require('./load-local-typescript.cjs').loadTs(path.join(__dirname, '../src/features/learning/rich-blocks.ts'));
});
const chart = () => ({ id:'c',kind:'chart',chartType:'line',title:'Distance',description:'Example',xKey:'time',illustrative:true,series:[{key:'distance',label:'Metres'}],data:[{time:0,distance:0},{time:1,distance:2}] });
test('chart types validate finite data and reject malformed rows, unsafe keys and excess sizes', () => {
  for(const chartType of ['bar','line','pie']) assert(rich.isChartBlock({...chart(),chartType}));
  for(const value of [NaN,Infinity,true,'2',{},1e13]) assert.equal(rich.isChartBlock({...chart(),data:[{time:0,distance:value}]}),false);
  for(const override of [{chartType:'script'},{data:[{time:0,distance:2,extra:1}]},{series:[{key:'constructor',label:'Bad'}]},{series:[{key:'time',label:'Bad'}]},{data:Array(51).fill({time:0,distance:2})},{chartType:'pie',data:[{time:0,distance:-1}]},{chartType:'pie',data:[{time:0,distance:0}]}]) assert.equal(rich.isChartBlock({...chart(),...override}),false);
});
test('live and restored blocks preserve valid IDs and provide local fallback', () => {
  assert.deepEqual(rich.responseBlock(chart(),'fallback'),chart());
  assert.equal(rich.responseBlock({kind:'markdown',text:'**Works**'},'old').id,'old');
  assert.equal(rich.responseBlock({kind:'text',text:'$5'},'old').text,'$5');
  for(const value of [null,{kind:'unknown'},{kind:'markdown',text:{}},{...chart(),data:[]},{kind:'table',caption:'Bad',columns:['A'],rows:[['1','2']]}]) assert.match(rich.responseBlock(value,'fallback').text,/could not be displayed/);
});
test('links reject executable, insecure, protocol-relative and disguised URLs', () => {
  for(const value of ['javascript:alert(1)','data:text/html,bad','http://example.com','//example.com','/\\evil.test','https://example.com\nattack']) assert.equal(rich.safeResponseUrl(value),undefined);
  assert.equal(rich.safeResponseUrl('/learn'),'/learn');
  assert.equal(rich.safeResponseUrl('https://example.com'), 'https://example.com/');
});
