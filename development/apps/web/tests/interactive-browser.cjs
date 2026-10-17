const assert=require('node:assert/strict'),http=require('node:http'),path=require('node:path'),fs=require('node:fs');
const {spawn}=require('node:child_process');
const {chromium}=require(path.resolve(__dirname,'../../../../.kilo/ui-check/node_modules/playwright'));
const cwd=path.resolve(__dirname,'..'),base='http://localhost:3135';
const id=n=>`${String(n).padStart(8,'0')}-1111-4111-8111-111111111111`;
const tree={id:id(1),code:'interactive-fixture',name:'Interactive curriculum',state:'published',version:2,revision:17,published_revision:17,draft_revision:1,
 levels:[{id:id(2),name:'Grade 1',subjects:[{id:id(3),name:'Science',domains:[{id:id(4),name:'Motion',categories:[],topics:[{id:id(5),name:'Gravity',subtopics:[{id:id(6),name:'Falling'}]}]}]}]}]};
const context={curriculum_id:id(1),level_id:id(2),subject_id:id(3),domain_id:id(4),category_id:null,topic_id:id(5),subtopic_id:null,curriculum_revision:17};
const html=fs.readFileSync(path.resolve(cwd,'../../../work/gravity-lab-html5.html'),'utf8');
let role='admin',saved=null,uploads=0,thumbnailUploads=0,createBody=null,opens=0;
const existing=[{id:id(800),title:'Existing image',type:'image',mime_type:'image/png'}, {id:id(801),title:'Existing video',type:'video',mime_type:'video/webm'}].map(row=>({...row,source:'upload',paths:[],path_details:[],version:1,published:false,availability:'available',alt_text:'Existing media fixture'}));
const json=(res,data,status=200)=>{res.writeHead(status,{'content-type':'application/json'});res.end(JSON.stringify(data));};
const body=async req=>{const chunks=[];for await(const chunk of req)chunks.push(chunk);return Buffer.concat(chunks);};
const mock=http.createServer(async(req,res)=>{
 const url=new URL(req.url,'http://test'),route=url.pathname.replace('/api/v1/','');
 if(route==='me')return json(res,{id:id(99),role,email:'interactive@example.test'});
 if(route==='admin/curricula')return json(res,{items:[tree]});
 if(route==='curricula')return json(res,{items:[{id:id(1)}]});
 if(route.endsWith('/tree'))return json(res,tree);
 if(route.endsWith('/revisions')||route==='admin/curriculum/imports')return json(res,{items:[]});
 if(route==='me/learning')return json(res,{items:[{id:id(98),curriculum_id:id(1),visible:true,version:1}]});
 if(route==='sessions')return json(res,{items:[],next_cursor:null});
 if(route==='me/activity'||route.endsWith('/recent'))return json(res,{status:'ok'});
 if(route==='admin/resources/paths')return json(res,{items:[{...context,label:'Interactive curriculum / Grade 1 / Science / Motion / Gravity',available_for_publication:true}]});
 if(route==='admin/resources/uploads'){
   const data=await body(req);if(data.includes(Buffer.from('poster.png'))){thumbnailUploads++;return json(res,{upload_id:id(701),mime_type:'image/png',byte_size:100},201);}assert(data.includes(Buffer.from('lab.html')));uploads++;
   return json(res,{upload_id:id(700),mime_type:'text/html',media_type:'interactive',byte_size:html.length},201);
 }
 if(route==='admin/resources/'+id(801)&&req.method==='PATCH'){const patch=JSON.parse((await body(req)).toString());assert.equal(patch.thumbnail_upload_id,id(701));Object.assign(existing[1],patch,{has_thumbnail:true,thumbnail_upload_id:id(701),version:2});return json(res,existing[1]);}
 if(route==='admin/resources'){
   if(req.method==='GET')return json(res,{items:[...existing,...(saved?[saved]:[])],total:existing.length+(saved?1:0)});
   createBody=JSON.parse((await body(req)).toString());
   saved={...createBody,id:createBody.creation_id,source:'upload',external_url:null,version:1,published:false,mime_type:'text/html',file_name:'lab.html',path_details:[],updated_at:new Date().toISOString()};
   return json(res,saved,201);
 }
 if(route.match(/^admin\/resources\/[0-9a-f-]+\/preview$/)){
   if(url.searchParams.get('thumbnail')==='true')return json(res,{url:base+'/existing.png',launch_mode:'media'});
   const fixture=existing.find(row=>route.includes(row.id));
   if(fixture)return json(res,{url:base+'/existing.'+(fixture.type==='image'?'png':'webm'),launch_mode:'media'});
   return json(res,{url:'',launch_mode:'interactive',html_document:html,version:1,expires_at:null});
 }
 if(route==='explore/context')return json(res,{context,candidates:[]});
 if(route==='explore')return json(res,{items:saved?[{...saved,kind:'resource',coverage:'topic',availability_state:'available'}]:[],total:saved?1:0,offset:0,limit:30});
 if(route.match(/^explore\/resource\/[0-9a-f-]+$/))return json(res,{item:saved,kind:'resource',availability_state:'available'});
 if(route.endsWith('/delivery')){assert.equal(url.searchParams.get('version'),'1');return json(res,{url:'',status:'ok',launch_mode:'interactive',html_document:html,version:1,expires_at:null});}
 if(route.endsWith('/activity')){opens++;return json(res,{status:'ok'});}
 return json(res,{},404);
});
(async()=>{
 await new Promise(r=>mock.listen(0,'127.0.0.1',r));
 const server=spawn(process.execPath,[path.join(cwd,'node_modules/next/dist/bin/next'),'start','-p','3135'],{cwd,windowsHide:true,env:{...process.env,FLAME_API_URL:`http://127.0.0.1:${mock.address().port}`,FLAME_BFF_SHARED_KEY:'interactive-test-key',FLAME_WEB_ORIGIN:base}});
 let browser,log='';server.stdout.on('data',d=>log+=d);server.stderr.on('data',d=>log+=d);
 try{
  let ready=false;for(let i=0;i<50;i++){try{if((await fetch(base+'/sign-in')).ok){ready=true;break;}}catch{}await new Promise(r=>setTimeout(r,300));}assert(ready,log);
  browser=await chromium.launch({channel:'msedge',headless:true});const ctx=await browser.newContext({viewport:{width:1440,height:920},reducedMotion:'reduce'});
  await ctx.addCookies([{name:'flame_session',value:'interactive-fixture',url:base,httpOnly:true}]);const page=await ctx.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/existing.png',route=>route.fulfill({contentType:'image/png',body:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a3AAAAABJRU5ErkJggg==','base64')}));
  await page.route('**/existing.webm',route=>route.fulfill({contentType:'video/webm',body:fs.readFileSync(path.join(cwd,'public/learning-assets/gravity.webm'))}));
  await page.goto(base+'/admin',{waitUntil:'networkidle'});await page.getByRole('button',{name:'Resource Library',exact:true}).click();const panel=page.locator('.b9-resource-panel');
  for(const fixture of existing){
   await panel.locator('tbody tr').filter({hasText:fixture.title}).getByRole('button',{name:'Preview',exact:true}).click();const preview=page.getByRole('dialog',{name:'Preview '+fixture.title,exact:true});await preview.waitFor();
   if(fixture.type==='image'){await preview.locator('img').waitFor();await page.waitForFunction(()=>document.querySelector('dialog img')?.naturalWidth>0);}
   else{await preview.locator('video').evaluate(video=>video.loop=true);await preview.getByRole('button',{name:'Play video',exact:true}).click();await preview.getByRole('button',{name:'Pause video',exact:true}).click();}
   assert.equal(await preview.locator('iframe').count(),0);await preview.getByRole('button',{name:'Close preview',exact:true}).click();
  }
  await panel.getByRole('button',{name:'Actions for Existing video',exact:true}).click();await page.getByRole('menuitem',{name:'Edit',exact:true}).click();
  await panel.getByLabel('Thumbnail image',{exact:true}).setInputFiles({name:'poster.png',mimeType:'image/png',buffer:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a3AAAAABJRU5ErkJggg==','base64')});
  await panel.getByAltText('Video thumbnail preview',{exact:true}).waitFor();await panel.getByRole('button',{name:'Save draft',exact:true}).click();await panel.getByText('Resource changes saved',{exact:true}).waitFor();assert.equal(thumbnailUploads,1);assert(existing[1].has_thumbnail);
  await panel.getByRole('button',{name:'+ Add resource',exact:true}).click();await panel.getByRole('combobox',{name:'Media type',exact:true}).selectOption('interactive');
  assert.equal(await panel.getByRole('combobox',{name:'Media source',exact:true}).count(),0);
  assert.equal(await panel.getByLabel('Upload HTML5 file',{exact:true}).getAttribute('accept'),'.html,.htm,text/html');
  await panel.getByRole('textbox',{name:'Title',exact:true}).fill('Gravity HTML5');await panel.getByRole('textbox',{name:'Rights holder',exact:true}).fill('Fixture');
  await panel.getByRole('textbox',{name:'Accessibility note',exact:true}).fill('Tab and Enter operate controls. Arrow keys lift the ball.');
  await panel.getByLabel('Upload HTML5 file',{exact:true}).setInputFiles({name:'lab.html',mimeType:'text/html',buffer:Buffer.from(html)});
  await page.waitForFunction(value=>document.querySelector('.resource-html-editor textarea')?.value===value,html.replace(/\r\n/g,'\n'));await panel.getByRole('tab',{name:'Preview',exact:true}).click();
  let frame=page.frameLocator('iframe[title="Gravity HTML5"]');await frame.getByRole('heading',{name:'Gravity Lab',exact:true}).waitFor();
  assert.equal(await page.locator('iframe').first().getAttribute('sandbox'),'allow-scripts');
  await frame.locator('#start').click();await frame.locator('#time-metric').filter({hasText:'s'}).waitFor();
  await panel.getByRole('button',{name:'Save draft',exact:true}).click();await panel.getByText('Resource added successfully',{exact:true}).waitFor();assert.equal(uploads,1);assert.equal(createBody.type,'interactive');assert.equal(createBody.upload_id,id(700));assert(!('external_url' in createBody));
  const row=panel.locator('tbody tr').filter({hasText:'Gravity HTML5'});await row.getByText('HTML5',{exact:true}).waitFor();await row.getByRole('button',{name:'Preview',exact:true}).click();
  let dialog=page.getByRole('dialog',{name:'Preview Gravity HTML5',exact:true});await dialog.waitFor();await dialog.locator('iframe').waitFor();await dialog.getByRole('button',{name:'Close preview',exact:true}).click();assert.equal(await page.locator('iframe').count(),0);
  role='member';await page.goto(base+'/flame',{waitUntil:'networkidle'});await page.getByRole('button',{name:'Explore',exact:true}).click();const explore=page.getByRole('dialog',{name:'Explore',exact:true});
  for(const [name,value] of [['curriculum',1],['level',2],['subject',3],['domain',4],['topic',5]])await explore.getByRole('combobox',{name:'Explore '+name,exact:true}).selectOption(id(value));
  await explore.getByRole('button',{name:'Interactive',exact:true}).click();await explore.getByRole('button',{name:'Open Gravity HTML5',exact:true}).click();dialog=page.getByRole('dialog',{name:'Gravity HTML5',exact:true});await dialog.waitFor();
  frame=page.frameLocator('iframe[title="Gravity HTML5"]');await frame.getByRole('heading',{name:'Gravity Lab',exact:true}).waitFor();
  const child=page.frames().find(f=>f!==page.mainFrame());assert.equal(await child.evaluate(()=>{try{return parent.document.title;}catch{return 'isolated';}}),'isolated');
  assert.equal(await child.evaluate(()=>{try{return localStorage.length;}catch{return 'blocked';}}),'blocked');
  await frame.locator('#start').click();await frame.locator('#fallen-metric').filter({hasText:'10.0 m'}).waitFor();
  // Fullscreen operates on the parent-owned viewer, retaining the sandbox and experiment state.
  await child.evaluate(()=>window.fullscreenStateProof='retained');
  await page.evaluate(()=>{
   window.orientationCalls=[];
   Object.defineProperty(screen.orientation,'lock',{configurable:true,value:async value=>window.orientationCalls.push(value)});
   Object.defineProperty(screen.orientation,'unlock',{configurable:true,value:()=>window.orientationCalls.push('unlock')});
  });
  await dialog.getByRole('button',{name:'Full screen interactive',exact:true}).click();
  await page.waitForFunction(()=>document.fullscreenElement?.getAttribute('data-interactive-fullscreen')==='true');
  assert.deepEqual(await page.evaluate(()=>window.orientationCalls),[]);
  assert.equal(await child.evaluate(()=>window.fullscreenStateProof),'retained');
  await frame.locator('#fallen-metric').filter({hasText:'10.0 m'}).waitFor();
  await page.screenshot({path:path.resolve(cwd,'../../../work/interactive-fullscreen-desktop.png')});
  await dialog.getByRole('button',{name:'Restore compact interactive',exact:true}).click();
  await page.waitForFunction(()=>!document.fullscreenElement);
  assert.deepEqual(await page.evaluate(()=>window.orientationCalls),[]);
  assert.equal(await child.evaluate(()=>window.fullscreenStateProof),'retained');
  // Browser-driven exit also restores the icon without closing the resource modal.
  await dialog.getByRole('button',{name:'Full screen interactive',exact:true}).click();
  await page.waitForFunction(()=>!!document.fullscreenElement);
  await page.evaluate(()=>document.exitFullscreen());
  await dialog.getByRole('button',{name:'Full screen interactive',exact:true}).waitFor();
  assert(await dialog.isVisible());
  await dialog.getByRole('button',{name:'Restart interactive',exact:true}).click();await frame.locator('#fallen-metric').filter({hasText:'0.0 m'}).waitFor();
  await frame.locator('#scene').scrollIntoViewIfNeeded();await page.screenshot({path:path.resolve(cwd,'../../../work/interactive-desktop.png')});await dialog.getByRole('button',{name:'Close resource',exact:true}).click();assert.equal(await page.locator('iframe').count(),0);assert(opens>=1);
  await page.setViewportSize({width:390,height:844});await explore.getByRole('button',{name:'Open Gravity HTML5',exact:true}).click();dialog=page.getByRole('dialog',{name:'Gravity HTML5',exact:true});await dialog.waitFor();await dialog.locator('iframe').waitFor();assert(await dialog.evaluate(d=>d.getBoundingClientRect().width<=innerWidth));
  await frame.getByRole('heading',{name:'Gravity Lab',exact:true}).waitFor();await frame.locator('#scene').scrollIntoViewIfNeeded();
  const geometry=await frame.locator('#ball').evaluate(ball=>new Promise(resolve=>requestAnimationFrame(()=>resolve({top:parseFloat(ball.style.top),scene:document.getElementById('scene').clientHeight}))));assert(geometry.top>geometry.scene-100);
  // Phones retain their chosen orientation; unsupported native fullscreen uses the same upright wide canvas.
  await page.evaluate(()=>{window.originalFullscreen=HTMLElement.prototype.requestFullscreen;HTMLElement.prototype.requestFullscreen=()=>Promise.reject(new Error('unsupported fixture'));});
  await dialog.getByRole('button',{name:'Full screen interactive',exact:true}).click();
  await dialog.getByRole('button',{name:'Restore compact interactive',exact:true}).waitFor();
  const landscape=await dialog.locator('iframe').evaluate(f=>({width:f.clientWidth,height:f.clientHeight,sandbox:f.getAttribute('sandbox'),rect:f.getBoundingClientRect().toJSON()}));
  assert(landscape.width>landscape.height,JSON.stringify(landscape));assert.equal(landscape.sandbox,'allow-scripts');
  const stage=dialog.locator('[data-interactive-fullscreen=true]');
  assert.equal(await stage.locator('div').first().evaluate(el=>getComputedStyle(el).transform),'none');
  const restoreBounds=await dialog.getByRole('button',{name:'Restore compact interactive',exact:true}).boundingBox();assert(restoreBounds.x>=0&&restoreBounds.x+restoreBounds.width<=390);
  assert(await dialog.locator('iframe').evaluate(f=>{const view=f.parentElement;view.scrollLeft=200;return view.scrollLeft>0;}));
  await page.screenshot({path:path.resolve(cwd,'../../../work/interactive-fullscreen-mobile.png')});
  await dialog.getByRole('button',{name:'Restore compact interactive',exact:true}).press('Escape');
  assert(await dialog.isVisible());await dialog.getByRole('button',{name:'Full screen interactive',exact:true}).waitFor();
  await page.evaluate(()=>{HTMLElement.prototype.requestFullscreen=window.originalFullscreen;});
  await dialog.getByRole('button',{name:'Full screen interactive',exact:true}).click();
  await page.waitForFunction(()=>!!document.fullscreenElement);
  assert(await dialog.locator('iframe').evaluate(f=>f.clientWidth>f.clientHeight));
  await page.setViewportSize({width:844,height:390});
  await page.waitForFunction(()=>{const f=document.querySelector('[data-interactive-fullscreen=true] iframe');return f&&f.clientWidth===innerWidth;});
  assert.deepEqual(await page.evaluate(()=>window.orientationCalls),[]);
  await dialog.getByRole('button',{name:'Restore compact interactive',exact:true}).click();
  await dialog.getByRole('button',{name:'Full screen interactive',exact:true}).waitFor();
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:path.resolve(cwd,'../../../work/interactive-mobile.png')});await dialog.getByRole('button',{name:'Close resource',exact:true}).press('Escape');await dialog.waitFor({state:'hidden'});
  await explore.getByRole('button',{name:'Open Gravity HTML5',exact:true}).click();dialog=page.getByRole('dialog',{name:'Gravity HTML5',exact:true});await dialog.waitFor();
  await dialog.getByRole('button',{name:'Full screen interactive',exact:true}).click();await page.waitForFunction(()=>!!document.fullscreenElement);
  await dialog.getByRole('button',{name:'Close resource',exact:true}).evaluate(button=>button.click());await dialog.waitFor({state:'hidden'});
  await page.waitForFunction(()=>!document.fullscreenElement&&document.body.style.overflow!=='hidden');assert.equal(await page.locator('iframe').count(),0);
  assert.deepEqual(errors,[]);console.log(JSON.stringify({passed:true,checks:['existing Image preview','existing Video play/pause','HTML5 upload','local sandbox preview','saved admin preview','Explore scoped viewer','gravity simulation','parent/storage isolation','native fullscreen and restore','no orientation API calls','fullscreen state preservation','browser fullscreen exit','upright wide portrait canvas and horizontal scrolling','manual landscape resize','restart','unmount cleanup','mobile','Escape'],uploads,opens}));
 }finally{await browser?.close();server.kill();await new Promise(r=>mock.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
