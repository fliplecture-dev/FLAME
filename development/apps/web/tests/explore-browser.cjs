const assert = require('node:assert/strict');
const http = require('node:http');
const path = require('node:path');
const {spawn} = require('node:child_process');
const {chromium} = require(path.resolve(__dirname,'../../../../.kilo/ui-check/node_modules/playwright'));
const AxeBuilder = require(path.resolve(__dirname,'../../../../.kilo/ui-check/node_modules/@axe-core/playwright')).default;
const cwd=path.resolve(__dirname,'..'), base='http://localhost:3123';
const uid=n=>`${String(n).padStart(8,'0')}-1111-4111-8111-111111111111`;
const ids={c:uid(1),l:uid(2),s:uid(3),d:uid(4),t:uid(5),st:uid(6),other:uid(7)};
const tree={id:ids.c,name:'Explore curriculum',revision:17,levels:[{id:ids.l,name:'Grade 2',subjects:[{id:ids.s,name:'Science',domains:[{id:ids.d,name:'Motion',categories:[],topics:[{id:ids.t,name:'Gravity',subtopics:[{id:ids.st,name:'Falling objects'}]},{id:ids.other,name:'Light',subtopics:[{id:uid(8),name:'Shadows'}]}]}]}]}]};
const context={curriculum_id:ids.c,level_id:ids.l,subject_id:ids.s,domain_id:ids.d,category_id:null,topic_id:ids.t,subtopic_id:ids.st,names:{topic:'Gravity',subtopic:'Falling objects'}};
const row={id:uid(10),mode:'study',context,revision:17,pinned:false,first_question:'Explain gravity',created_at:new Date().toISOString(),updated_at:new Date().toISOString(),recent_at:new Date().toISOString()};
let listings=0, acknowledgements=0, unavailable=false, openRequests=0, currentRevision=17;
const openScopes=[];
const curiosityRow={...row,id:uid(11),mode:'curiosity',context:null,revision:null,first_question:'Explain gravity in curiosity'};
const curiosityContexts=new Map([[uid(41),{...context,subtopic_id:null}]]);
let curiosityAnswer=41;
const item=(n,kind='resource')=>({mime_type:kind==='resource'?'image/png':null,alt_text:'Gravity learning illustration',id:uid(100+n),version:2,kind,type:kind==='resource'?'diagram':kind==='kit'?'activity_kit':'tutor',title:kind==='resource'?`Gravity ${String(n).padStart(3,'0')}`:kind==='kit'?'Gravity kit':'Gravity teacher',description:'Useful learning detail',...(kind==='resource'&&n===0?{type:'video',mime_type:null,thumbnail_url:'https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg'}:kind==='resource'&&n===1?{type:'video',mime_type:'video/mp4',has_thumbnail:true}:{}),availability_state:kind==='tutor'?'unknown':'available',coverage:'topic',languages:[],grade_min:null,grade_max:null});
const json=(res,data,status=200)=>{res.writeHead(status,{'content-type':'application/json'});res.end(JSON.stringify(data));};
const mock=http.createServer(async(req,res)=>{
 const url=new URL(req.url,'http://fixture'), route=url.pathname.replace('/api/v1/','');
 if(req.headers['x-bff-key']!=='explore-test-secret'||req.headers['x-flame-session']!=='explore-test-session')return json(res,{},401);
 if(route==='me')return json(res,{id:uid(99),role:'admin',email:'explore@example.test'});
 if(route==='curricula')return json(res,{items:[{id:ids.c}]});
 if(route===`curricula/${ids.c}/tree`)return json(res,tree);
 if(route==='me/learning')return json(res,{items:[{id:uid(98),curriculum_id:ids.c,visible:true,version:1}]});
 if(route==='me/activity'||route.endsWith('/recent'))return json(res,{status:'ok'});
 if(route==='sessions')return json(res,{items:[row,curiosityRow],next_cursor:null});
 if(route.endsWith('/capability-check'))return json(res,{status:'continue'});
 if(route.endsWith('/ask')){
   const chunks=[];for await(const chunk of req)chunks.push(chunk);const data=JSON.parse(Buffer.concat(chunks).toString());
   const mid=uid(++curiosityAnswer);curiosityContexts.set(mid,data.question.includes('Light')?{...context,topic_id:ids.other,subtopic_id:null}:data.question.includes('Gravity')?{...context,subtopic_id:null}:data.question.includes('ambiguous')?'ambiguous':null);
   await new Promise(r=>setTimeout(r,100));return json(res,{status:'ok',route:'direct_llm',knowledge_source:'model_generated',grounded:false,message_id:mid,blocks:[{kind:'text',text:'Curiosity answer: '+data.question}]});
 }
 if(route.endsWith('/messages'))return json(res,{items:route.includes(uid(11))?[{id:uid(40),role:'user',turn_number:1,blocks:[{kind:'text',text:'Explain gravity in curiosity'}]},{id:uid(41),role:'assistant',turn_number:1,blocks:[{kind:'text',text:'A saved Curiosity explanation.'}]}]:[{id:uid(20),role:'user',turn_number:1,blocks:[{kind:'text',text:'Explain gravity'}]},{id:uid(21),role:'assistant',turn_number:1,blocks:[{kind:'text',text:'Gravity pulls objects toward Earth.'}]}],next_cursor:null});
 if(route.endsWith('/recommendations'))return json(res,{status:'no_results',resources:[],teachers:[],recommendation_decision:{primary:null,alternative:null}});
 if(route.endsWith('/displayed')){acknowledgements++;return json(res,{status:'ok'});}
 if(route==='explore/summary'){
   const found=url.searchParams.get('session_id')===uid(11)?curiosityContexts.get(url.searchParams.get('message_id')):context;
   return json(res,found?{videos:2,images:103,interactives:0}:{videos:0,images:0,interactives:0});
 }
 if(route==='explore/context'){
   if(url.searchParams.get('session_id')===uid(11)){
     const found=curiosityContexts.get(url.searchParams.get('message_id'));
     if(found==='ambiguous')return json(res,{context:null,candidates:[{...context,subtopic_id:null,curriculum_revision:currentRevision,label:'Grade 2 Gravity'},{...context,topic_id:ids.other,subtopic_id:null,curriculum_revision:currentRevision,label:'Grade 2 Light'}]});
     return json(res,{context:found?{...found,curriculum_revision:currentRevision}:null,candidates:[]});
   }
   return json(res,{context:{...context,curriculum_revision:17}});
 }
 if(route==='explore/curiosity'){
   const kind=url.searchParams.get('kind')||'resource',offset=Number(url.searchParams.get('offset')||0),search=url.searchParams.get('search')||'';
   const paths=[{...context,curriculum_revision:currentRevision,subtopic_id:null},{...context,topic_id:ids.other,curriculum_revision:currentRevision,subtopic_id:null}];
   const all=(kind==='resource'?[item(0),{...item(1),title:'Light from another matching path',browse_path:paths[1]}]:[item(kind==='kit'?300:301,kind)]).map(row=>({...row,browse_path:row.browse_path||paths[0]})).filter(row=>row.title.toLowerCase().includes(search.toLowerCase()));
   return json(res,{items:all.slice(offset,offset+24),total:all.length,offset,limit:24});
 }
 if(route==='explore'){
   listings++;if(Number(url.searchParams.get('curriculum_revision'))!==currentRevision)return json(res,{error:{code:'curriculum_revision_changed',message:'This curriculum changed. Refresh Explore paths.'}},409);const kind=url.searchParams.get('kind')||'resource',q=url.searchParams.get('search')||'',offset=Number(url.searchParams.get('offset')||0);
   if(q==='slow')await new Promise(r=>setTimeout(r,900));
   let all=url.searchParams.get('topic_id')===ids.other?[]:kind==='resource'?Array.from({length:105},(_,n)=>item(n)): [item(kind==='kit'?300:301,kind)];
   if(q)all=all.filter(r=>q==='slow'||q==='fast'||r.title.toLowerCase().includes(q.toLowerCase()));
   if(q==='fast')all=[{...item(999),title:'Fast result'}];
   return json(res,{items:all.slice(offset,offset+24),total:all.length,offset,limit:24,curriculum_revision:17});
 }
 const opened=route.match(/^explore\/(resource|tutor|kit)\/([^/]+)$/);
 if(opened){if(Number(url.searchParams.get('curriculum_revision'))!==currentRevision)return json(res,{error:{code:'curriculum_revision_changed',message:'This curriculum changed. Refresh Explore paths.'}},409);openRequests++;openScopes.push(url.searchParams.get('topic_id'));if(!url.searchParams.get('topic_id'))return json(res,{error:{message:'Missing item scope'}},422);if(unavailable)return json(res,{error:{code:'explore_item_unavailable',message:'This item is no longer available for this learning path. Refresh Explore.'}},404);
   const kind=opened[1];let data=kind==='resource'?{id:opened[2],version:2,type:'diagram',title:'Gravity figure',description:'A falling ball',alt_text:'A ball falling toward Earth'}:kind==='kit'?{id:opened[2],version:2,name:'Gravity kit',materials:['Ball'],instructions:'Observe the falling ball.',supervision:'Ask a parent.',prerequisites:'Review materials with a parent.'}:{id:opened[2],version:2,name:'Gravity teacher',languages:['English'],expertise:[],availability:null};
   await new Promise(r=>setTimeout(r,100));return json(res,{item:data,kind,availability_state:kind==='tutor'?'unknown':'available'});
 }
 if(route.endsWith('/delivery'))return json(res,{status:'ok',version:2,launch_mode:'media',url:base+'/fixture.png'});
 if(route.endsWith('/activity'))return json(res,{status:'ok'});
 return json(res,{error:{code:'not_found'}},404);
});
(async()=>{
 await new Promise(r=>mock.listen(0,'127.0.0.1',r));
 const server=spawn(process.execPath,[path.join(cwd,'node_modules/next/dist/bin/next'),'start','-p','3123'],{cwd,windowsHide:true,env:{...process.env,FLAME_API_URL:`http://127.0.0.1:${mock.address().port}`,FLAME_BFF_SHARED_KEY:'explore-test-secret',FLAME_WEB_ORIGIN:base}});
 let browser,log='';server.stdout.on('data',d=>log+=d);server.stderr.on('data',d=>log+=d);
 try{
  let ready=false;for(let i=0;i<40;i++){try{if((await fetch(base+'/sign-in')).ok){ready=true;break;}}catch{}await new Promise(r=>setTimeout(r,500));}assert(ready,log);
  browser=await chromium.launch({channel:'msedge',headless:true});const ctx=await browser.newContext({viewport:{width:1536,height:920}});await ctx.addCookies([{name:'flame_session',value:'explore-test-session',url:base,httpOnly:true}]);const page=await ctx.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/fixture.png',route=>route.fulfill({contentType:'image/png',body:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a3AAAAABJRU5ErkJggg==','base64')}));
  await page.route('https://i.ytimg.com/**',route=>route.fulfill({contentType:'image/png',body:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a3AAAAABJRU5ErkJggg==','base64')}));
  await page.goto(base+'/flame',{waitUntil:'networkidle'});assert.equal(listings,0);
  const brand=page.locator('.desktop-sidebar .flame-mode-brand');
  await brand.locator('summary').press('ArrowUp');await brand.getByRole('menuitemradio',{name:'Curiosity',exact:true}).press('Enter');await page.getByRole('heading',{name:'What are you curious about?',exact:true}).waitFor();
  await brand.locator('summary').press('ArrowDown');await brand.getByRole('menuitemradio',{name:'Study',exact:true}).press('Enter');await page.getByRole('heading',{name:'What will you learn today?',exact:true}).waitFor();
  const trigger=page.getByRole('button',{name:'Explore',exact:true}),panel=page.getByRole('dialog',{name:'Explore',exact:true});
  assert.equal(await page.locator('.workspace-header .explore-trigger .lucide-chevron-left').count(),1);assert.equal(await page.locator('.workspace-header .explore-trigger').count(),1);await trigger.click();await panel.waitFor();assert.equal(await trigger.getAttribute('aria-expanded'),'true');assert.equal(await page.locator('.explore-trigger').count(),1);
  assert.equal(await page.locator('.flame-topbar .explore-trigger').count(),0);
  assert.equal(await page.locator('.workspace-header .explore-trigger').count(),0);
  assert.equal(await panel.locator('.explore-header .explore-trigger .lucide-chevron-right').count(),1);assert.equal(await panel.locator('.explore-header .explore-trigger').count(),1);assert(await panel.evaluate(d=>Math.abs(d.getBoundingClientRect().top-d.querySelector('.explore-trigger').getBoundingClientRect().top)<1));
  assert.equal(await page.locator('.workspace-modes .mode-dropdown').count(),0);
  assert.equal(await page.locator('.flame-topbar > nav').count(),0);
  assert.equal(await panel.locator('.explore-dropdown-controls, .explore-refresh').count(),0);
  assert.equal(await panel.getByRole('combobox',{name:'Media type',exact:true}).count(),0);
  assert.equal(await panel.getByRole('combobox',{name:'Language',exact:true}).count(),0);
  const layout=await page.evaluate(()=>{const search=document.querySelector('.explore-search').getBoundingClientRect();const chips=document.querySelector('.explore-media-chips').getBoundingClientRect();const filters=document.querySelector('.explore-filter-toggle').getBoundingClientRect();return {searchBottom:search.bottom,chipsTop:chips.top,searchRight:search.right,filtersLeft:filters.left,centerDiff:Math.abs((search.top+search.bottom-filters.top-filters.bottom)/2)};});
  assert(layout.searchBottom<=layout.chipsTop+1);assert(layout.filtersLeft>=layout.searchRight);assert(layout.centerDiff<1);
  await page.setViewportSize({width:1090,height:892});await page.waitForTimeout(100);assert(await panel.evaluate(d=>d.matches(':modal')));await panel.getByRole('button',{name:'Explore',exact:true}).click();assert(await panel.evaluate(d=>d.classList.contains('explore-closing')));
  await panel.waitFor({state:'hidden'});await page.waitForFunction(()=>document.activeElement===document.querySelector('.workspace-header .explore-trigger'));const compact=await page.evaluate(()=>{const crumb=document.querySelector('.workspace-breadcrumb').getBoundingClientRect(),explore=document.querySelector('.workspace-header .explore-trigger').getBoundingClientRect();return {crumbRight:crumb.right,buttonLeft:explore.left,centerDiff:Math.abs((explore.top+explore.bottom-crumb.top-crumb.bottom)/2),overflow:document.documentElement.scrollWidth>innerWidth};});assert(compact.crumbRight<=compact.buttonLeft);assert(compact.centerDiff<3);assert(!compact.overflow);
  await page.screenshot({path:path.resolve(cwd,'../../../work/annotations-header-1090.png')});await page.setViewportSize({width:1588,height:892});await trigger.click();await panel.waitFor();

  await panel.getByRole('combobox',{name:'Explore curriculum',exact:true}).selectOption(ids.c);await panel.getByRole('combobox',{name:'Explore level',exact:true}).selectOption(ids.l);await panel.getByRole('combobox',{name:'Explore subject',exact:true}).selectOption(ids.s);await panel.getByRole('combobox',{name:'Explore domain',exact:true}).selectOption(ids.d);await panel.getByRole('combobox',{name:'Explore topic',exact:true}).selectOption(ids.t);
  for(const title of ['Gravity 000','Gravity 001']){const thumb=panel.getByRole('button',{name:'Open thumbnail for '+title,exact:true});await thumb.locator('img').waitFor();assert(await thumb.locator('img').evaluate(img=>img.complete&&img.naturalWidth>0));}
  await panel.getByRole('button',{name:'Open thumbnail for Gravity 000',exact:true}).click();await page.getByRole('dialog',{name:'Gravity figure',exact:true}).waitFor();await page.getByRole('button',{name:'Close resource',exact:true}).click();
  await panel.getByText('105 matching resources',{exact:true}).waitFor();await panel.locator('.explore-thumbnail img').first().waitFor();assert.equal(await page.getByRole('heading',{name:'What will you learn today?',exact:true}).count(),1);
  assert(await panel.evaluate(d=>d.scrollWidth<=d.clientWidth+1));
  const desktop=await page.evaluate(()=>({panel:document.querySelector('.explore-panel').getBoundingClientRect().toJSON(),reading:document.querySelector('.learning-column').getBoundingClientRect().toJSON()}));assert(desktop.reading.right<=desktop.panel.left+1);
  if(await page.locator('.sidebar-rail').isVisible())await page.locator('.sidebar-rail').getByRole('button',{name:'Expand sidebar',exact:true}).click();
  const navBefore=await page.locator('.desktop-sidebar').evaluate(el=>el.getBoundingClientRect().width),listBeforeResize=listings;
  const leftDivider=page.getByRole('separator',{name:'Resize navigation sidebar',exact:true}),rightDivider=page.getByRole('separator',{name:'Resize Explore panel',exact:true});
  let edge=await leftDivider.boundingBox();await page.mouse.move(edge.x+edge.width/2,180);await page.mouse.down();await page.mouse.move(edge.x+edge.width/2+80,180,{steps:8});await page.mouse.up();
  const navAfter=await page.locator('.desktop-sidebar').evaluate(el=>el.getBoundingClientRect().width);assert(navAfter>=navBefore+70);
  const mediaBefore=await panel.evaluate(el=>el.getBoundingClientRect().width);edge=await rightDivider.boundingBox();await page.mouse.move(edge.x+edge.width/2,200);await page.mouse.down();await page.mouse.move(edge.x+edge.width/2-100,200,{steps:8});await page.mouse.up();
  const mediaAfter=await panel.evaluate(el=>el.getBoundingClientRect().width);assert(mediaAfter>=mediaBefore+90);assert(await page.locator('.learning-column').evaluate(el=>el.getBoundingClientRect().width>=399));assert.equal(listings,listBeforeResize);
  const restored=await ctx.newPage();await restored.goto(base+'/flame',{waitUntil:'networkidle'});assert(Math.abs(await restored.locator('.desktop-sidebar').evaluate(el=>el.getBoundingClientRect().width)-navAfter)<2);await restored.getByRole('button',{name:'Explore',exact:true}).click();await restored.getByRole('dialog',{name:'Explore',exact:true}).waitFor();await restored.waitForTimeout(250);assert(Math.abs(await restored.locator('.explore-panel').evaluate(el=>el.getBoundingClientRect().width)-mediaAfter)<2);await restored.close();
  await rightDivider.press('ArrowRight');assert(await panel.evaluate(el=>el.getBoundingClientRect().width)<mediaAfter);await rightDivider.dblclick();await leftDivider.dblclick();
  assert(!await page.locator('.student-app').evaluate(el=>el.classList.contains('pane-resizing')));

  await panel.getByRole('button',{name:'Next',exact:true}).click();await panel.getByText('25–48 of 105',{exact:true}).waitFor();
  await panel.locator('.explore-scroll').evaluate(el=>{el.scrollTop=180;});const savedScroll=await panel.locator('.explore-scroll').evaluate(el=>el.scrollTop),beforeReopen=listings;
  await page.evaluate(()=>{const original=Date.now;Date.now=()=>original()+60000;});
  await panel.getByRole('button',{name:'Explore',exact:true}).click();await panel.waitFor({state:'hidden'});await trigger.click();await panel.getByText('25–48 of 105',{exact:true}).waitFor();
  assert.equal(listings,beforeReopen);assert.equal(await panel.getByRole('status').filter({hasText:'Loading'}).count(),0);await page.waitForFunction(top=>document.querySelector('.explore-scroll').scrollTop===top,savedScroll);

  await panel.getByRole('searchbox',{name:'Search Explore resources',exact:true}).fill('Gravity 104');await panel.getByRole('button',{name:'Open Gravity 104',exact:true}).waitFor();
  await panel.getByRole('button',{name:'Open thumbnail for Gravity 104',exact:true}).press('Enter');const viewer=page.getByRole('dialog',{name:'Gravity figure',exact:true});await viewer.waitFor();await viewer.locator('img').waitFor();await viewer.getByRole('button',{name:'Close resource',exact:true}).click();assert.equal(await panel.getByRole('searchbox',{name:'Search Explore resources',exact:true}).inputValue(),'Gravity 104');
  await panel.getByRole('searchbox',{name:'Search Explore resources',exact:true}).fill('slow');await page.waitForTimeout(350);await panel.getByRole('searchbox',{name:'Search Explore resources',exact:true}).fill('fast');await panel.getByRole('button',{name:'Open Fast result',exact:true}).waitFor();await page.waitForTimeout(1100);assert.equal(await panel.getByRole('button',{name:'Open Fast result',exact:true}).count(),1);
  await panel.getByRole('searchbox',{name:'Search Explore resources',exact:true}).fill('');await page.waitForTimeout(350);await panel.getByRole('tab',{name:'Teachers',exact:true}).click();await panel.getByText(/Availability unknown/).waitFor();await panel.getByRole('button',{name:'Open Gravity teacher',exact:true}).click();const teacher=page.getByRole('dialog',{name:'Gravity teacher',exact:true});await teacher.getByText('Availability: Unknown — confirm with the tutor',{exact:true}).waitFor();await teacher.getByRole('button',{name:'Close resource',exact:true}).click();
  await panel.getByRole('tab',{name:'Activity Kits',exact:true}).click();await panel.getByRole('button',{name:'Open Gravity kit',exact:true}).click();const kit=page.getByRole('dialog',{name:'Gravity kit',exact:true});await kit.getByText('Observe the falling ball.',{exact:true}).waitFor();await kit.getByRole('button',{name:'Close resource',exact:true}).click();
  unavailable=true;await panel.getByRole('button',{name:'Open Gravity kit',exact:true}).click();await panel.getByRole('alert').waitFor();assert.equal(await page.locator('.resource-dialog[open]').count(),0);unavailable=false;
  await panel.getByRole('button',{name:'Explore',exact:true}).click();await trigger.waitFor();
  if(await page.locator('.sidebar-rail').isVisible())await page.locator('.sidebar-rail').getByRole('button',{name:'Expand sidebar',exact:true}).click();
  await page.locator('.desktop-sidebar .shortcut-section').getByRole('button',{name:'Falling objects (study)',exact:true}).click();await page.getByText('Gravity pulls objects toward Earth.',{exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Explore this topic',exact:true}).count(),0);
  await page.getByRole('button',{name:'Explore resources: 2 videos · 103 images',exact:true}).screenshot({path:path.resolve(cwd,'../../../work/explore-answer-counts.png')});
  await page.getByRole('button',{name:'Explore resources: 2 videos · 103 images',exact:true}).click();await panel.getByText('105 matching resources',{exact:true}).waitFor();assert.equal(await panel.locator('select[aria-label="Explore subtopic"]').inputValue(),ids.st);
  await panel.getByRole('button',{name:'Learning path filters',exact:true}).click();await panel.getByRole('combobox',{name:'Explore topic',exact:true}).selectOption(ids.other);await panel.getByText('0 matching resources',{exact:true}).waitFor();assert.equal(await page.getByRole('heading',{name:'Falling objects',exact:true}).count(),1);assert.equal(await panel.locator('select[aria-label="Explore subtopic"]').inputValue(),'');
  // An open Explore follows learning navigation without clicking its trigger.
  for (const [tab,count] of [['Media','105 matching resources'],['Teachers','1 matching teachers'],['Activity Kits','1 matching kits']]) {
    await panel.getByRole('tab',{name:tab,exact:true}).click();
    await page.getByRole('button',{name:'View Gravity topic',exact:true}).click();
    await panel.getByText(count,{exact:true}).waitFor();
    assert.equal(await panel.locator('select[aria-label="Explore topic"]').inputValue(),ids.t);
    assert.equal(await panel.locator('select[aria-label="Explore subtopic"]').inputValue(),'');
    await page.locator('.subtopic-actions').getByRole('button',{name:'Falling objects',exact:true}).click();
    await panel.getByText(count,{exact:true}).waitFor();
    await page.waitForFunction(id=>document.querySelector('select[aria-label="Explore subtopic"]').value===id,ids.st);
  }
  await panel.getByRole('tab',{name:'Media',exact:true}).click();
  await page.locator('.desktop-sidebar .topic-open').getByText('Light',{exact:true}).click();
  await panel.getByText('0 matching resources',{exact:true}).waitFor();
  assert.equal(await panel.locator('select[aria-label="Explore topic"]').inputValue(),ids.other);
  await page.locator('.desktop-sidebar .topic-open').getByText('Gravity',{exact:true}).click();
  await panel.getByText('105 matching resources',{exact:true}).waitFor();
  await page.locator('.subtopic-actions').getByRole('button',{name:'Falling objects',exact:true}).click();
  await page.waitForFunction(id=>document.querySelector('select[aria-label="Explore subtopic"]').value===id,ids.st);
  await page.screenshot({path:path.resolve(cwd,'../../../work/explore-desktop.png')});
  await page.setViewportSize({width:390,height:740});await panel.waitFor();assert(await panel.evaluate(d=>d.matches(':modal')));assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.equal(await page.getByRole('separator').count(),0);if(await panel.getByRole('button',{name:'Learning path filters',exact:true}).getAttribute('aria-expanded')==='false')await panel.getByRole('button',{name:'Learning path filters',exact:true}).click();await panel.getByRole('combobox',{name:'Explore topic',exact:true}).selectOption(ids.t);await panel.getByRole('combobox',{name:'Explore subtopic',exact:true}).selectOption(ids.st);await panel.getByText('105 matching resources',{exact:true}).waitFor();await page.screenshot({path:path.resolve(cwd,'../../../work/explore-mobile.png')});currentRevision=18;tree.revision=18;const retainedListings=listings;await panel.getByRole('button',{name:'Explore',exact:true}).click();await panel.waitFor({state:'hidden'});await trigger.click();await panel.getByText('105 matching resources',{exact:true}).waitFor();assert.equal(listings,retainedListings);await panel.getByRole('button',{name:'Open Gravity 000',exact:true}).click();await panel.getByRole('alert').waitFor();assert.equal(await panel.getByRole('alert').locator('button').count(),0);await panel.getByRole('button',{name:'Explore',exact:true}).click();await trigger.click();await panel.getByText('105 matching resources',{exact:true}).waitFor();assert.equal(await panel.locator('select[aria-label="Explore subtopic"]').inputValue(),ids.st);
  const buttons=panel.locator('button:visible');await buttons.last().focus();await page.keyboard.press('Tab');assert(await panel.evaluate(d=>d.contains(document.activeElement)));await page.keyboard.press('Escape');await panel.waitFor({state:'hidden'});assert.equal(await trigger.getAttribute('aria-expanded'),'false');assert.equal(acknowledgements,0);await page.locator('.workspace-modes').getByRole('button',{name:'Curiosity',exact:true}).click();await trigger.click();await panel.getByRole('searchbox',{name:'Find a learning path',exact:true}).fill('Falling objects');await panel.locator('.explore-path-matches button').first().click();await panel.getByText('105 matching resources',{exact:true}).waitFor();assert.equal(await page.getByRole('heading',{name:'What are you curious about?',exact:true}).count(),1);await page.keyboard.press('Escape');await panel.waitFor({state:'hidden'});assert.deepEqual(errors,[]);
  await page.setViewportSize({width:1588,height:892});
  if(await page.locator('.sidebar-rail').isVisible())await page.locator('.sidebar-rail').getByRole('button',{name:'Expand sidebar',exact:true}).click();
  await page.locator('.desktop-sidebar .shortcut-section').getByRole('button',{name:'Explain gravity in curiosity (curiosity)',exact:true}).click();
  await page.getByText('A saved Curiosity explanation.',{exact:true}).waitFor();await trigger.click();
  await panel.getByText('105 matching resources',{exact:true}).waitFor();
  const ask=async question=>{await page.locator('#flame-prompt').fill(question);await page.getByRole('button',{name:'Send learning request',exact:true}).click();await page.getByText('Curiosity answer: '+question,{exact:true}).waitFor();};
  await ask('Explain Light');await panel.getByText('0 matching resources',{exact:true}).waitFor();assert.equal(await panel.locator('select[aria-label="Explore topic"]').inputValue(),ids.other);
  await panel.getByRole('tab',{name:'Activity Kits',exact:true}).click();await ask('Explain Gravity');await panel.getByText('1 matching kits',{exact:true}).waitFor();const curiosityListings=listings;await panel.getByRole('button',{name:'Explore',exact:true}).click();await panel.waitFor({state:'hidden'});await trigger.click();await panel.getByText('1 matching kits',{exact:true}).waitFor();assert.equal(listings,curiosityListings);
  await panel.getByRole('tab',{name:'Teachers',exact:true}).click();await panel.getByText('1 matching teachers',{exact:true}).waitFor();
  await page.screenshot({path:path.resolve(cwd,'../../../work/explore-curiosity-gravity.png')});
  await ask('Explain dinosaurs');await panel.getByText('No published learning path matches this question.',{exact:true}).waitFor();assert.equal(await panel.locator('.explore-item').count(),0);
  assert.equal(await page.locator('.conversation-turn').filter({hasText:'Curiosity answer: Explain dinosaurs'}).getByRole('button',{name:/Explore resources:/}).count(),0,'Empty results must not display an answer Explore link');
  await ask('Explain ambiguous');await panel.getByText('1 matching teachers',{exact:true}).waitFor();assert.equal(await panel.getByRole('list',{name:'Matching learning paths'}).count(),0);
  await panel.getByRole('button',{name:'Open Gravity teacher',exact:true}).click();await page.getByRole('dialog',{name:'Gravity teacher',exact:true}).getByRole('button',{name:'Close resource',exact:true}).click();
  await panel.getByRole('tab',{name:'Activity Kits',exact:true}).click();await panel.getByText('1 matching kits',{exact:true}).waitFor();
  await panel.getByRole('tab',{name:'Media',exact:true}).click();await panel.getByText('2 matching resources',{exact:true}).waitFor();await panel.getByRole('button',{name:'Open Light from another matching path',exact:true}).click();
  await page.getByRole('dialog',{name:'Gravity figure',exact:true}).getByRole('button',{name:'Close resource',exact:true}).click();
  assert.equal(openScopes.at(-1),ids.other);
  await panel.getByRole('searchbox',{name:'Search Explore resources',exact:true}).fill('another matching path');await panel.getByText('1 matching resources',{exact:true}).waitFor();
  await page.screenshot({path:path.resolve(cwd,'../../../work/explore-curiosity.png')});await page.emulateMedia({reducedMotion:'reduce'});assert.equal(await panel.evaluate(d=>getComputedStyle(d).animationName),'none');await panel.getByRole('button',{name:'Explore',exact:true}).click();await panel.waitFor({state:'hidden'});assert.deepEqual(errors,[]);
  // Frontend-only dark palette: expanded account, Browse Media and compact rail.
  require('node:fs').mkdirSync(path.resolve(cwd,'../../../work/theme'),{recursive:true});
  await page.setViewportSize({width:1536,height:920});
  const expand=page.getByRole('button',{name:'Expand sidebar',exact:true});if(await expand.isVisible())await expand.click();
  await page.emulateMedia({colorScheme:'light'});
  await page.getByRole('button',{name:'Switch to dark mode',exact:true}).click();
  const admin=page.locator('.desktop-sidebar .profile-admin-link');await admin.waitFor({state:'visible'});
  async function contrast(locator,minimum=4.5){
    const ratio=await locator.evaluate(el=>{
      const css=getComputedStyle(el);
      function luminance(color){const rgb=color.match(/[\d.]+/g).slice(0,3).map(Number).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4});return .2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2];}
      const a=luminance(css.color),b=luminance(css.backgroundColor);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
    });assert(ratio>=minimum,'Dark contrast '+ratio+' below '+minimum);
  }
  await contrast(admin);await admin.hover();await contrast(admin);
  await trigger.click();await panel.waitFor({state:'visible'});await panel.getByRole('heading',{name:'Browse Media',exact:true}).waitFor();
  const pathFilters=panel.getByRole('button',{name:'Learning path filters',exact:true});if(await pathFilters.getAttribute('aria-expanded')!=='true')await pathFilters.click();
  for(const tab of await panel.getByRole('tab').all())await contrast(tab);
  const openMedia=panel.getByRole('button',{name:/^Open (?!thumbnail)/}).first();await openMedia.waitFor();await contrast(openMedia);await openMedia.hover();await contrast(openMedia);
  const mediaAudit=await new AxeBuilder({page}).include('.explore-panel').include('.desktop-sidebar .sidebar-account').withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
  assert.deepEqual(mediaAudit.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),[]);
  await page.screenshot({path:path.resolve(cwd,'../../../work/theme/dark-browse-media.png')});
  await panel.getByRole('button',{name:'Explore',exact:true}).click();await panel.waitFor({state:'hidden'});
  await page.getByRole('button',{name:'Collapse sidebar',exact:true}).click();
  const rail=page.locator('.sidebar-rail');await rail.waitFor({state:'visible'});
  await contrast(rail.locator('.profile-admin-link'));
  for(const button of await rail.locator('.rail-button').all()){
    // Transparent idle controls inherit the rail surface; selected/hover states are opaque.
    await button.hover();await contrast(button);await button.focus();
    assert.equal(await button.evaluate(el=>getComputedStyle(el,'::after').opacity),'1');
  }
  const railAudit=await new AxeBuilder({page}).include('.sidebar-rail').withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();assert.deepEqual(railAudit.violations.map(v=>v.id),[]);
  await page.screenshot({path:path.resolve(cwd,'../../../work/theme/dark-compact-sidebar.png')});
  await page.setViewportSize({width:390,height:844});await trigger.click();await panel.waitFor({state:'visible'});assert(await panel.evaluate(el=>el.scrollWidth<=el.clientWidth+1));
  await page.screenshot({path:path.resolve(cwd,'../../../work/theme/dark-browse-media-mobile.png')});
  const mobileAudit=await new AxeBuilder({page}).include('.explore-panel').withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();assert.deepEqual(mobileAudit.violations.map(v=>v.id),[]);
  assert.deepEqual(errors,[]);
  console.log('PASS: dark admin link, Browse Media controls/cards/filters and compact rail icons/tooltips: contrast, accessibility, desktop/mobile.');
  console.log('PASS: Explore Study and Curiosity following, multi-path automatic results across all catalogues, per-item scoped open/delivery, combined search, saved Curiosity restore, unmatched clearing, independent path, stale async suppression, viewers, desktop/mobile/focus.');
 }finally{await browser?.close();server.kill();mock.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
