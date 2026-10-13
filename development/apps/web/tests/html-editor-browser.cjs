const assert=require('node:assert/strict');
const http=require('node:http'),path=require('node:path'),fs=require('node:fs');
const {spawn}=require('node:child_process');
const {chromium}=require(path.resolve(__dirname,'../../../../.kilo/ui-check/node_modules/playwright'));
const cwd=path.resolve(__dirname,'..'),base='http://localhost:3150';
const id=n=>`${String(n).padStart(8,'0')}-1111-4111-8111-111111111111`;
const curriculum={id:id(1),code:'resource-test',name:'Resource fixture',version:2,revision:17,published_revision:17,draft_revision:1,state:'published',levels:[]};
let options=Array.from({length:112},(_,i)=>({topic_id:id(200+i),subtopic_id:i%2?id(400+i):null,subject_id:id(3),curriculum_id:id(1),
 level_id:id(2),domain_id:id(4),category_id:null,available_for_publication:true,level:'Grade 1',subject:'Science',domain:'Motion',category:'',topic:'Gravity '+i,subtopic:i%2?'Lesson '+i:'',label:'Resource fixture / Grade 1 / Science / Motion / Gravity '+i+(i%2?' / Lesson '+i:'')}));
const key=p=>p.topic_id+':'+(p.subtopic_id||'');
let rows=[],uploadTypes=new Map(),uploads=0,creates=0,patches=0,failUpload=true,failAssociation=true,failPublication=true,failPatch=true,loseCreation=false,failDelete=true,failMapConflict=false;
let readDelay=0,activeReviews=0,maxReviews=0,pathsBeforeReview=false,finishedReviews=0;const htmlUploads=new Map();const bodies=[],versions=[],listQueries=[];
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
 if(route==='admin/resources/paths'){if(readDelay&&finishedReviews===0)pathsBeforeReview=true;return json(res,{items:options});}
 if(route==='admin/resources/external-video/inspect'){const input=await body(req);if(input.url.includes('private'))return error(res,'external_video_unavailable','This video is unavailable or private.',422,{field:'external_url'});return json(res,videoInfo(input.url));}
 if(route==='admin/resources/uploads'){const chunks=[];for await(const part of req)chunks.push(part);const data=Buffer.concat(chunks);const isGif=data.includes(Buffer.from('motion.gif')),isVideo=data.includes(Buffer.from('movie.webm'));const isHtml=data.includes(Buffer.from('interactive.html'));const mime=isHtml?'text/html':isGif?'image/gif':isVideo?'video/webm':'image/png';if(isHtml&&data.includes(Buffer.from('INVALID_FIXTURE')))return error(res,'invalid_html','HTML document is invalid.',422,{field:'file'});if(failUpload){failUpload=false;return error(res,'invalid_media_content','Invalid media.',422,{field:'file'});}uploads++;if(isHtml){const text=data.toString();htmlUploads.set(id(700+uploads),text.match(/Content-Type: text\/html\r\n\r\n([\s\S]*?)\r\n--/i)?.[1]||'');}uploadTypes.set(id(700+uploads),mime);return json(res,{upload_id:id(700+uploads),mime_type:mime,byte_size:70},201);}
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
  if(match[2]==='preview'&&saved.type==='interactive'&&!saved.upload_id&&!saved.external_url)return json(res,{url:'',html_document:'',launch_mode:'interactive_pending',media_ready:false});
  if(match[2]==='preview'&&saved.type==='interactive')return json(res,{url:'',html_document:htmlUploads.get(saved.upload_id),launch_mode:'interactive'});
  if(match[2]==='preview')return saved.type==='video'&&saved.external_video?json(res,{launch_mode:'blocked_external_video',external_video:saved.external_video}):json(res,{url:base+'/fixture.'+(saved.mime_type==='image/gif'?'gif':saved.mime_type==='video/webm'?'webm':'png')});
  if(req.method==='GET'){if(readDelay){activeReviews++;maxReviews=Math.max(maxReviews,activeReviews);await new Promise(resolve=>setTimeout(resolve,readDelay));activeReviews--;finishedReviews++;}if(match[2]==='delete-preview')return json(res,{resource:saved,dependencies:{shared_resources:1,activity_kits:1,activity_records:2,conversation_references:1}});return json(res,saved);}
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
 const server=spawn(process.execPath,[path.join(cwd,'node_modules/next/dist/bin/next'),'start','-p','3150'],{cwd,windowsHide:true,env:{...process.env,FLAME_API_URL:`http://127.0.0.1:${mock.address().port}`,FLAME_BFF_SHARED_KEY:'resource-browser-key',FLAME_WEB_ORIGIN:base}});
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
  failUpload=false;failPatch=false;failPublication=false;
  const original='<!doctype html><html><head><style>body{color:navy}</style></head><body><h1>Paste fixture</h1><button onclick="this.textContent=\'Started\'">Start</button></body></html>';
  await panel.getByRole('button',{name:'+ Add resource',exact:true}).click();await panel.getByRole('combobox',{name:'Media type',exact:true}).selectOption('interactive');assert.equal(await panel.getByRole('combobox',{name:'Media source',exact:true}).count(),0);assert.equal(await panel.getByRole('textbox',{name:'Approved HTTPS URL',exact:true}).count(),0);const editor=panel.getByRole('textbox',{name:'HTML5 code',exact:true});
  await panel.getByRole('button',{name:'Save draft',exact:true}).click();await panel.getByRole('alert').filter({hasText:'Paste a non-empty'}).first().waitFor();assert.equal(uploads,0);
  await panel.getByLabel('Upload HTML5 file',{exact:true}).setInputFiles({name:'interactive.html',mimeType:'text/html',buffer:Buffer.from(original)});await page.waitForFunction(value=>document.querySelector('.resource-html-editor textarea')?.value===value,original);assert.equal(uploads,0,'Choosing a file populates code without server upload');
  await panel.getByLabel('Upload HTML5 file',{exact:true}).setInputFiles({name:'invalid.txt',mimeType:'text/plain',buffer:Buffer.from('wrong')});await panel.getByRole('alert').filter({hasText:'Choose one .html'}).waitFor();assert.equal(await editor.inputValue(),original);
  await panel.getByLabel('Upload HTML5 file',{exact:true}).setInputFiles({name:'interactive.html',mimeType:'text/html',buffer:Buffer.from([0xff,0xfe])});await panel.getByRole('alert').filter({hasText:'Use a UTF-8 HTML file'}).waitFor();assert.equal(await editor.inputValue(),original);
  await editor.fill(original);await panel.getByRole('textbox',{name:'Title',exact:true}).fill('Pasted HTML lesson');await panel.getByRole('textbox',{name:'Rights holder',exact:true}).fill('Fixture owner');await panel.getByRole('textbox',{name:'Accessibility note',exact:true}).fill('Use Tab and Enter to start.');await panel.getByRole('tab',{name:'Preview',exact:true}).click();let frame=page.frameLocator('iframe[title="Pasted HTML lesson"]');await frame.getByRole('heading',{name:'Paste fixture',exact:true}).waitFor();await frame.getByRole('button',{name:'Start',exact:true}).click();await frame.getByRole('button',{name:'Started',exact:true}).waitFor();await panel.getByRole('tab',{name:'Preview',exact:true}).press('ArrowLeft');assert.equal(await editor.inputValue(),original);assert.equal(await panel.locator('iframe').count(),0);
  await panel.getByRole('button',{name:'Save draft',exact:true}).dblclick();await panel.getByText('Resource added successfully',{exact:true}).waitFor();assert.equal(uploads,1);assert.equal(rows.length,1);assert.equal(rows[0].mime_type,'text/html');assert.equal(htmlUploads.get(rows[0].upload_id),original);
  const row=panel.locator('tbody tr').first();async function edit(){await row.getByRole('button',{name:'Actions for Pasted HTML lesson',exact:true}).click();await page.getByRole('menuitem',{name:'Edit',exact:true}).click();await editor.waitFor();await page.waitForFunction(text=>document.querySelector('.resource-html-editor textarea')?.value===text,htmlUploads.get(rows[0].upload_id));}
  await edit();await panel.getByRole('textbox',{name:'Description',exact:true}).fill('Metadata only');await panel.getByRole('button',{name:'Save draft',exact:true}).click();await panel.getByText('Resource changes saved',{exact:true}).waitFor();assert.equal(uploads,1,'Metadata edit retains HTML');
  await edit();const updated=original.replace('Paste fixture','Updated fixture');await editor.fill(updated);failPatch=true;await panel.getByRole('button',{name:'Save draft',exact:true}).click();await panel.getByRole('alert').filter({hasText:'Resource changed elsewhere'}).waitFor();assert.equal(await editor.inputValue(),updated);assert.equal(uploads,2);await panel.getByRole('button',{name:'Review latest version',exact:true}).click();await panel.getByText(/Latest version loaded/).waitFor();assert.equal(await editor.inputValue(),updated,'Latest preview does not overwrite edits');await panel.getByRole('button',{name:'Save draft',exact:true}).click();await panel.getByText('Resource changes saved',{exact:true}).waitFor();assert.equal(uploads,2,'Retry reuses uploaded HTML');assert.equal(htmlUploads.get(rows[0].upload_id),updated);
  await edit();await editor.fill('INVALID_FIXTURE');await panel.getByRole('button',{name:'Save draft',exact:true}).click();await panel.getByRole('alert').filter({hasText:'HTML document is invalid'}).first().waitFor();assert.equal(await editor.inputValue(),'INVALID_FIXTURE');await editor.fill('x'.repeat(2*1024*1024+1));await panel.getByRole('button',{name:'Save draft',exact:true}).click();await panel.getByRole('alert').filter({hasText:'up to 2 MiB'}).first().waitFor();assert.equal(uploads,2);page.once('dialog',dialog=>dialog.accept());await panel.getByRole('button',{name:'Cancel',exact:true}).click();
  await row.getByRole('button',{name:'Actions for Pasted HTML lesson',exact:true}).click();await page.getByRole('menuitem',{name:'Publish',exact:true}).click();await row.getByText('Published',{exact:true}).waitFor();await edit();assert(await editor.isDisabled(),'Published source cannot be edited');page.once('dialog',dialog=>dialog.accept());await panel.getByRole('button',{name:'Unpublish to edit as draft',exact:true}).click();await panel.getByText('Resource unpublished successfully.',{exact:true}).waitFor();assert(await editor.isEnabled());await page.setViewportSize({width:390,height:800});assert(await panel.locator('.resource-html-editor').evaluate(e=>e.scrollWidth<=e.clientWidth));await page.screenshot({path:path.resolve(cwd,'../../../work/html-source-editor.png'),fullPage:true});assert.deepEqual(errors,[]);
  await page.setViewportSize({width:1440,height:900});await panel.getByRole('button',{name:'Back to library',exact:true}).click();rows.push({...rows[0],id:id(977),title:'Pending code fixture',source:'pending',upload_id:null,external_url:null,mime_type:null,published:false,version:1});await panel.getByRole('searchbox',{name:'Search resources',exact:true}).fill('Pending code');const pendingRow=panel.locator('tbody tr').filter({hasText:'Pending code fixture'});await pendingRow.getByText('HTML pending',{exact:true}).waitFor();await pendingRow.getByRole('button',{name:'Actions for Pending code fixture',exact:true}).click();await page.getByRole('menuitem',{name:'Edit',exact:true}).click();await panel.getByRole('textbox',{name:'HTML5 code',exact:true}).waitFor();await panel.getByText('Paste or upload HTML5 before previewing or publishing.',{exact:true}).waitFor();assert(await panel.getByRole('button',{name:'Publish',exact:true}).isDisabled());await page.waitForFunction(()=>!document.querySelector('.resource-html-editor textarea')?.disabled);assert.equal(await panel.getByRole('textbox',{name:'HTML5 code',exact:true}).inputValue(),'');await panel.getByRole('textbox',{name:'HTML5 code',exact:true}).fill(original);await panel.getByRole('button',{name:'Save draft',exact:true}).click();await pendingRow.getByText('HTML5',{exact:true}).waitFor();assert.equal(rows.find(r=>r.id===id(977)).mime_type,'text/html');assert.deepEqual(errors,[]);
  console.log('PASS: pending Interactive row opens empty HTML editor, blocks publication, and accepts HTML later.');
  console.log('PASS: pasted HTML creation and sandbox preview, duplicate guard, saved source loading, metadata-only retention, code replacement, conflict review without losing edits, upload reuse, invalid/oversize preservation, publication protection and narrow layout.');
 }catch(error){if(page){await page.screenshot({path:path.resolve(cwd,'../../../work/html-editor-failure.png'),fullPage:true});}throw error;}
 finally{await browser?.close();server.kill();mock.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
