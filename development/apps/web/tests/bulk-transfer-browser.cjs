const assert=require('node:assert/strict'),http=require('node:http'),path=require('node:path'),fs=require('node:fs');
const {spawn}=require('node:child_process');
const {chromium}=require(path.resolve(__dirname,'../../../../.kilo/ui-check/node_modules/playwright'));
const cwd=path.resolve(__dirname,'..'),base='http://localhost:3119';
const id=n=>`${String(n).padStart(8,'0')}-1111-4111-8111-111111111111`;
const curriculum={id:id(1),code:'bulk',name:'Bulk fixture',version:1,revision:1,published_revision:1,draft_revision:1,state:'published',levels:[]};
const json=(res,data,status=200)=>{res.writeHead(status,{'content-type':'application/json'});res.end(JSON.stringify(data));};
const jobs=new Map(),commits={};let sequence=20,failOnce=true,invalidNext=false;
const workbook=fs.readFileSync(path.resolve(cwd,'public/bulk-import-samples/students/students.xlsx'));
const mock=http.createServer(async(req,res)=>{
 const route=new URL(req.url,'http://fixture').pathname.replace('/api/v1/','');
 if(route==='me')return json(res,{id:id(99),email:'bulk@example.test',role:'admin'});
 if(route==='admin/curricula')return json(res,{items:[curriculum]});
 if(route.endsWith('/tree'))return json(res,curriculum);
 if(route.endsWith('/revisions')||route==='admin/curriculum/imports'||route==='admin/resources/paths')return json(res,{items:[]});
 const transfer=route.match(/^admin\/bulk\/(resources|teachers|students|activity-kits)\/(preview|export|template)$/);
 if(transfer){const kind=transfer[1];
  if(transfer[2]!=='preview'){res.writeHead(200,{'content-type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','content-disposition':`attachment; filename="${kind}.xlsx"`});return res.end(workbook);}
  for await(const chunk of req){};
  const job={id:id(sequence++),kind,filename:kind+'.xlsx',status:'review',preview_token:'a'.repeat(64),total:2,counts:{add:1,merge:1,unchanged:0,invalid:0},rows:[{row:2,record_key:'new',name:'New '+kind,operation:'add',errors:[],preserved_fields:[],fields_to_fill:[],mappings_to_add:1},{row:3,record_key:'existing',name:'Existing '+kind,operation:'merge',existing_id:id(50),errors:[],preserved_fields:['name'],fields_to_fill:['description'],mappings_to_add:1}]};if(invalidNext){invalidNext=false;job.counts={add:1,merge:0,unchanged:0,invalid:1};job.rows[1]={row:3,record_key:'auto-resources-test',name:'New Interactive',operation:'invalid',errors:['1 validation error for LearningMetadata purposes.0 Input should be explain, demonstrate, practise or human_help [type=literal_error, input_value=explore]']};}jobs.set(job.id,job);return json(res,job);
 }
 const operation=route.match(/^admin\/bulk\/imports\/([0-9a-f-]+)(?:\/(review|commit|cancel))?$/);
 if(operation){const job=jobs.get(operation[1]);if(!job)return json(res,{error:{message:'Not found'}},404);if(!operation[2])return json(res,job);
  const chunks=[];for await(const chunk of req)chunks.push(chunk);const body=JSON.parse(Buffer.concat(chunks).toString()||'{}');
  if(operation[2]==='cancel'){job.status='cancelled';return json(res,job);}
  if(operation[2]==='review'){job.preview_token='b'.repeat(64);return json(res,job);}
  commits[job.kind]=(commits[job.kind]||0)+1;await new Promise(r=>setTimeout(r,150));
  if(job.kind==='resources'&&failOnce){failOnce=false;return json(res,{error:{code:'bulk_import_conflict',message:'Catalogue changed. Nothing was imported. Review latest comparison.'}},409);}
  assert.equal(body.preview_token,job.preview_token);assert.equal(body.confirm,true);job.status='completed';job.result={added:1,merged:1,unchanged:0,mappings_added:2};return json(res,job);
 }
 if(['admin/resources','admin/teachers','admin/activity-kits','admin/students'].includes(route))return json(res,{items:[],total:0});
 return json(res,{error:{message:'Not found '+route}},404);
});
(async()=>{let server,browser;try{
 await new Promise(r=>mock.listen(0,'127.0.0.1',r));
 server=spawn(process.execPath,[path.join(cwd,'node_modules/next/dist/bin/next'),'start','--port','3119'],{cwd,windowsHide:true,env:{...process.env,FLAME_WEB_ORIGIN:base,FLAME_API_URL:`http://127.0.0.1:${mock.address().port}`,FLAME_BFF_SHARED_KEY:'fixture-secret'},stdio:'ignore'});
 for(let n=0;n<70;n++){try{if((await fetch(base+'/sign-in')).ok)break;}catch{}await new Promise(r=>setTimeout(r,200));}
 browser=await chromium.launch({channel:'msedge',headless:true});const context=await browser.newContext({viewport:{width:1280,height:900}});await context.addCookies([{name:'flame_session',value:'fixture-session',url:base}]);const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'/admin',{waitUntil:'networkidle'});
 for(const [kind,label] of [['resources','Resource Library'],['teachers','Teachers'],['students','Students'],['activity-kits','Activity Kits']]){
  await page.getByRole('button',{name:label,exact:true}).click();
  const panel=page.locator('.bulk-transfer').filter({has:page.getByRole('button',{name:'Import Excel / ZIP',exact:true})});
  const download=page.waitForEvent('download');await panel.getByRole('button',{name:'Export Excel',exact:true}).click();assert((await download).suggestedFilename().endsWith('.xlsx'));
  await panel.getByRole('button',{name:'Import Excel / ZIP',exact:true}).click();const dialog=page.getByRole('dialog',{name:'Bulk import '+kind.replace('-',' '),exact:true});
  await dialog.getByLabel('Excel workbook or media package').setInputFiles({name:kind+'.xlsx',mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',buffer:workbook});await dialog.getByRole('button',{name:'Validate and preview',exact:true}).click();await dialog.getByText('Keep existing: name',{exact:true}).waitFor();
  assert(await dialog.getByRole('button',{name:'Confirm import',exact:true}).isDisabled());await dialog.getByRole('checkbox').check();await dialog.getByRole('button',{name:'Confirm import',exact:true}).dblclick();
  if(kind==='resources'){await dialog.getByRole('alert').filter({hasText:'Nothing was imported'}).waitFor();await dialog.getByRole('button',{name:'Review latest comparison',exact:true}).click();assert(await dialog.getByRole('button',{name:'Confirm import',exact:true}).isDisabled());await dialog.getByRole('checkbox').check();await dialog.getByRole('button',{name:'Confirm import',exact:true}).click();}
  await dialog.getByRole('button',{name:'Return to catalogue',exact:true}).waitFor();await dialog.getByRole('button',{name:'Return to catalogue',exact:true}).click();await panel.getByRole('status').filter({hasText:'Import completed'}).waitFor();assert.equal(commits[kind],kind==='resources'?2:1);
 }
 await page.getByRole('button',{name:'Students',exact:true}).click();await page.getByRole('button',{name:'Import Excel / ZIP',exact:true}).click();const dialog=page.getByRole('dialog',{name:'Bulk import students',exact:true});await dialog.getByLabel('Excel workbook or media package').setInputFiles({name:'students.xlsx',mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',buffer:workbook});await dialog.getByRole('button',{name:'Validate and preview',exact:true}).click();await dialog.getByText('Keep existing: name',{exact:true}).waitFor();
 await page.setViewportSize({width:390,height:800});assert(await dialog.evaluate(e=>e.getBoundingClientRect().width<=innerWidth));await page.screenshot({path:path.resolve(cwd,'../../../work/bulk-transfer-narrow.png'),fullPage:true});page.once('dialog',d=>d.accept());await page.keyboard.press('Escape');await dialog.waitFor({state:'hidden'});assert.equal(commits.students,1);assert.deepEqual(errors,[]);
 await page.getByRole('button',{name:'Resource Library',exact:true}).click();invalidNext=true;await page.getByRole('button',{name:'Import Excel / ZIP',exact:true}).click();const invalidDialog=page.getByRole('dialog',{name:'Bulk import resources',exact:true});await invalidDialog.getByLabel('Excel workbook or media package').setInputFiles({name:'resources.xlsx',mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',buffer:workbook});await invalidDialog.getByRole('button',{name:'Validate and preview',exact:true}).click();await invalidDialog.getByText(/purposes: use explain/).waitFor();assert(await invalidDialog.getByRole('button',{name:'Confirm import',exact:true}).isDisabled());assert(await invalidDialog.getByRole('checkbox').isDisabled());await invalidDialog.getByText('Confirmation blocked: 1 invalid rows.',{exact:true}).waitFor();await invalidDialog.getByRole('button',{name:'Show first invalid row',exact:true}).click();await invalidDialog.locator('#resources-bulk-row-3').waitFor();await page.reload({waitUntil:'networkidle'});await page.getByRole('button',{name:'Resource Library',exact:true}).click();await page.getByRole('button',{name:'Import Excel / ZIP',exact:true}).click();await page.getByRole('dialog',{name:'Bulk import resources',exact:true}).getByText(/purposes: use explain/).waitFor();page.once('dialog',d=>d.accept());await page.getByRole('dialog',{name:'Bulk import resources',exact:true}).getByRole('button',{name:'Cancel import',exact:true}).click();assert.deepEqual(errors,[]);
 console.log('PASS: invalid legacy preview row without optional arrays renders its actual error, blocks commit, resumes after reload and cancels without crashing.');
 console.log('PASS: four-module import/export controls, binary BFF downloads, confirmation, duplicate-submit guard, stale comparison recovery, success/list refresh, cancellation, keyboard Escape and narrow dialog.');
}finally{await browser?.close();server?.kill();await new Promise(r=>mock.close(r));}})().catch(error=>{console.error(error);process.exitCode=1;});
