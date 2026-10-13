const assert = require('node:assert/strict');
const http = require('node:http');
const path = require('node:path');
const fs = require('node:fs');
const { spawn } = require('node:child_process');
const { chromium } = require(path.resolve(__dirname, '../../../../.kilo/ui-check/node_modules/playwright'));
const cwd = path.resolve(__dirname, '..');
const base = 'http://localhost:3116';
const uid = n => `${String(n).padStart(8, '0')}-1111-4111-8111-111111111111`;
const ids = { c: uid(1), l: uid(2), s: uid(3), d: uid(4), t: uid(5), st: uid(6) };
const tree = { id: ids.c, name: 'Sidebar curriculum', revision: 1, levels: [{ id: ids.l, name: 'Grade 1', subjects: [{ id: ids.s, name: 'Science', domains: [{ id: ids.d, name: 'Motion', categories: [], topics: [{ id: ids.t, name: 'Gravity', subtopics: [{ id: ids.st, name: 'Falling objects' }] }] }] }] }] };
const contextPath = { curriculum_id: ids.c, level_id: ids.l, subject_id: ids.s, domain_id: ids.d, category_id: null, topic_id: ids.t, subtopic_id: ids.st, names: { topic: 'Gravity', subtopic: 'Falling objects' } };
const now = new Date().toISOString();
const rows = [{ id: uid(10), mode: 'study', context: contextPath, revision: 1, pinned: false, first_question: 'Explain force', created_at: now, updated_at: now, recent_at: now }];
let opens = 0;
let includeVideo=false;
let structured=false, unavailableKit=false, failedRecommendations=false;
const seenRecommendations=new Set();
const practiceKit={id:uid(70),version:2,name:'Gravity practice kit',description:'Practise falling objects.',materials:['Ball'],instructions:'Observe the ball falling.',supervision:'Ask a parent to supervise.',cost:null,currency:null,availability:'Available',prerequisites:'Check materials and supervision.'};
const tutor={id:uid(71),version:2,name:'Gravity tutor',bio:'Science tutor',qualifications:'Teacher',experience:'Primary science',languages:['English'],availability:null,expertise:[{subject_id:ids.s,topic_id:ids.t,claim_status:'declared'}]};
function structuredResult(index){
 const resource=index===2?resources[1]:index===4?licensedVideo:{...resources[0],type:'image',mime_type:'image/png'};
 const kind=index===3?'kit':index===5?'tutor':'resource', item=kind==='kit'?practiceKit:kind==='tutor'?tutor:resource;
 const primary={candidate_id:item.id,candidate_kind:kind,candidate_type:kind==='kit'?'activity_kit':kind==='tutor'?'tutor':resource.type,version:2,display_mode:index===1?'reference earlier':index===0||index===2?'inline':'optional card',reason:kind==='kit'?'This kit helps you practise gravity.':kind==='tutor'?'This tutor lists science expertise.':'This media supports the current concept.',availability_state:kind==='tutor'?'unknown':'available',reference_message_id:index===1?uid(21):null};
 return {status:'ok',resources:kind==='resource'?[resource]:[],teachers:kind==='tutor'?[tutor]:[],kits:kind==='kit'?[practiceKit]:[],recommendation_decision:{learning_intent:kind==='kit'?'practise':kind==='tutor'?'human_help':'explain',concept:'gravity',primary,alternative:null,display_mode:primary.display_mode}};
}
const licensedVideo={id:uid(60),version:2,type:'video',mime_type:'video/webm',title:'Licensed gravity video',description:'Gravity lesson',caption_or_transcript:'Objects fall toward Earth.',accessibility_note:'Transcript below.'};
const titles = ['Force — push pull', 'Gravity makes objects fall', 'Broken gravity illustration'];
const resources = titles.map((title, i) => ({ id: uid(50+i), version: 2, type: 'image', title, description: title + ' for Grade 1 learners', alt_text: title, caption_or_transcript: title, attribution: null }));
resources[0].type='animation'; resources[0].mime_type='image/gif';
const turns = ['Explain force', 'Another force example', 'Explain gravity', 'Explain evaporation', 'Show the force image again', 'Show a gravity diagram'];
const messages = new Map([[rows[0].id, turns.flatMap((text, i) => [
 { id: uid(20+i*2), role: 'user', turn_number: i+1, blocks: [{ kind: 'text', text }] },
 { id: uid(21+i*2), role: 'assistant', turn_number: i+1, blocks: [{ kind: 'text', text: 'Explanation '+(i+1)+': '+text }] }
])]]);
const displays = new Map();
const json = (response, value, status = 200) => { response.writeHead(status, { 'content-type': 'application/json' }); response.end(JSON.stringify(value)); };
const body = async request => { const chunks = []; for await (const chunk of request) chunks.push(chunk); return JSON.parse(Buffer.concat(chunks).toString() || '{}'); };
const mock = http.createServer(async (request, response) => {
  const route = new URL(request.url, 'http://fixture').pathname.replace('/api/v1/', '');
  if (request.headers['x-bff-key'] !== 'sidebar-test-secret' || request.headers['x-flame-session'] !== 'sidebar-test-session') return json(response, {}, 401);
  if (route === 'me') return json(response, { id: uid(99), role: 'member', email: 'sidebar@example.test' });
  if (route === 'curricula') return json(response, { items: [{ id: ids.c }] });
  if (route === `curricula/${ids.c}/tree`) return json(response, tree);
  if (route === 'me/learning') return json(response, { items: [{ id: uid(98), curriculum_id: ids.c, visible: true, version: 1 }] });
  if (route === 'me/activity') return json(response, { recorded: true });
  if (route === 'sessions') return json(response, { items: rows, next_cursor: null });
  if (route === 'sessions/recent/clear') { rows.forEach(row => { if (!row.pinned) row.recent_at = null; }); return json(response, { status: 'cleared' }); }
  if (route === 'sessions/pins/clear') { rows.forEach(row => { if (row.pinned) { row.pinned = false; row.recent_at = new Date().toISOString(); } }); return json(response, { status: 'unpinned' }); }
  if (route.endsWith('/images/displayed')) { const data = await body(request); displays.set(data.message_id, data); return json(response, {status:'ok'}); }
  if(route.endsWith('/recommendations/displayed')){const data=await body(request);seenRecommendations.add(data.candidate_id);return json(response,{status:'ok'});}
  const supportOpen=route.match(/^sessions\/[^/]+\/recommendations\/([^/]+)$/);
  if(supportOpen){const mid=new URL(request.url,'http://fixture').searchParams.get('message_id');const index=[21,23,25,27,29,31].findIndex(n=>uid(n)===mid);const data=structuredResult(index);if(unavailableKit&&supportOpen[1]===practiceKit.id)return json(response,{error:{message:'Kit is unavailable'}},404);return json(response,{decision:data.recommendation_decision.primary,item:[...data.resources,...data.teachers,...data.kits].find(r=>r.id===supportOpen[1])});}
  const delivery = route.match(/^resources\/([^/]+)\/delivery$/);
  if (delivery) { if(delivery[1]===licensedVideo.id)return json(response,{status:'ok',version:2,launch_mode:licensedVideo.type==='external_video'?'external_video':'media',url:licensedVideo.type==='external_video'?'https://www.youtube.com/embed/M7lc1UVf-VE':base+'/licensed.webm'});const resource = resources.find(r => r.id === delivery[1]); return json(response, { status:'ok', version:2, launch_mode:'media', url:'http://localhost:3116/fixture-'+(resource.id === uid(52) ? 'broken' : resource.id)+'.png' }); }
  if (route.endsWith('/activity')) return json(response, {status:'ok'});
  const match = route.match(/^sessions\/([^/]+)\/(pin|recent|messages|recommendations)$/);
  if (match) {
    const row = rows.find(row => row.id === match[1]);
    if (!row) return json(response, {}, 404);
    if (match[2] === 'messages') return json(response, { items: messages.get(row.id), next_cursor: null });
    if (match[2] === 'recommendations') {
      const mid = new URL(request.url, 'http://fixture').searchParams.get('message_id');
      const index = [21,23,25,27,29,31].findIndex(n => uid(n) === mid);
      if(failedRecommendations)return json(response,{status:'unavailable',resources:[],teachers:[],learning_response:{schema_version:1,message_id:mid,recommendations:{status:'unavailable',code:'recommendation_timeout'}}});
      if(structured){const data=structuredResult(index);return json(response,{...data,learning_response:{schema_version:1,message_id:mid,recommendations:{status:'completed',data}}});}
      if(includeVideo&&index===3)return json(response,{status:'ok',resources:[licensedVideo],teachers:[],image_decision:{display_mode:'none'}});
      const resource = index === 2 ? resources[1] : index === 5 ? resources[2] : resources[0];
      const mode = index === 3 ? 'none' : index === 1 ? 'reference earlier' : 'inline';
      return json(response, {status:'ok', resources:mode==='none'?[]:[resource], teachers:[], image_decision:{ resource_id:mode==='none'?null:resource.id, resource_version:2, display_mode:mode, reason:'Fixture concept match', reference_message_id:index===1?uid(21):null, displayed:displays.get(mid)?.display_status==='displayed' }});
    }
    if (match[2] === 'pin') { row.pinned = (await body(request)).pinned; row.recent_at ||= new Date().toISOString(); return json(response, row); }
    if (match[2] === 'recent') { opens++; row.recent_at = new Date().toISOString(); return json(response, row); }
  }
  json(response, { error: { code: 'not_found' } }, 404);
});
(async () => {
  await new Promise(resolve => mock.listen(0, '127.0.0.1', resolve));
  const server = spawn(process.execPath, [path.join(cwd, 'node_modules/next/dist/bin/next'), 'start', '-p', '3116'], { cwd, windowsHide:true, env:{...process.env, FLAME_API_URL:`http://127.0.0.1:${mock.address().port}`, FLAME_BFF_SHARED_KEY:'sidebar-test-secret', FLAME_WEB_ORIGIN:base} });
  let browser, log=''; server.stdout.on('data',d=>log+=d); server.stderr.on('data',d=>log+=d);
  try {
    let ready=false; for(let i=0;i<40;i++){try{if((await fetch(base+'/sign-in')).ok){ready=true;break;}}catch{} await new Promise(r=>setTimeout(r,500));} assert(ready,log);
    browser=await chromium.launch({channel:'msedge',headless:true});
    const context=await browser.newContext({viewport:{width:1200,height:850},reducedMotion:'reduce'});
    await context.addCookies([{name:'flame_session',value:'sidebar-test-session',url:base,httpOnly:true}]);
    const page=await context.newPage(); const errors=[]; page.on('pageerror',e=>errors.push(e.message));
    await page.route('**/fixture-*.png',route => route.request().url().includes('broken') ? route.fulfill({status:404}) : route.request().url().includes(uid(50)) ? route.fulfill({contentType:'image/gif',body:fs.readFileSync(path.join(__dirname,'fixtures/force-motion.gif'))}) : route.fulfill({contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="600" height="180"><rect width="600" height="180" fill="#e9f2ff"/><text x="50" y="90" font-size="24" fill="#264774">Isolated learning illustration fixture</text></svg>'}));
    const open = async()=>{await page.goto(base,{waitUntil:'networkidle'}); await page.locator('.desktop-sidebar .shortcut-section').getByRole('button',{name:'Falling objects (study)',exact:true}).click();};
    await open();
    await page.locator('.conversation-inline-image').first().waitFor();
    const animation=page.locator('.conversation-inline-image .animated-media').first();
    await animation.getByRole('button',{name:'Play animation',exact:true}).waitFor();
    assert.equal(await animation.getAttribute('data-playing'),'false');
    await animation.getByRole('button',{name:'Play animation',exact:true}).click();assert.equal(await animation.getAttribute('data-playing'),'true');
    await animation.getByRole('button',{name:'Pause animation',exact:true}).click();assert(await animation.locator('canvas').isVisible());
    await page.getByRole('button',{name:'Retry image',exact:true}).waitFor();
    await page.waitForFunction(()=>document.querySelectorAll('.conversation-inline-image img').length===3);
    assert.equal(await page.locator('dialog[open]').count(),0,'No automatic modal');
    assert.equal(await page.getByRole('heading',{name:'Explore further',exact:true}).count(),0);
    assert.equal(await page.getByText('No published resources or subject-matched teachers are available for this answer yet.').count(),0);
    assert.deepEqual(await page.locator('.conversation-inline-image img').evaluateAll(images=>images.map(i=>i.alt)),[titles[0],titles[1],titles[0]]);
    assert(await page.locator('.conversation-inline-image img').evaluateAll(images=>images.every(i=>i.complete&&i.naturalWidth>0)));
    await page.getByRole('button',{name:'View earlier image · '+titles[0],exact:true}).click();
    assert.equal(await page.locator(':focus').getAttribute('id'),'learning-image-'+uid(21));
    await page.getByRole('button',{name:'Enlarge '+titles[0],exact:true}).first().click();
    await page.getByRole('dialog',{name:titles[0],exact:true}).waitFor();
    await page.getByRole('button',{name:'Close resource',exact:true}).click();
    assert.equal(await page.getByText('Explanation 6: Show a gravity diagram', {exact:true}).count(),1);
    for(let i=0;i<100&&(!displays.has(uid(21))||!displays.has(uid(31)));i++)await new Promise(r=>setTimeout(r,100));
    assert.equal(displays.get(uid(21))?.display_status,'displayed',JSON.stringify([...displays])+' '+log); assert.equal(displays.get(uid(31))?.display_status,'failed');
    await page.reload({waitUntil:'networkidle'});
    await page.locator('.desktop-sidebar .shortcut-section').getByRole('button',{name:'Falling objects (study)',exact:true}).click();
    await page.getByRole('button',{name:'View earlier image · '+titles[0],exact:true}).waitFor();
    assert.equal(displays.get(uid(21))?.resource_version,2);
    assert.deepEqual(errors,[]);
    await page.screenshot({path:path.resolve(cwd,'../../../work/conversation-inline-images.png'),fullPage:true});
    // Licensed uploaded video stays inside the same conversation, including mobile/fullscreen.
    const movie=await page.evaluate(async()=>{const canvas=document.createElement('canvas');canvas.width=240;canvas.height=135;canvas.style.cssText='position:fixed;top:0;left:0;opacity:.01;pointer-events:none';document.body.appendChild(canvas);const context=canvas.getContext('2d');context.fillStyle='#336699';context.fillRect(0,0,240,135);const stream=canvas.captureStream(10);const recorder=new MediaRecorder(stream,{mimeType:'video/webm;codecs=vp8'});const chunks=[];recorder.ondataavailable=e=>chunks.push(e.data);const done=new Promise(resolve=>recorder.onstop=resolve);recorder.start();context.fillStyle='white';context.fillRect(10,10,30,30);const timer=setInterval(()=>{context.fillStyle='#336699';context.fillRect(0,0,240,135);context.fillStyle='white';context.fillText('Gravity '+Date.now(),10,50);},50);await new Promise(r=>setTimeout(r,900));recorder.stop();await done;clearInterval(timer);stream.getTracks().forEach(t=>t.stop());canvas.remove();return Array.from(new Uint8Array(await new Blob(chunks).arrayBuffer()));});
    await page.route('**/licensed.webm',route=>route.fulfill({contentType:'video/webm',body:Buffer.from(movie)}));includeVideo=true;await open();const card=page.getByRole('button',{name:/Licensed gravity video/});await card.scrollIntoViewIfNeeded();const scroll=await page.evaluate(()=>window.scrollY);let popups=0;page.on('popup',()=>popups++);
    await card.click();let player=page.getByRole('dialog',{name:licensedVideo.title,exact:true});await player.locator('video').evaluate(v=>v.loop=true);await player.getByRole('button',{name:'Play video',exact:true}).focus();await page.keyboard.press('Space');await player.getByRole('button',{name:'Pause video',exact:true}).click();await player.getByRole('button',{name:'Enter fullscreen',exact:true}).click();await player.getByRole('button',{name:'Exit fullscreen',exact:true}).click();await player.getByRole('button',{name:'Close player',exact:true}).click();await player.waitFor({state:'hidden'});assert.equal(page.url(),base+'/');assert(Math.abs((await page.evaluate(()=>window.scrollY))-scroll)<2);assert.equal(popups,0);
    await page.setViewportSize({width:390,height:740});await card.click();player=page.getByRole('dialog',{name:licensedVideo.title,exact:true});await player.getByRole('button',{name:'Play video',exact:true}).click();await player.getByRole('button',{name:'Pause video',exact:true}).click();assert.equal(await player.locator('a,iframe').count(),0);await page.keyboard.press('Escape');await player.waitFor({state:'hidden'});assert.equal(popups,0);assert.equal(await page.getByText('Explanation 4: Explain evaporation',{exact:true}).count(),1);assert.deepEqual(errors,[]);
    // Provider SDK fixtures exercise FLAME controls and failure recovery without real provider dependencies.
    await page.route('https://www.youtube.com/iframe_api',route=>route.fulfill({contentType:'application/javascript',body:`window.YT={Player:function(frame,config){this.playVideo=()=>config.events.onStateChange({data:1});this.pauseVideo=()=>{};window.fixtureVideoError=()=>config.events.onError({data:101});setTimeout(()=>config.events.onReady(),0);}};window.onYouTubeIframeAPIReady?.();`}));
    await page.route(/^https:\/\/www\.youtube\.com\/embed\//,route=>route.fulfill({contentType:'text/html',body:'<p>Provider player fixture</p>'}));
    licensedVideo.type='external_video';await page.setViewportSize({width:1200,height:850});await open();await page.setViewportSize({width:390,height:740});const externalCard=page.getByRole('button',{name:/Licensed gravity video/});await externalCard.scrollIntoViewIfNeeded();const beforeExternal=await page.evaluate(()=>window.scrollY);await externalCard.click();player=page.getByRole('dialog',{name:licensedVideo.title,exact:true});await player.getByRole('button',{name:'Play video',exact:true}).click();await player.getByRole('button',{name:'Play video',exact:true}).focus();await page.keyboard.press('Space');await player.getByRole('button',{name:'Pause video',exact:true}).click();assert.equal(await player.locator('iframe').count(),1);await player.getByRole('button',{name:'Fullscreen',exact:true}).click();await player.getByRole('button',{name:'Exit fullscreen',exact:true}).click();await page.evaluate(()=>window.fixtureVideoError());await player.getByRole('alert').filter({hasText:'cannot be embedded'}).waitFor();await player.getByRole('button',{name:'Retry video',exact:true}).click();await player.getByRole('button',{name:'Play video',exact:true}).click();await player.getByRole('button',{name:'Close player',exact:true}).click();await player.waitFor({state:'hidden'});assert.equal(page.url(),base+'/');assert(Math.abs((await page.evaluate(()=>window.scrollY))-beforeExternal)<2);assert.equal(popups,0);assert.equal(await page.getByText('Explanation 4: Explain evaporation',{exact:true}).count(),1);assert.deepEqual(errors,[]);
    // Structured MVP recommendations reuse existing viewers and never open anything automatically.
    structured=true;await page.setViewportSize({width:1200,height:850});await open();await page.getByRole('button',{name:'View activity kit: Gravity practice kit',exact:true}).waitFor();assert.equal(await page.locator('dialog[open]').count(),0);assert.equal(await page.getByRole('heading',{name:'Explore further',exact:true}).count(),0);
    await page.getByRole('button',{name:'View earlier resource · '+titles[0],exact:true}).click();assert.equal(await page.locator(':focus').getAttribute('id'),'learning-resource-'+uid(21)+'-'+uid(50));
    await page.getByRole('button',{name:'View activity kit: Gravity practice kit',exact:true}).click();let support=page.getByRole('dialog',{name:practiceKit.name,exact:true});await support.getByText(practiceKit.instructions,{exact:true}).waitFor();await support.getByText(practiceKit.supervision,{exact:true}).waitFor();await support.getByRole('button',{name:'Close resource',exact:true}).click();
    await page.getByRole('button',{name:'View tutor: Gravity tutor',exact:true}).click();support=page.getByRole('dialog',{name:tutor.name,exact:true});await support.getByText('Availability: Unknown — confirm with the tutor',{exact:true}).waitFor();await support.getByText('Viewing this profile does not book a session or contact the tutor. Scheduling is not yet available in FLAME.',{exact:true}).waitFor();await page.keyboard.press('Escape');
    await page.getByRole('button',{name:'Play video: '+licensedVideo.title,exact:true}).click();player=page.getByRole('dialog',{name:licensedVideo.title,exact:true});await player.getByRole('button',{name:'Play video',exact:true}).click();await player.getByRole('button',{name:'Close player',exact:true}).click();
    unavailableKit=true;await page.getByRole('button',{name:'View activity kit: Gravity practice kit',exact:true}).click();await page.getByRole('alert').filter({hasText:'recommendation changed or is unavailable'}).waitFor();assert.equal(await page.locator('dialog[open]').count(),0);assert.equal(await page.getByText('Explanation 4: Explain evaporation',{exact:true}).count(),1);unavailableKit=false;
    for(let i=0;i<50&&!seenRecommendations.has(tutor.id);i++)await new Promise(r=>setTimeout(r,100));assert(seenRecommendations.has(tutor.id)&&seenRecommendations.has(practiceKit.id)&&seenRecommendations.has(licensedVideo.id));
    await page.setViewportSize({width:390,height:740});await page.getByRole('button',{name:'View activity kit: Gravity practice kit',exact:true}).click();support=page.getByRole('dialog',{name:practiceKit.name,exact:true});assert(await support.evaluate(d=>d.scrollWidth<=d.clientWidth+1));await page.keyboard.press('Escape');await page.screenshot({path:path.resolve(cwd,'../../../work/mvp-recommendations-mobile.png'),fullPage:true});
    failedRecommendations=true;await page.setViewportSize({width:1200,height:850});await open();await page.getByRole('button',{name:'Retry learning suggestions',exact:true}).first().waitFor();assert.equal(await page.getByText('Explanation 4: Explain evaporation',{exact:true}).count(),1);assert.deepEqual(errors,[]);
    console.log('PASS: existing image/GIF/native/external video regressions plus structured MVP image/reference/cards, kit instructions/supervision, unknown tutor availability, rechecked unavailable kit, display acknowledgements, failure isolation, keyboard controls and narrow-screen layout. Provider SDKs are fixtures.');
  } finally {await browser?.close();server.kill();mock.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
