const assert=require('node:assert/strict'),http=require('node:http'),path=require('node:path');
const {spawn}=require('node:child_process');
const {chromium}=require(path.resolve(__dirname,'../../../../.kilo/ui-check/node_modules/playwright'));
const cwd=path.resolve(__dirname,'..'),base='http://localhost:3123';
const id=n=>`${String(n).padStart(8,'0')}-1111-4111-8111-111111111111`;
const resource=(n,title)=>({id:id(n),title,type:'image',source:'upload',version:1,published:false,availability:'available',paths:[],path_details:[],mime_type:'image/png',learning_metadata:{topic_labels:[]}});
const obsolete=resource(1,'Deleted fixture media'),active=resource(2,'Available fixture media');
let deleted=false,holdList=false,releaseList,releaseSlow;
const json=(res,data,status=200)=>{res.writeHead(status,{'content-type':'application/json'});res.end(JSON.stringify(data));};
const mock=http.createServer(async(req,res)=>{
 const url=new URL(req.url,'http://fixture'),route=url.pathname.replace('/api/v1/','');
 if(route==='me')return json(res,{id:id(99),role:'admin',email:'fixture@example.test'});
 if(route==='admin/curricula'||route==='admin/resources/paths')return json(res,{items:[]});
 if(route==='admin/resources'){
  const q=url.searchParams.get('q');
  if(q==='slow'){await new Promise(resolve=>releaseSlow=resolve);return json(res,{items:[obsolete],total:1});}
  if(q==='error')return json(res,{error:{message:'Fixture refresh failed'}},503);
  if(holdList)await new Promise(resolve=>releaseList=resolve);
  return json(res,{items:deleted?[active]:[obsolete,active],total:deleted?1:2});
 }
 if(route===`admin/resources/${obsolete.id}/delete-preview`)return json(res,{resource:obsolete,dependencies:{shared_resources:0,activity_kits:0,activity_records:0,conversation_references:0}});
 if(route===`admin/resources/${obsolete.id}/delete`){deleted=true;holdList=true;return json(res,{status:'deleted',id:obsolete.id,media_retained:true});}
 return json(res,{error:{message:'Fixture route unavailable'}},404);
});
const waitFor=async getter=>{for(let i=0;i<100&&!getter();i++)await new Promise(r=>setTimeout(r,50));assert(getter(),'Fixture request did not start');};
(async()=>{let server,browser;try{
 await new Promise(r=>mock.listen(0,'127.0.0.1',r));
 server=spawn(process.execPath,[path.join(cwd,'node_modules/next/dist/bin/next'),'start','--port','3123'],{cwd,windowsHide:true,env:{...process.env,FLAME_WEB_ORIGIN:base,FLAME_API_URL:`http://127.0.0.1:${mock.address().port}`,FLAME_BFF_SHARED_KEY:'fixture-secret'},stdio:'ignore'});
 for(let i=0;i<100;i++){try{if((await fetch(base+'/sign-in')).ok)break;}catch{}await new Promise(r=>setTimeout(r,200));}
 browser=await chromium.launch({channel:'msedge',headless:true});const context=await browser.newContext();await context.addCookies([{name:'flame_session',value:'fixture-session',url:base}]);const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'/admin',{waitUntil:'networkidle'});await page.getByRole('button',{name:'Resource Library',exact:true}).click();const panel=page.locator('.b9-resource-panel'),table=panel.locator('tbody');
 await table.getByText(obsolete.title,{exact:true}).waitFor();
 await panel.getByRole('button',{name:'Actions for '+obsolete.title}).click();await page.getByRole('menuitem',{name:'Delete',exact:true}).click();
 const dialog=page.getByRole('dialog',{name:'Delete '+obsolete.title,exact:true});await dialog.getByRole('checkbox',{name:/I confirm deletion/}).check();await dialog.getByRole('button',{name:'Delete resource',exact:true}).click();
 await waitFor(()=>releaseList);assert.equal(await table.locator('tr').count(),0,'Deleted row remained visible during refresh');
 assert(await panel.getByRole('checkbox',{name:'Select resources on this page'}).isDisabled());
 holdList=false;releaseList();releaseList=null;await dialog.waitFor({state:'hidden'});await table.getByText(active.title,{exact:true}).waitFor();assert.equal(await table.getByText(obsolete.title,{exact:true}).count(),0);
 const search=panel.getByRole('searchbox',{name:'Search resources'});
 await search.fill('slow');await waitFor(()=>releaseSlow);assert.equal(await table.locator('tr').count(),0);
 await search.fill('fresh');await table.getByText(active.title,{exact:true}).waitFor();releaseSlow();releaseSlow=null;await page.waitForTimeout(300);assert.equal(await table.getByText(obsolete.title,{exact:true}).count(),0,'Late old response restored a deleted row');
 await search.fill('error');await panel.getByRole('alert').filter({hasText:'Fixture refresh failed'}).waitFor();assert.equal(await table.locator('tr').count(),0,'Failed refresh restored cached rows');
 await search.fill('');await table.getByText(active.title,{exact:true}).waitFor();
 holdList=true;await page.reload({waitUntil:'domcontentloaded'});await page.getByRole('button',{name:'Resource Library',exact:true}).click();await waitFor(()=>releaseList);assert.equal(await panel.locator('tbody tr').count(),0);
 holdList=false;releaseList();releaseList=null;await panel.locator('tbody').getByText(active.title,{exact:true}).waitFor();assert.equal(await panel.locator('tbody').getByText(obsolete.title,{exact:true}).count(),0);
 assert.deepEqual(errors,[]);console.log('Passed: delayed deletion refresh, cold reload, filter changes, stale response rejection and failure without old rows.');
}finally{releaseList?.();releaseSlow?.();await browser?.close();server?.kill();await new Promise(r=>mock.close(r));}})().catch(e=>{console.error(e);process.exitCode=1;});
