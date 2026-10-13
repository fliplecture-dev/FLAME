const assert=require('node:assert/strict');
const http=require('node:http'),path=require('node:path'),fs=require('node:fs');
const {spawn}=require('node:child_process');
const {chromium}=require(path.resolve(__dirname,'../../../../.kilo/ui-check/node_modules/playwright'));
const cwd=path.resolve(__dirname,'..'),base='http://localhost:3117';
const id=n=>`${String(n).padStart(8,'0')}-1111-4111-8111-111111111111`;
const curriculum={id:id(1),code:'resource-test',name:'Resource fixture',version:2,revision:17,published_revision:17,draft_revision:1,state:'published',levels:[]};
let options=Array.from({length:112},(_,i)=>({topic_id:id(200+i),subtopic_id:i%2?id(400+i):null,subject_id:id(3),curriculum_id:id(1),
 level_id:id(2),domain_id:id(4),category_id:null,available_for_publication:true,level:'Grade 1',subject:'Science',domain:'Motion',category:'',topic:'Gravity '+i,subtopic:i%2?'Lesson '+i:'',label:'Resource fixture / Grade 1 / Science / Motion / Gravity '+i+(i%2?' / Lesson '+i:'')}));
const key=p=>p.topic_id+':'+(p.subtopic_id||'');
let rows=[],uploadTypes=new Map(),uploads=0,creates=0,patches=0,failUpload=true,failAssociation=true,failPublication=true,failPatch=true,loseCreation=false,failDelete=true,failMapConflict=false;
const bodies=[],versions=[],listQueries=[];
const json=(res,data,status=200)=>{res.writeHead(status,{'content-type':'application/json'});res.end(JSON.stringify(data));};
const body=async req=>{const parts=[];for await(const part of req)parts.push(part);return JSON.parse(Buffer.concat(parts).toString()||'{}');};
const error=(res,code,message,status=422,extra={})=>json(res,{request_id:'resource-test-reference',error:{code,message,...extra}},status);
const details=paths=>paths.map(p=>({...options.find(o=>key(o)===key(p)),...p,valid:true}));
const videoInfo=url=>({provider:url.includes('vimeo')?'vimeo':'youtube',provider_name:url.includes('vimeo')?'Vimeo':'YouTube',video_id:url.includes('vimeo')?'76979871':'M7lc1UVf-VE',canonical_url:url,title:'External gravity lesson',description:'Gravity explanation',thumbnail_url:null,verification:'public_embeddable',student_playback_allowed:false,playback_reason:'Student playback is blocked: this provider has not been approved for navigation-free playback in FLAME. Use a licensed uploaded video instead.'});
const mock=http.createServer(async(req,res)=>{
 const url=new URL(req.url,'http://test'),route=url.pathname.replace('/api/v1/','');
 if(route==='me')return json(res,{id:id(99),role:'admin',email:'resource@example.test'});
 if(route==='admin/curricula')return json(res,{items:[curriculum]});
 if(route.endsWith('/tree'))return json(res,curriculum);
 if(route.endsWith('/revisions'))return json(res,{items:[]});
 if(route==='admin/curriculum/imports')return json(res,{items:[]});
 if(route==='admin/resources/paths')return json(res,{items:options});
 if(route==='admin/resources/external-video/inspect'){const input=await body(req);if(input.url.includes('private'))return error(res,'external_video_unavailable','This video is unavailable or private.',422,{field:'external_url'});return json(res,videoInfo(input.url));}
 if(route==='admin/resources/uploads'){const chunks=[];for await(const part of req)chunks.push(part);const data=Buffer.concat(chunks);const isGif=data.includes(Buffer.from('motion.gif')),isVideo=data.includes(Buffer.from('movie.webm'));const mime=isGif?'image/gif':isVideo?'video/webm':'image/png';if(failUpload){failUpload=false;return error(res,'invalid_media_content','Invalid media.',422,{field:'file'});}uploads++;uploadTypes.set(id(700+uploads),mime);return json(res,{upload_id:id(700+uploads),mime_type:mime,byte_size:70},201);}
 if(route==='admin/resources'){
  if(req.method==='GET'){
   listQueries.push(Object.fromEntries(url.searchParams));
   let matches=rows.filter(r=>(!url.searchParams.get('q')||r.title.toLowerCase().includes(url.searchParams.get('q').toLowerCase()))&&(!url.searchParams.get('type')||r.type===url.searchParams.get('type'))&&(!url.searchParams.get('published')||String(r.published)===url.searchParams.get('published')));
   if(url.searchParams.get('sort')==='title')matches.sort((a,b)=>a.title.localeCompare(b.title));
   const offset=Number(url.searchParams.get('offset')||0),limit=Number(url.searchParams.get('limit')||30);
   return json(res,{items:matches.slice(offset,offset+limit),total:matches.length});
  }
  const input=await body(req);creates++;bodies.push(input);await new Promise(r=>setTimeout(r,180));
  if(rows.some(r=>r.id===input.creation_id))return error(res,'resource_creation_exists','Creation already completed.',409);
  const saved={...input,id:input.creation_id,source:input.external_url?'external':'upload',external_url:input.external_url??null,external_video:input.type==='video'&&input.external_url?videoInfo(input.external_url):null,version:1,published:false,path_details:details(input.paths??[]),mime_type:uploadTypes.get(input.upload_id),byte_size:70,file_name:'motion.gif',updated_at:new Date().toISOString()};rows.push(saved);
  if(loseCreation){loseCreation=false,failDelete=true,failMapConflict=false;return error(res,'upstream_timeout','The API response timed out.',504);}
  return json(res,saved,201);
 }
 const match=route.match(/^admin\/resources\/([0-9a-f-]+)(?:\/(publish|unpublish|preview|delete-preview|delete))?$/);
 if(match){
  const saved=rows.find(r=>r.id===match[1]);if(!saved)return error(res,'resource_not_found','Resource not found.',404);
  if(match[2]==='preview')return saved.type==='video'&&saved.external_video?json(res,{launch_mode:'blocked_external_video',external_video:saved.external_video}):json(res,{url:base+'/fixture.'+(saved.mime_type==='image/gif'?'gif':saved.mime_type==='video/webm'?'webm':'png')});
  if(req.method==='GET'){if(match[2]==='delete-preview')return json(res,{resource:saved,dependencies:{shared_resources:1,activity_kits:1,activity_records:2,conversation_references:1}});return json(res,saved);}
  const input=await body(req);versions.push(input.expected_version);
  if(match[2]==='publish'){
   assert.equal(input.expected_version,saved.version);
   if(failPublication){failPublication=false;return error(res,'published_path_required','Select an available published curriculum path.',422,{field:'paths'});}
   saved.version++;saved.published=true;return json(res,saved);
  }
  if(match[2]==='unpublish'){assert.equal(input.expected_version,saved.version);saved.version++;saved.published=false;return json(res,saved);}
  if(match[2]==='delete-preview')return json(res,{resource:saved,dependencies:{shared_resources:1,activity_kits:1,activity_records:2,conversation_references:1}});
  if(match[2]==='delete'){
   assert.equal(input.confirm_resource_id,saved.id);
   if(failDelete){failDelete=false;saved.version++;return error(res,'stale_version','Resource changed elsewhere.',409);}
   assert.equal(input.expected_version,saved.version);rows=rows.filter(r=>r.id!==saved.id);return json(res,{status:'deleted',id:saved.id,media_retained:true});
  }
  patches++;
  if(Object.hasOwn(input,'paths')){
   if(failAssociation){failAssociation=false;const invalid=input.paths.find(p=>p.topic_id===id(310));options=options.filter(o=>o.topic_id!==id(310));return error(res,'resource_paths_unavailable','Selected path was removed. Review current paths and remove that selection.',422,{field:'paths',invalid_paths:[invalid]});}
   if(failMapConflict){failMapConflict=false;saved.version++;return error(res,'stale_version','Resource changed elsewhere.',409);}
   assert.equal(input.expected_version,saved.version);saved.paths=input.paths;saved.path_details=details(input.paths);saved.version++;return json(res,saved);
  }
  if(failPatch){failPatch=false;saved.version++;return error(res,'stale_version','Resource changed elsewhere.',409);}
  assert.equal(input.expected_version,saved.version);Object.assign(saved,input,{version:saved.version+1,path_details:details(input.paths??saved.paths),mime_type:input.upload_id?uploadTypes.get(input.upload_id):saved.mime_type,...(input.type==='video'&&input.external_url&&input.external_url?{external_video:videoInfo(input.external_url)}:{})});return json(res,saved);
 }
 return json(res,{},404);
});
(async()=>{
 await new Promise(resolve=>mock.listen(0,'127.0.0.1',resolve));
 const server=spawn(process.execPath,[path.join(cwd,'node_modules/next/dist/bin/next'),'start','-p','3117'],{cwd,windowsHide:true,env:{...process.env,FLAME_API_URL:`http://127.0.0.1:${mock.address().port}`,FLAME_BFF_SHARED_KEY:'resource-browser-key',FLAME_WEB_ORIGIN:base}});
 let browser,page;
 try{
  for(let i=0;i<50;i++){try{if((await fetch(base+'/sign-in')).ok)break;}catch{}await new Promise(r=>setTimeout(r,300));}
  browser=await chromium.launch({channel:'msedge',headless:true});const context=await browser.newContext({viewport:{width:1440,height:900},reducedMotion:'reduce'});
  await context.addCookies([{name:'flame_session',value:'resource-fixture-session',url:base,httpOnly:true}]);page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const gif=fs.readFileSync(path.join(__dirname,'fixtures/force-motion.gif'));await page.route('**/fixture.gif',r=>r.fulfill({contentType:'image/gif',body:gif}));
  await page.route('https://www.youtube.com/iframe_api',route=>route.fulfill({contentType:'application/javascript',body:`window.YT={Player:function(frame,config){this.playVideo=()=>config.events.onStateChange({data:1});this.pauseVideo=()=>{};window.fixtureVideoError=()=>config.events.onError({data:101});setTimeout(()=>config.events.onReady(),0);}};window.onYouTubeIframeAPIReady?.();`}));
  await page.route('https://player.vimeo.com/api/player.js',route=>route.fulfill({contentType:'application/javascript',body:`window.Vimeo={Player:function(){const events={};this.on=(event,fn)=>events[event]=fn;this.ready=()=>Promise.resolve();this.play=()=>{events.play?.();return Promise.resolve();};this.pause=()=>Promise.resolve();window.fixtureVideoError=()=>events.error?.();}};`}));
  await page.route(/https:\/\/(www\.youtube\.com\/embed|player\.vimeo\.com\/video)\//,route=>route.fulfill({contentType:'text/html',body:'<!doctype html><html><body><p>Isolated provider player fixture</p></body></html>'}));
  await page.goto(base+'/admin',{waitUntil:'networkidle'});await page.getByRole('button',{name:'Resource Library',exact:true}).click();const panel=page.locator('.b9-resource-panel');
  await panel.getByRole('button',{name:'+ Add resource',exact:true}).click();
  assert.equal(await panel.locator('.b9-resource-paths').count(),0);assert.equal(await panel.getByRole('combobox',{name:'Library Topic',exact:true}).count(),0);
  await panel.getByRole('textbox',{name:'Concepts (comma separated)',exact:true}).fill('force, push, pull');await panel.getByRole('textbox',{name:'Alternative terms (comma separated)',exact:true}).fill('pushes and pulls');await panel.getByRole('combobox',{name:'From grade',exact:true}).selectOption('1');await panel.getByRole('combobox',{name:'Through grade',exact:true}).selectOption('3');await panel.getByRole('checkbox',{name:'Explain concepts',exact:true}).check();
  await panel.getByRole('textbox',{name:'Title',exact:true}).fill('Isolated force animation');await panel.getByRole('textbox',{name:'Rights holder',exact:true}).fill('Test owner');await panel.getByRole('textbox',{name:'Image description',exact:true}).fill('A force arrow pushes a box.');
  await panel.getByLabel('File',{exact:true}).setInputFiles({name:'motion.gif',mimeType:'image/gif',buffer:gif});
  await panel.locator('.animated-media').getByRole('button',{name:'Play animation',exact:true}).click();await panel.locator('.animated-media').getByRole('button',{name:'Pause animation',exact:true}).click();
  await panel.getByRole('button',{name:'Save draft',exact:true}).click();await panel.getByRole('alert').filter({hasText:'Upload failed.'}).first().waitFor();assert.equal(uploads,0);
  await panel.getByRole('button',{name:'Save draft',exact:true}).dblclick();await panel.getByText('Resource added successfully',{exact:true}).waitFor();assert.equal(creates,1);assert.equal(uploads,1);assert.deepEqual(bodies[0].paths,[]);
  const row=panel.locator('tbody tr').filter({hasText:'Isolated force animation'});await row.waitFor();await row.getByText('Not mapped',{exact:true}).waitFor();
  const actions=()=>row.getByRole('button',{name:'Actions for Isolated force animation',exact:true});
  failPublication=false;await actions().click();await page.getByRole('menuitem',{name:'Publish',exact:true}).click();await panel.getByText('Resource published successfully.',{exact:true}).waitFor();assert(rows[0].published&&rows[0].paths.length===0);
  await row.getByRole('button',{name:'Map topics',exact:true}).click();let mapping=page.getByRole('dialog',{name:'Map topics for Isolated force animation',exact:true});await mapping.waitFor();
  await mapping.getByText(/Saved mapping changes update learner availability immediately/).waitFor();
  let picker=mapping.locator('.b9-resource-paths');await picker.locator('.b9-path-options input').first().check();await picker.locator('.b9-path-options input').nth(1).check();
  await mapping.getByRole('searchbox',{name:'Search topics and subtopics',exact:true}).fill('Gravity 110');await picker.locator('.b9-path-options input').first().check();
  await mapping.getByRole('button',{name:'Clear mapping filters',exact:true}).click();await mapping.getByRole('button',{name:'Next paths',exact:true}).click();await picker.locator('.b9-path-options input').first().check();assert.equal(await picker.locator('.b9-selected-paths > div').count(),4);
  await mapping.getByRole('button',{name:'Save mappings',exact:true}).dblclick();await mapping.getByRole('alert').filter({hasText:'Mappings were not saved'}).waitFor();assert.equal(rows[0].paths.length,0);assert(rows[0].published);assert.equal(await picker.locator('.b9-selected-paths > div').count(),4);
  await mapping.getByRole('button',{name:'Review latest mappings',exact:true}).click();await mapping.getByText(/Latest saved mappings loaded below/).waitFor();
  await mapping.getByRole('button',{name:'Remove Resource fixture / Grade 1 / Science / Motion / Gravity 110',exact:true}).click();
  await mapping.getByRole('button',{name:'Save mappings',exact:true}).click();await mapping.waitFor({state:'hidden'});await panel.getByText('Resource mappings updated successfully.',{exact:true}).waitFor();assert.equal(rows[0].paths.length,3);assert(rows[0].published);assert.equal(uploads,1);
  await row.getByRole('button',{name:'Manage mappings',exact:true}).click();mapping=page.getByRole('dialog',{name:'Map topics for Isolated force animation',exact:true});picker=mapping.locator('.b9-resource-paths');await picker.locator('.b9-selected-paths > div').nth(2).waitFor();assert.equal(await picker.locator('.b9-selected-paths > div').count(),3);
  await mapping.getByRole('combobox',{name:'Library Curriculum',exact:true}).fill('Resource fixture');await mapping.getByRole('combobox',{name:'Library Level',exact:true}).fill('Grade 1');await mapping.getByRole('combobox',{name:'Library Subject',exact:true}).fill('Science');await mapping.getByRole('combobox',{name:'Library Topic',exact:true}).fill('Gravity 3');
  await picker.locator('.b9-path-options input').first().check();failMapConflict=true;
  await mapping.getByRole('button',{name:'Save mappings',exact:true}).click();await mapping.getByRole('alert').filter({hasText:'Resource changed elsewhere'}).waitFor();assert.equal(await picker.locator('.b9-selected-paths > div').count(),4);assert(await mapping.getByRole('button',{name:'Save mappings',exact:true}).isDisabled());
  await mapping.getByRole('button',{name:'Review latest mappings',exact:true}).click();await mapping.getByText(/Latest saved mappings loaded below/).waitFor();
  page.once('dialog',d=>d.accept());await mapping.getByRole('button',{name:'Cancel',exact:true}).click();assert.equal(rows[0].paths.length,3);
  await row.getByRole('button',{name:'Manage mappings',exact:true}).click();mapping=page.getByRole('dialog',{name:'Map topics for Isolated force animation',exact:true});picker=mapping.locator('.b9-resource-paths');await picker.locator('.b9-selected-paths > div').nth(2).waitFor();
  for(let i=0;i<3;i++)await picker.locator('.b9-selected-paths > div').first().getByRole('button',{name:/Remove/}).click();
  await mapping.getByRole('button',{name:'Save mappings',exact:true}).click();await mapping.waitFor({state:'hidden'});await panel.getByText('Resource mappings updated successfully.',{exact:true}).waitFor();assert(rows[0].published&&rows[0].paths.length===0);await row.getByText('Not mapped',{exact:true}).waitFor();
  // Media editing remains independent: no mapping payload, existing media retained.
  await actions().click();await page.getByRole('menuitem',{name:'Edit',exact:true}).click();assert.equal(await panel.locator('.b9-resource-paths').count(),0);
  assert.deepEqual(rows[0].learning_metadata.concepts,['force','push','pull']);assert.equal(await panel.getByRole('textbox',{name:'Concepts (comma separated)',exact:true}).inputValue(),'force, push, pull');await page.screenshot({path:path.resolve(cwd,'../../../work/recommendation-metadata-editor.png'),fullPage:true});await page.setViewportSize({width:390,height:800});assert(await panel.locator('.recommendation-metadata').evaluate(e=>e.scrollWidth<=e.clientWidth),'Metadata editor fits narrow viewport');await page.screenshot({path:path.resolve(cwd,'../../../work/recommendation-metadata-editor-narrow.png'),fullPage:true});await page.setViewportSize({width:1440,height:900});
  page.once('dialog',d=>d.accept());await panel.getByRole('button',{name:'Unpublish to edit as draft',exact:true}).click();await panel.getByText('Resource unpublished successfully.',{exact:true}).waitFor();
  await panel.getByRole('textbox',{name:'Description',exact:true}).fill('Metadata only');await panel.getByRole('button',{name:'Save draft',exact:true}).click();await panel.getByRole('alert').filter({hasText:'Resource changed elsewhere'}).first().waitFor();
  await panel.getByRole('button',{name:'Review latest version',exact:true}).click();await panel.getByText(/Latest version loaded/).waitFor();await panel.getByRole('button',{name:'Save draft',exact:true}).click();await panel.getByText('Resource changes saved',{exact:true}).waitFor();assert.equal(uploads,1);
  await actions().click();await page.getByRole('menuitem',{name:'Delete',exact:true}).click();let deletion=page.getByRole('dialog',{name:'Delete Isolated force animation',exact:true});await deletion.getByText(/Their files remain intact/).waitFor();assert(await deletion.getByRole('button',{name:'Delete resource',exact:true}).isDisabled());await deletion.getByRole('button',{name:'Cancel',exact:true}).click();assert.equal(rows.length,1);
  await actions().click();await page.getByRole('menuitem',{name:'Delete',exact:true}).click();deletion=page.getByRole('dialog',{name:'Delete Isolated force animation',exact:true});await deletion.getByRole('checkbox',{name:/I confirm deletion/}).check();
  await deletion.getByRole('button',{name:'Delete resource',exact:true}).click();await deletion.getByRole('alert').filter({hasText:'Resource changed elsewhere'}).waitFor();assert.equal(rows.length,1);
  await deletion.getByRole('button',{name:'Review deletion again',exact:true}).click();await deletion.getByRole('checkbox',{name:/I confirm deletion/}).check();await deletion.getByRole('button',{name:'Delete resource',exact:true}).click();await deletion.waitFor({state:'hidden'});await row.waitFor({state:'hidden'});await panel.getByText('Resource deleted successfully.',{exact:true}).waitFor();assert.equal(rows.length,0);assert.equal(await panel.locator('tbody tr').count(),0);
  await page.screenshot({path:path.resolve(cwd,'../../../work/resource-media-mapping-deletion.png'),fullPage:true});
  await panel.getByRole('button',{name:'+ Add resource',exact:true}).click();await panel.getByRole('textbox',{name:'Title',exact:true}).fill('Lost response animation');await panel.getByRole('textbox',{name:'Rights holder',exact:true}).fill('Test owner');await panel.getByRole('textbox',{name:'Image description',exact:true}).fill('A force arrow');await panel.getByLabel('File',{exact:true}).setInputFiles({name:'motion.gif',mimeType:'image/gif',buffer:gif});loseCreation=true;
  await panel.getByRole('button',{name:'Save draft',exact:true}).click();await panel.getByRole('alert').filter({hasText:'could not be confirmed'}).first().waitFor();await panel.getByRole('button',{name:'Save draft',exact:true}).click();await panel.getByText('Resource added successfully',{exact:true}).waitFor();assert.equal(rows.length,1);assert.equal(uploads,2);
  const last=panel.locator('tbody tr').first();await last.getByRole('button',{name:'Map topics',exact:true}).click();mapping=page.getByRole('dialog',{name:'Map topics for Lost response animation',exact:true});await mapping.locator('.b9-path-options input').first().waitFor();
  await page.setViewportSize({width:390,height:800});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert(await mapping.evaluate(e=>e.scrollWidth<=e.clientWidth),'Mapping dialog has no horizontal overflow');
  await page.screenshot({path:path.resolve(cwd,'../../../work/resource-mapping-dialog-narrow.png'),fullPage:true});await mapping.getByRole('button',{name:'Cancel',exact:true}).click();assert.deepEqual(errors,[]);
  // External videos use URL-only creation, retained mapping/actions and a metadata-only preview.
  await page.setViewportSize({width:1440,height:900});let popups=0;page.on('popup',()=>popups++);const beforeExternalUploads=uploads;
  await panel.getByRole('button',{name:'+ Add resource',exact:true}).click();await panel.getByRole('combobox',{name:'Media type',exact:true}).selectOption('video');await panel.getByRole('combobox',{name:'Media source',exact:true}).selectOption('external');
  assert.equal(await panel.getByLabel('File',{exact:true}).count(),0);await panel.getByRole('textbox',{name:'Video URL',exact:true}).fill('https://vimeo.com/private');
  await panel.getByRole('button',{name:'Validate video URL',exact:true}).click();await panel.getByRole('alert').filter({hasText:'private'}).first().waitFor();assert.equal(await panel.getByRole('textbox',{name:'Video URL',exact:true}).inputValue(),'https://vimeo.com/private');
  await panel.getByRole('textbox',{name:'Video URL',exact:true}).fill('https://youtu.be/M7lc1UVf-VE');await panel.getByRole('button',{name:'Validate video URL',exact:true}).click();await panel.getByText('Source: YouTube',{exact:true}).waitFor();
  await panel.locator('.external-video-summary').screenshot({path:path.resolve(cwd,'../../../work/admin-compact-video-preview.png')});assert.equal(await panel.getByRole('textbox',{name:'Title',exact:true}).inputValue(),'External gravity lesson');await panel.getByRole('textbox',{name:'Rights holder',exact:true}).fill('Licensed teacher');await panel.getByRole('textbox',{name:'Caption or transcript (optional for GIF)',exact:true}).fill('Gravity pulls objects toward Earth.');
  await panel.getByRole('button',{name:'Save draft',exact:true}).click();await panel.getByRole('heading',{name:'Resource Library',exact:true}).waitFor();const externalRow=panel.locator('tbody tr').filter({hasText:'External gravity lesson'});await externalRow.waitFor();await externalRow.getByText('Video',{exact:true}).waitFor();await externalRow.getByText('Source: YouTube',{exact:true}).waitFor();assert.equal(uploads,beforeExternalUploads);
  await externalRow.getByRole('button',{name:'Preview',exact:true}).click();let previewDialog=page.getByRole('dialog',{name:'Preview External gravity lesson',exact:true});await previewDialog.getByText('Source: YouTube',{exact:true}).waitFor();assert.equal(await previewDialog.locator('iframe').count(),1);assert.equal(await previewDialog.locator('a,video').count(),0);await previewDialog.getByRole('button',{name:'Play video',exact:true}).click();await previewDialog.getByRole('button',{name:'Pause video',exact:true}).click();await previewDialog.getByRole('button',{name:'Close preview',exact:true}).click();
  await externalRow.getByRole('button',{name:'Actions for External gravity lesson',exact:true}).click();await page.getByRole('menuitem',{name:'Publish',exact:true}).click();await externalRow.getByText('Published',{exact:true}).waitFor();
  await externalRow.getByRole('button',{name:'Map topics',exact:true}).click();let em=page.getByRole('dialog',{name:'Map topics for External gravity lesson',exact:true});await em.locator('.b9-path-options input').nth(1).check();await em.getByRole('button',{name:'Save mappings',exact:true}).click();await em.waitFor({state:'hidden'});assert(rows.find(r=>r.type==='video'&&r.external_video).published);
  await externalRow.getByRole('button',{name:'Actions for External gravity lesson',exact:true}).click();await page.getByRole('menuitem',{name:'Edit',exact:true}).click();page.once('dialog',d=>d.accept());await panel.getByRole('button',{name:'Unpublish to edit as draft',exact:true}).click();await panel.getByText('Resource unpublished successfully.',{exact:true}).waitFor();
  await panel.getByRole('textbox',{name:'Video URL',exact:true}).fill('https://vimeo.com/76979871');await panel.getByRole('button',{name:'Validate video URL',exact:true}).click();await panel.getByText('Source: Vimeo',{exact:true}).waitFor();await panel.getByRole('button',{name:'Save draft',exact:true}).click();await externalRow.getByText('Source: Vimeo',{exact:true}).waitFor();
  await externalRow.getByRole('button',{name:'Preview',exact:true}).click();previewDialog=page.getByRole('dialog',{name:'Preview External gravity lesson',exact:true});await previewDialog.getByText('Source: Vimeo',{exact:true}).waitFor();assert.equal(await previewDialog.locator('iframe').count(),1);assert.equal(await previewDialog.locator('a,video').count(),0);await previewDialog.getByRole('button',{name:'Play video',exact:true}).click();await previewDialog.getByRole('button',{name:'Pause video',exact:true}).click();await page.keyboard.press('Escape');await previewDialog.waitFor({state:'hidden'});
  assert.equal(popups,0);assert.equal(page.url(),base+'/admin');await page.setViewportSize({width:390,height:740});await externalRow.getByRole('button',{name:'Manage mappings',exact:true}).click();em=page.getByRole('dialog',{name:'Map topics for External gravity lesson',exact:true});await em.getByText('Source: Vimeo',{exact:true}).waitFor();assert(await em.evaluate(d=>d.scrollWidth<=d.clientWidth+1));await page.screenshot({path:path.resolve(cwd,'../../../work/external-video-mobile.png'),fullPage:true});await em.getByRole('button',{name:'Cancel',exact:true}).click();
  // The approved alternative uses an actual locally generated WebM, with no provider links.
  await page.setViewportSize({width:1440,height:900});const movie=await page.evaluate(async()=>{const canvas=document.createElement('canvas');canvas.width=240;canvas.height=135;canvas.style.cssText='position:fixed;top:0;left:0;opacity:.01;pointer-events:none';document.body.appendChild(canvas);const context=canvas.getContext('2d');context.fillStyle='#336699';context.fillRect(0,0,240,135);const stream=canvas.captureStream(10);const recorder=new MediaRecorder(stream,{mimeType:'video/webm;codecs=vp8'});const chunks=[];recorder.ondataavailable=e=>chunks.push(e.data);const done=new Promise(resolve=>recorder.onstop=resolve);recorder.start();context.fillStyle='white';context.fillRect(10,10,30,30);const timer=setInterval(()=>{context.fillStyle='#336699';context.fillRect(0,0,240,135);context.fillStyle='white';context.fillText('Licensed fixture '+Date.now(),10,50);},50);await new Promise(r=>setTimeout(r,800));recorder.stop();await done;clearInterval(timer);stream.getTracks().forEach(t=>t.stop());canvas.remove();return Array.from(new Uint8Array(await new Blob(chunks).arrayBuffer()));});
  await page.route('**/fixture.webm',route=>route.fulfill({contentType:'video/webm',body:Buffer.from(movie)}));await panel.getByRole('button',{name:'+ Add resource',exact:true}).click();await panel.getByRole('textbox',{name:'Title',exact:true}).fill('Licensed uploaded lesson');await panel.getByLabel('File',{exact:true}).setInputFiles({name:'movie.webm',mimeType:'video/webm;codecs=vp8',buffer:Buffer.from(movie)});await panel.getByRole('button',{name:'Save draft',exact:true}).click();
  const videoRow=panel.locator('tbody tr').filter({hasText:'Licensed uploaded lesson'});await videoRow.getByRole('button',{name:'Preview',exact:true}).click();previewDialog=page.getByRole('dialog',{name:'Preview Licensed uploaded lesson',exact:true});await previewDialog.waitFor();await previewDialog.locator('video').evaluate(v=>v.loop=true);await previewDialog.getByRole('button',{name:'Play video',exact:true}).click();await previewDialog.getByRole('button',{name:'Pause video',exact:true}).waitFor();await previewDialog.getByRole('button',{name:'Pause video',exact:true}).click();await previewDialog.getByRole('button',{name:'Enter fullscreen',exact:true}).click();await previewDialog.getByRole('button',{name:'Exit fullscreen',exact:true}).click();assert.equal(await previewDialog.locator('a,iframe').count(),0);assert.equal(await previewDialog.locator('video').getAttribute('controls'),null);await previewDialog.getByRole('button',{name:'Close preview',exact:true}).click();assert.equal(popups,0);assert.equal(page.url(),base+'/admin');assert.deepEqual(errors,[]);
  console.log('PASS: media-only creation and mapping/deletion regressions; External video URL-only form, validation error preservation, YouTube/Vimeo metadata save/edit/preview, published mapping, standard in-app iframe playback without API keys, mobile dialog, and actual licensed WebM play/pause/fullscreen/exit/close.');
 }catch(error){if(page){await page.screenshot({path:path.resolve(cwd,'../../../work/resource-mapping-deletion-failure.png'),fullPage:true});fs.writeFileSync(path.resolve(cwd,'../../../work/resource-mapping-deletion-failure.html'),await page.content());}throw error;}
 finally{await browser?.close();server.kill();mock.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});





