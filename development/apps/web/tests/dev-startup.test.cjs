const {test}=require('node:test');const assert=require('node:assert/strict');
const {ready,API_URL,WEB_URL}=require('../scripts/dev.cjs');
test('unexpected exits retry with a bounded budget',()=>{
 const {RestartBudget}=require('../scripts/dev.cjs');const budget=new RestartBudget();
 assert.equal(budget.allow(0),true);assert.equal(budget.allow(1000),true);assert.equal(budget.allow(2000),true);
 assert.equal(budget.allow(3000),false);assert.equal(budget.allow(61000),true);
});
test('canonical local ports and readiness gate',async()=>{
 assert.equal(API_URL,'http://127.0.0.1:8000');assert.equal(WEB_URL,'http://localhost:3000');
 const urls=[];await ready(API_URL,1,async url=>{urls.push(url);return {ok:true,json:async()=>url.endsWith('/live')?{service:'flame-api'}:{checks:{database:'ok'}}};});
 assert.deepEqual(urls,[API_URL+'/health/live',API_URL+'/health/ready']);
});
test('wrong service, failed database and exited backend block startup',async()=>{
 await assert.rejects(ready(API_URL,1,async()=>({ok:true,json:async()=>({service:'other'})})),/did not become ready/);
 await assert.rejects(ready(API_URL,1,async url=>({ok:!url.endsWith('/ready'),json:async()=>({service:'flame-api'})})),/database did not become ready/);
 await assert.rejects(ready(API_URL,1,async()=>{},()=>false),/Backend exited/);
});
