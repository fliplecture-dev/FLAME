const assert = require('node:assert/strict');
const http = require('node:http');
const path = require('node:path');
const fs = require('node:fs');
const {spawn} = require('node:child_process');
const {chromium} = require(path.resolve(__dirname,'../../../../.kilo/ui-check/node_modules/playwright'));
const cwd=path.resolve(__dirname,'..'),base='http://localhost:3113';
const id=n=>`${String(n).padStart(8,'0')}-1111-4111-8111-111111111111`;
let cid=id(1),name='TN Stateboard',draft=2,version=4,published=13,token=id(91),batch=id(90),pending=true;
let staleOnSave=true,commits=0,reviews=0,previews=0,failCommit=true;
let baseDraft=1,basePublished=9,baseVersion=3;
let saved=['Grade 1','Science','Motion','','Push','Saved Basics'];
let workbook=Array.from({length:52},(_,i)=>['Grade 1','Science','Motion','','Push',`Workbook row ${i+1}`]);
let events=[{status:'uploaded',at:new Date().toISOString()},{status:'validated',at:new Date().toISOString()}];
const row=()=>({id:cid,code:'TN_StateBoard',name,state:published?'published':'draft',version,revision:published,published_revision:published,draft_revision:draft});
const tree=()=>({...row(),levels:saved?[{id:id(2),name:saved[0],version:draft,subjects:[{id:id(3),name:saved[1],version:draft,domains:[{id:id(4),name:saved[2],version:draft,categories:[],topics:[{id:id(5),name:saved[4],version:draft,subtopics:[{id:id(6),name:saved[5],version:draft}]}]}]}]}] : []});
const preview=()=>({import_id:batch,preview_revision:token,base_revision:basePublished,base_draft_revision:baseDraft,curriculum_version:baseVersion,published_revision:basePublished,status:'previewed',issue_count:0,counts:{created:52,updated:0,removed:1,reused:0,duplicates:0,invalid:0},dependency_warnings:['Historical records are retained.']});
const json=(res,data,status=200)=>{res.writeHead(status,{'content-type':'application/json'});res.end(JSON.stringify(data));};
const body=async req=>{let parts=[];for await(const part of req)parts.push(part);return JSON.parse(Buffer.concat(parts).toString()||'{}');};
const mock=http.createServer(async(req,res)=>{
 const url=new URL(req.url,'http://test'),route=url.pathname.replace('/api/v1/','');
 if(route==='me')return json(res,{id:id(99),role:'admin',email:'admin@example.test'});
 if(route==='admin/curricula'){
  if(req.method==='POST'){const input=await body(req);cid=id(101);name=input.name;draft=1;version=1;published=0;pending=false;saved=null;return json(res,row(),201);}
  return json(res,{items:[row()]});
 }
 if(route.endsWith('/tree'))return json(res,tree());
 if(route.endsWith('/revisions'))return json(res,{items:published?[{number:published,change_kind:'publish',created_at:new Date().toISOString()}]:[]});
 if(route.endsWith('/deletion-review'))return json(res,{counts:{hierarchy_nodes:6,student_associations:1},blockers:{student_associations:1}});
 if(route.endsWith('/draft/rename')){const input=await body(req);assert.equal(input.expected_revision,draft);saved[['level','subject','domain','category','topic','subtopic'].indexOf(input.field)]=input.name;draft++;return json(res,{draft_revision:draft});}
 if(route.endsWith('/paths/batch')){const input=await body(req);assert.equal(input.expected_revision,draft);saved=Object.values(input.changes[0].values);draft++;return json(res,{draft_revision:draft,rows:[]});}
 if(route==='admin/curriculum/imports')return json(res,{items:[{import_id:batch,filename:'Fixture.xlsx',status:pending?'previewed':'committed',created_at:new Date().toISOString(),events,draft_revision:draft,published_revision:published}]});
 if(route===`admin/curriculum/imports/${batch}`)return json(res,{status:pending?'previewed':'committed',filename:'Fixture.xlsx',sheets:['Curriculum'],sheet_levels:{Curriculum:'__ALL_LEVELS__'},preview:pending?preview():null});
 if(route.endsWith('/issues'))return json(res,{items:[],total:0});
 if(route.endsWith('/review-rows')){
  let items=workbook.map((values,i)=>({sheet:'Curriculum',row_number:i+2,values,operation:'created',errors:[]}));
  if(url.searchParams.get('q'))items=items.filter(r=>r.values.join(' ').includes(url.searchParams.get('q')));
  if(url.searchParams.get('operation')==='removed')items=[{sheet:'Saved draft',row_number:1,values:saved,operation:'removed',errors:[]}];
  const offset=Number(url.searchParams.get('offset')||0),limit=Number(url.searchParams.get('limit')||50);
  return json(res,{items:items.slice(offset,offset+limit),total:items.length,uploaded_total:52});
 }
 if(route.endsWith('/preview')){previews++;token=id(92+previews);baseDraft=draft;basePublished=published;baseVersion=version;return json(res,preview());}
 if(route.endsWith('/review')){
  reviews++;const input=await body(req);
  if(staleOnSave){staleOnSave=false;draft++;return json(res,{error:{code:'stale_preview',message:'Stale preview.'}},409);}
  assert.equal(input.preview_revision,token);
  for(const change of input.changes)if(change.action==='upsert')workbook[change.row_number-2]=change.values;
  token=id(96+reviews);baseDraft=draft;events.push({status:'corrections_validated',at:new Date().toISOString()});return json(res,preview());
 }
 if(route.endsWith('/commit')){
  commits++;const input=await body(req);assert.equal(input.preview_revision,token);
  if(failCommit){failCommit=false;return json(res,{error:{code:'invalid_rows',message:'Replacement rejected; no draft changes saved.'}},422);}
  draft++;pending=false;saved=workbook[0];events.push({status:'replacement_draft_created',at:new Date().toISOString(),draft_revision:draft});return json(res,{...preview(),draft_revision:draft,status:'replacement_draft_created'});
 }
 if(route.endsWith('/publish')){const input=await body(req);assert.equal(input.expected_version,version);assert.equal(input.expected_draft_revision,draft);published++;version++;return json(res,{id:cid,revision:published,version,published_revision:published,draft_revision:0,state:'published'});}
 return json(res,{},404);
});
(async()=>{
 await new Promise(resolve=>mock.listen(0,'127.0.0.1',resolve));
 const server=spawn(process.execPath,[path.join(cwd,'node_modules/next/dist/bin/next'),'start','-p','3113'],{cwd,windowsHide:true,env:{...process.env,FLAME_API_URL:`http://127.0.0.1:${mock.address().port}`,FLAME_BFF_SHARED_KEY:'replacement-test-secret',FLAME_WEB_ORIGIN:base}});
 let browser,page;
 try{
  for(let i=0;i<40;i++){try{if((await fetch(base+'/sign-in')).ok)break;}catch{}await new Promise(r=>setTimeout(r,500));}
  browser=await chromium.launch({channel:'msedge',headless:true});
  const context=await browser.newContext({viewport:{width:1280,height:900}});
  await context.addCookies([{name:'flame_session',value:'replacement-test-session',url:base,httpOnly:true}]);
  page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('dialog',dialog=>dialog.accept());
  await page.goto(base+'/admin',{waitUntil:'networkidle'});
  await page.getByRole('button',{name:'Edit',exact:true}).click();
  await page.locator('.admin-pending-import').waitFor();
  const hierarchy=page.locator('section.admin-card').filter({has:page.getByRole('heading',{name:'Hierarchy Table',exact:true})}).locator('.admin-grid');
  await hierarchy.getByText('Saved Basics',{exact:true}).waitFor();
  assert.equal(await page.getByRole('heading',{name:'Workbook comparison'}).count(),0,'Pending workbook replaced hierarchy');
  assert(await page.getByRole('button',{name:'Publish changes',exact:true}).isDisabled());
  await hierarchy.getByRole('button',{name:'Edit',exact:true}).click();
  await page.getByRole('combobox',{name:'subtopic row 1',exact:true}).fill('Saved row edited');
  await hierarchy.getByRole('button',{name:'Save',exact:true}).click();
  await hierarchy.getByText('Saved row edited',{exact:true}).waitFor();
  assert.equal(await hierarchy.getByRole('combobox',{name:'subtopic row 1',exact:true}).count(),0);
  await page.getByRole('button',{name:'Continue import',exact:true}).dblclick();
  await page.getByRole('heading',{name:'Workbook comparison'}).waitFor();
  const grid=page.locator('.admin-import-review');
  const create=page.getByRole('button',{name:'Create replacement draft',exact:true});
  assert(await create.isDisabled(),'Stale restored preview allowed replacement');
  await page.getByRole('button',{name:'Revalidate comparison',exact:true}).click();
  await page.getByText(/Comparison updated against/).waitFor();
  assert.equal(await grid.locator('input[aria-label="Subtopic import row 1"]').count(),0,'Clean import row is editable');
  await page.reload({waitUntil:'networkidle'});
  assert.equal(await page.getByRole('tab',{name:'Excel Import',exact:true}).getAttribute('aria-selected'),'true');
  await grid.getByText('Workbook row 1',{exact:true}).waitFor();
  await grid.locator('tbody tr').first().getByRole('button',{name:'Edit',exact:true}).click();
  const correction=grid.getByRole('combobox',{name:'Subtopic import row 1',exact:true});await correction.fill('Preserved review edit');
  const controlsTop=await create.boundingBox(),tableTop=await grid.boundingBox();assert(controlsTop.y<tableTop.y,'Replacement controls buried below rows');
  await grid.getByRole('button',{name:'Next',exact:true}).click();await grid.getByText('Workbook row 51',{exact:true}).waitFor();
  await grid.getByRole('button',{name:'Previous',exact:true}).click();await correction.waitFor();assert.equal(await correction.inputValue(),'Preserved review edit');
  await page.getByRole('tab',{name:'Hierarchy',exact:true}).click();await hierarchy.getByText('Saved row edited',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Continue import',exact:true}).click();assert.equal(await correction.inputValue(),'Preserved review edit');
  await grid.getByLabel('More actions for import row 1',{exact:true}).click();
  const menu=grid.locator('details[open]');assert.deepEqual(await menu.getByRole('button').allTextContents(),['Insert row above','Insert row below','Duplicate row','Delete row']);
  await page.keyboard.press('Escape');assert.equal(await grid.locator('details[open]').count(),0);
  await grid.locator('tbody tr').first().getByRole('button',{name:'Save',exact:true}).click();
  await page.getByRole('button',{name:'Retry comparison',exact:true}).waitFor();assert.equal(reviews,1);assert.equal(await correction.inputValue(),'Preserved review edit');
  await page.getByRole('button',{name:'Retry comparison',exact:true}).click();await page.getByText(/Comparison updated against/).waitFor();
  await grid.locator('tbody tr').first().getByRole('button',{name:'Save',exact:true}).click();
  await grid.getByText('Preserved review edit',{exact:true}).waitFor();assert.equal(await correction.count(),0,'Row Save did not return readable mode');
  await grid.getByRole('combobox',{name:'Comparison filter',exact:true}).selectOption('removed');await grid.getByText('Saved row edited',{exact:true}).waitFor();
  assert.equal(await grid.getByRole('button',{name:'Edit',exact:true}).count(),0);
  await grid.getByRole('button',{name:'Clear filters',exact:true}).click();await grid.getByText('Preserved review edit',{exact:true}).waitFor();
  await grid.locator('.admin-grid-scroll').evaluate(el=>{el.scrollLeft=0;});await page.evaluate(()=>window.scrollTo(0,0));
  fs.mkdirSync(path.resolve(cwd,'../../../work'),{recursive:true});await page.screenshot({path:path.resolve(cwd,'../../../work/curriculum-import-workspace.png'),fullPage:true});
  const confirm=page.locator('.admin-replacement-warning input');await confirm.fill('REPLACE TN_StateBoard');await create.click();
  await page.getByText('Replacement rejected; no draft changes saved.').waitFor();assert.equal(saved[5],'Saved row edited');
  await create.dblclick();await page.getByText('Replacement draft created. Review and publish when ready.').waitFor();assert.equal(commits,2);
  await hierarchy.getByText('Preserved review edit',{exact:true}).waitFor();assert.equal(await page.locator('.admin-pending-import').count(),0);
  await page.getByRole('button',{name:'Publish changes',exact:true}).click();await page.getByText('Curriculum update published successfully — revision 14.').waitFor();
  await page.getByRole('tab',{name:'Import History',exact:true}).click();await page.getByText('Fixture.xlsx · committed',{exact:true}).waitFor();
  await page.getByText(/replacement draft created ·/).waitFor();
  await page.getByRole('tab',{name:'Hierarchy',exact:true}).click();await page.reload({waitUntil:'networkidle'});await hierarchy.getByText('Preserved review edit',{exact:true}).waitFor();
  assert.equal(await page.locator('.admin-pending-import').count(),0,'Completed import restored after refresh');
  await page.getByLabel('More curriculum actions',{exact:true}).click();await page.getByRole('button',{name:'Permanently delete curriculum',exact:true}).click();
  await page.getByRole('dialog').getByText('Deletion blocked',{exact:true}).waitFor();
  assert(await page.getByRole('dialog').getByRole('button',{name:'Permanently delete curriculum',exact:true}).isDisabled());
  await page.getByRole('dialog').getByRole('button',{name:'Cancel',exact:true}).click();
  await page.getByRole('button',{name:'← All curricula',exact:true}).click();
  await page.getByRole('button',{name:'Create curriculum',exact:true}).click();
  await page.getByRole('textbox',{name:'Curriculum code',exact:true}).fill('TN_StateBoard');await page.getByRole('textbox',{name:'Curriculum name',exact:true}).fill('New fixture');
  await page.getByRole('button',{name:'Create draft',exact:true}).click();await page.getByText('Curriculum created. Review the draft before publishing.').waitFor();
  await hierarchy.getByRole('button',{name:'Add row',exact:true}).first().click();
  for(const [field,value] of Object.entries({level:'Grade 1',subject:'Science',domain:'Motion',topic:'Gravity',subtopic:'First lesson'})) await hierarchy.getByRole('combobox',{name:field+' row 1',exact:true}).fill(value);
  await hierarchy.getByRole('button',{name:'Save',exact:true}).click();await hierarchy.getByText('First lesson',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Publish changes',exact:true}).click();await page.getByText('Curriculum published successfully — revision 1.').waitFor();
  assert.deepEqual(errors,[]);
  fs.mkdirSync(path.resolve(cwd,'../../../work'),{recursive:true});await page.screenshot({path:path.resolve(cwd,'../../../work/curriculum-workspace.png')});
  console.log('PASS: coherent tabs/reload, saved hierarchy accessible during import, readable row saves, editing menu, page preservation, stale preview blocked/recovered, failed replacement atomic, successful replacement clears pending state, history, guarded delete dialog, first/update publication.');
 }catch(error){
  if(page){fs.mkdirSync(path.resolve(cwd,'../../../work'),{recursive:true});await page.screenshot({path:path.resolve(cwd,'../../../work/curriculum-workspace-failure.png')});fs.writeFileSync(path.resolve(cwd,'../../../work/curriculum-workspace-failure.html'),await page.content());}
  throw error;
 }finally{await browser?.close();server.kill();mock.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
