// Isolated production app + synthetic API; no real accounts, provider calls or database writes.
const assert = require('node:assert/strict');
const http = require('node:http');
const path = require('node:path');
const fs = require('node:fs');
const { spawn } = require('node:child_process');
const toolRoot = process.env.FLAME_UI_TOOLS || path.resolve(__dirname, '../../../../.kilo/ui-check/node_modules');
const { chromium } = require(path.join(toolRoot, 'playwright'));
const AxeBuilder = require(path.join(toolRoot, '@axe-core/playwright')).default;
const cwd = path.resolve(__dirname, '..');
const port=Number(process.env.FLAME_SIMULATION_PORT||3117);
const base = 'http://localhost:'+port;
let currentSpec,streamFixture=false,networkLeaks=0;
let pendingReplies=0,simulationStarts=[],failSimulation=false,eligibilityDelay=0;
const simulationSources = require('./simulation-fixtures.cjs');
const uid = n => `${String(n).padStart(8, '0')}-1111-4111-8111-111111111111`;
const ids = { c:uid(1),l:uid(2),s:uid(3),d:uid(4),t:uid(5),st:uid(6) };
const tree = {id:ids.c,name:'Rich renderer curriculum',revision:1,levels:[{id:ids.l,name:'Grade 1',subjects:[{id:ids.s,name:'Science',domains:[{id:ids.d,name:'Motion',categories:[],topics:[{id:ids.t,name:'Gravity',subtopics:[{id:ids.st,name:'Falling objects'}]}]}]}]}]};
const contextPath = {curriculum_id:ids.c,level_id:ids.l,subject_id:ids.s,domain_id:ids.d,category_id:null,topic_id:ids.t,subtopic_id:ids.st,names:{topic:'Gravity',subtopic:'Falling objects'}};
const now = new Date().toISOString();
const sessions = ['study','curiosity'].map((mode,i)=>({id:uid(10+i),mode,context:mode==='study'?contextPath:null,revision:mode==='study'?1:null,pinned:false,first_question:mode==='study'?'Rich Study answer':'Rich Curiosity answer',created_at:now,updated_at:now,recent_at:now}));
const markdown = [
  '## Rich learning answer',
  '**Strong explanation** with *emphasis* and ~~old wording~~.',
  '- [x] First idea\n- [ ] Second idea',
  '| Time | Distance |\n| --- | --- |\n| 1 | 2 |',
  'An inline equation $$d = vt$$. Currency stays literal: $5 and $10.',
  '$$\n\\frac{1}{2} + x^2\n$$',
  '```python\nprint("Hello learner")\n```',
  '```unknown-language\n<literal-code>\n```',
  '```json\n{"example": 2}\n```',
  '[Safe link](https://example.com) [Unsafe link](javascript:alert(1))',
  '![Omitted image](https://example.com/tracking.png)',
  '<script>window.__richAttack = true</script><iframe src="https://example.com"></iframe>',
  'Malformed math remains readable: $$\\notARealCommand{x}$$',
].join('\n\n');
const templates = require('../src/features/learning/math-templates.json');
function mathBlock(template) { return {id:template,kind:'math_visual',version:1,template,title:templates[template].label,description:'Explore this mathematical example using the controls.',parameters:Object.fromEntries(Object.entries(templates[template].parameters).map(([key,spec])=>[key,spec.default]))}; }
function blocks() { return [{id:'intro',kind:'markdown',text:'**Interactive science**. Explore the simulation below alongside this explanation.'}]; }
const messages = new Map(sessions.map(session=>[session.id,[{id:uid(20),role:'user',turn_number:1,blocks:[{kind:'text',text:session.first_question}]},{id:uid(21),role:'assistant',turn_number:1,blocks:blocks()}]]));
const json = (res,value,status=200)=>{res.writeHead(status,{'content-type':'application/json'});res.end(JSON.stringify(value));};
const body = async req=>{const chunks=[];for await(const chunk of req)chunks.push(chunk);return JSON.parse(Buffer.concat(chunks).toString()||'{}');};
let asks=0, failNext=false;
const mock = http.createServer(async(req,res)=>{
  if(req.url.startsWith('/sandbox-network-probe')){networkLeaks++;return json(res,{},403);}
  const route=new URL(req.url,'http://fixture').pathname.replace('/api/v1/','');
  if(req.headers['x-bff-key']!=='rich-test-secret'||req.headers['x-flame-session']!=='rich-test-session')return json(res,{},401);
  if(route==='me')return json(res,{id:uid(99),role:'member',email:'rich@example.test'});
  if(route==='curricula')return json(res,{items:[{id:ids.c}]});
  if(route===`curricula/${ids.c}/tree`)return json(res,tree);
  if(route==='me/learning')return json(res,{items:[{id:uid(98),curriculum_id:ids.c,visible:true,version:1}]});
  if(route==='me/activity')return json(res,{recorded:true});
  if(route==='sessions')return json(res,{items:sessions,next_cursor:null});
  const match=route.match(/^sessions\/([^/]+)\/(recent|messages|recommendations|capability-check|ask|ask-stream|simulation)$/);
  if(match){
    const session=sessions.find(row=>row.id===match[1]);
    if(!session)return json(res,{},404);
    if(match[2]==='recent')return json(res,session);
    if(match[2]==='messages')return json(res,{items:messages.get(session.id),next_cursor:null});
    if(match[2]==='recommendations')return json(res,{status:'no_results',resources:[],teachers:[],activity_kits:[]});
    if(match[2]==='capability-check')return json(res,{status:'continue'});
    if(match[2]==='simulation'){
      const input=await body(req);simulationStarts.push(input.start);
      if(eligibilityDelay)await new Promise(resolve=>setTimeout(resolve,eligibilityDelay));
      if(failSimulation){failSimulation=false;return json(res,{error:{code:'fixture_interruption'}},503);}
      if(pendingReplies>0){pendingReplies--;return json(res,{status:'pending'});}
      return json(res,currentSpec);
    }
    if(match[2]==='ask-stream'){
      if(!streamFixture)return json(res,{},404);
      await body(req);res.writeHead(200,{'content-type':'application/x-ndjson','cache-control':'no-store'});
      res.write(JSON.stringify({type:'delta',text:'Streaming science explanation.'})+'\n');
      setTimeout(()=>res.end(JSON.stringify({type:'answer',answer:{status:'ok',route:'direct_llm',knowledge_source:'model_generated',grounded:false,message_id:uid(87),blocks:[{id:'streamed',kind:'markdown',text:'Completed streaming science explanation.'}]}})+'\n'),600);return;
    }
    if(match[2]==='ask'){
      asks++;
      const question=(await body(req)).question;
      if(failNext){failNext=false;return json(res,{error:{code:'provider_unavailable',message:'Try again.'}},503);}
      const saved=messages.get(session.id),turn=1+saved.filter(row=>row.role==='user').length;
      const answer=blocks().map(block=>({...block,id:block.id+'-'+turn}));
      saved.push({id:uid(30+turn*2),role:'user',turn_number:turn,blocks:[{kind:'text',text:question}]},{id:uid(31+turn*2),role:'assistant',turn_number:turn,blocks:answer});
      return json(res,{status:'ok',route:'direct_llm',knowledge_source:'model_generated',grounded:false,message_id:uid(31+turn*2),blocks:answer});
    }
  }
  return json(res,{error:{code:'not_found'}},404);
});
(async()=>{
  let live;
  if(process.argv.includes('--live')&&!process.env.FLAME_EXISTING_LIVE_SERVER){
    const apiRoot=path.resolve(cwd,'../flame-api');
    live=spawn(path.join(apiRoot,'.venv/Scripts/python.exe'),['-m','scripts.check_simulations'],{cwd:apiRoot,windowsHide:true});
    live.stdout.on('data',d=>process.stdout.write(d));live.stderr.on('data',d=>process.stderr.write(d));
    await new Promise(resolve=>setTimeout(resolve,2000));
  }
  await new Promise(resolve=>mock.listen(0,'127.0.0.1',resolve));
  const server=spawn(process.execPath,[path.join(cwd,'node_modules/next/dist/bin/next'),process.env.FLAME_TEST_DEV?'dev':'start','-p',String(port)],{cwd,windowsHide:true,env:{...process.env,FLAME_NEXT_DIST_DIR:process.env.FLAME_TEST_DEV?'.next-f13-dev':'.next-f13',FLAME_API_URL:`http://127.0.0.1:${mock.address().port}`,FLAME_BFF_SHARED_KEY:'rich-test-secret',FLAME_WEB_ORIGIN:base}});
  let log='',browser;
  server.stdout.on('data',d=>log+=d);server.stderr.on('data',d=>log+=d);
  try{
    for(let i=0;i<60;i++){try{if((await fetch(base+'/sign-in')).ok)break;}catch{}await new Promise(r=>setTimeout(r,500));}
    browser=await chromium.launch({channel:'msedge',headless:true,args:['--enable-unsafe-swiftshader']});
    const context=await browser.newContext({viewport:{width:1200,height:1000}});
    await context.addCookies([{name:'flame_session',value:'rich-test-session',url:base,httpOnly:true}]);
    const page=await context.newPage(),errors=[],external=[];
    page.on('pageerror',e=>{errors.push(e.message);console.log('PAGE ERROR',e.message);});
    page.on('response',async r=>{if(r.url().endsWith('/compile')&&!r.ok())console.log('COMPILE FAILURE',await r.text().catch(()=>''));});
    page.on('request',r=>{if(!r.url().startsWith(base)&&/^https?:/.test(r.url()))external.push(r.url());});
    page.on('console',msg=>{if(msg.type()==='error')console.log('browser:',msg.text().slice(0,240));});
    let specs=simulationSources;
    if(process.argv.includes('--live')){const response=await fetch('http://127.0.0.1:3138/fixtures',{signal:AbortSignal.timeout(120000)});assert(response.ok,'Live generation failed');specs=await response.json();}
    const firstCsrf=await context.request.get(base+'/api/auth/csrf');const firstToken=(await firstCsrf.json()).csrf;
    const parallelCsrf=await Promise.all([context.request.get(base+'/api/auth/csrf'),context.request.get(base+'/api/auth/csrf')]);
    for(const response of parallelCsrf)assert.equal((await response.json()).csrf,firstToken,'Parallel calls must retain the CSRF token');
    assert.equal((await context.request.post(base+'/api/simulations/compile',{data:{}})).status(),403);
    assert.equal((await context.request.post(base+'/api/simulations/compile',{headers:{origin:'https://untrusted.invalid','x-flame-csrf':firstToken},data:{}})).status(),403);
    assert.equal((await context.request.post(base+'/api/simulations/compile',{headers:{origin:base,'x-flame-csrf':firstToken},data:{}})).status(),422);
    const results=[];
    // Ordinary answers must not flash simulation progress during eligibility checks.
    currentSpec={status:'ineligible'};eligibilityDelay=1500;
    await page.goto(base,{waitUntil:'networkidle'});
    const eligibility=page.waitForResponse(response=>response.url().includes('/simulation')&&!response.url().includes('/compile'));
    await page.locator('.desktop-sidebar').getByRole('button',{name:'Falling objects (study)',exact:true}).click();
    await page.waitForTimeout(300);
    assert.equal(await page.getByRole('progressbar',{name:'Interactive simulation preparation'}).count(),0,'No progress while deciding whether an answer needs a simulation');
    await eligibility;
    assert.equal(await page.getByRole('progressbar',{name:'Interactive simulation preparation'}).count(),0,'Non-simulation answers never display simulation progress');
    eligibilityDelay=0;
    console.log('Non-simulation eligibility checks have no progress indicator: passed');
    for(const spec of specs.filter(s=>!process.env.FLAME_ENGINE||s.engine===process.env.FLAME_ENGINE)){
      pendingReplies=2;simulationStarts=[];
      currentSpec={status:'ready',version:1,title:spec.name,description:'Explore this illustrative simulation.',...spec};
      if(spec.name==='isolation-probe')currentSpec.source=currentSpec.source.replace("['https:','','example.invalid','blocked.js'].join('/')",JSON.stringify(`http://127.0.0.1:${mock.address().port}/sandbox-network-probe`));
      await page.goto(base,{waitUntil:'networkidle'});
      await page.locator('.desktop-sidebar').getByRole('button',{name:'Falling objects (study)',exact:true}).click();
      await page.getByText('Preparing interactive simulation…',{exact:true}).waitFor();
      const generatingProgress=page.getByRole('progressbar',{name:'Interactive simulation preparation'});
      assert.equal(await generatingProgress.getAttribute('aria-valuemin'),'0');
      assert.equal(await generatingProgress.getAttribute('aria-valuemax'),'100');
      assert(Number(await generatingProgress.getAttribute('aria-valuenow'))<70,'Generation progress must remain below its completed milestone');
      await page.getByText('Estimated progress',{exact:true}).waitFor();
      const progressDir=path.resolve(cwd,'../../../work/f13');fs.mkdirSync(progressDir,{recursive:true});
      if(spec.engine==='matter')await page.locator('.simulation-progress').screenshot({path:path.join(progressDir,'preparation-progress.png')});
      const player=page.locator('.flame-message .simulation-player');
      await player.waitFor();
      await page.waitForFunction(()=>['ready','error'].includes(document.querySelector('.simulation-player')?.dataset.simulationState),{},{timeout:30000});
      const state=await player.getAttribute('data-simulation-state');
      if(state!=='ready'){await page.waitForTimeout(500);console.log('SERVER LOG',log.slice(-3000));throw Error('Runtime failed: '+spec.name+' '+await player.innerText());}
      assert.equal(await player.getByRole('progressbar').getAttribute('aria-valuenow'),'100','Only actual sandbox ready completes progress');
      assert.equal(await player.getByText('Estimated progress',{exact:true}).count(),0);
      await player.getByRole('progressbar').waitFor({state:'detached'});
      assert.deepEqual(simulationStarts,[false,false,false],'History must poll pending source without starting another generation');
      const frame=player.frameLocator('iframe');
      const numeric=async key=>{const text=await frame.locator('output').innerText();const match=text.match(new RegExp('(?:^| · )'+key+': (-?[0-9.]+)'));return match?Number(match[1]):NaN;};
      const reset=async()=>{await player.getByRole('button',{name:'Reset simulation',exact:true}).click();await page.waitForFunction(()=>document.querySelector('.simulation-player')?.dataset.simulationState==='ready');await frame.getByRole('button',{name:'Pause',exact:true}).waitFor();};
      if(spec.name==='isolation-probe'){
        await frame.locator('output').filter({hasText:'networkBlocked: 1.00'}).waitFor();
        const readout=await frame.locator('output').innerText();
        for(const key of ['domBlocked','storageBlocked','workerBlocked','fetchBlocked','evalBlocked','networkBlocked'])assert(readout.includes(key+': 1.00'),key+' must be blocked at runtime');
      }
      if(spec.engine==='matter')await frame.locator('output').filter({hasText:'y:'}).waitFor();
      if(spec.name==='falling'){
        await frame.getByLabel('Gravity',{exact:false}).fill('0');
        const start=await numeric('y');await page.waitForTimeout(500);const zero=await numeric('y');
        await frame.getByLabel('Gravity',{exact:false}).fill('3');await page.waitForTimeout(400);const gravity=await numeric('y');
        assert(Number.isFinite(start)&&Number.isFinite(zero)&&Number.isFinite(gravity),'Falling ball must report positions');
        assert(gravity>zero+5,'Increased gravity must move the falling ball downward');
        await reset();
      }
      if(spec.name==='collision'){
        await page.waitForTimeout(1200);assert(await numeric('collisions')>=1,'Matter must report actual collisions');
        await frame.getByRole('button',{name:'Pause',exact:true}).click();await page.waitForTimeout(80);
        const x=await numeric('x'),y=await numeric('y'),box=await frame.locator('canvas').boundingBox();assert(box);
        await frame.getByLabel('Gravity',{exact:false}).fill('0');await frame.getByRole('button',{name:'Resume',exact:true}).click();
        await page.mouse.move(box.x+x/800*box.width,box.y+y/450*box.height);await page.mouse.down();await page.mouse.move(box.x+(x+80)/800*box.width,box.y+(y-80)/450*box.height,{steps:12});await page.mouse.up();
        await page.waitForTimeout(300);assert(Math.abs(await numeric('y')-y)>20,'Dragging must move a body');
        await reset();
      }
      if(spec.name==='friction'){
        await frame.getByLabel('Friction',{exact:false}).fill('0');await page.waitForTimeout(450);const low=await numeric('x');
        await reset();await frame.getByLabel('Friction',{exact:false}).fill('0.8');await page.waitForTimeout(450);const high=await numeric('x');
        assert(Number.isFinite(low)&&Number.isFinite(high)&&low>high+15,`Higher friction must reduce sliding distance: low=${low}, high=${high}`);
        await reset();
      }
      await frame.getByRole('button',{name:'Pause',exact:true}).click();
      await frame.getByRole('button',{name:'Resume',exact:true}).waitFor();
      await page.evaluate(()=>document.dispatchEvent(new Event('visibilitychange')));
      await frame.getByRole('button',{name:'Resume',exact:true}).waitFor();
      await frame.getByRole('button',{name:'Resume',exact:true}).click();
      if(['three','r3f'].includes(spec.engine)){
        if(spec.engine==='r3f')await frame.locator('output').filter({hasText:'azimuth:'}).waitFor();
        const beforeOrbit=spec.engine==='r3f'?await numeric('azimuth'):0;
        const box=await frame.locator('canvas').boundingBox();assert(box);
        await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2+100,box.y+box.height/2-40,{steps:8});await page.mouse.up();
        if(spec.engine==='r3f'){await page.waitForTimeout(300);assert(Math.abs(await numeric('azimuth')-beforeOrbit)>.1,'Pointer orbit must rotate the R3F camera');}
      }
      if(spec.engine==='matter'){
        await frame.getByLabel('Gravity',{exact:false}).fill('0');await frame.getByLabel('Friction',{exact:false}).fill('0.7');
        await frame.getByRole('button',{name:'Pause',exact:true}).click();
        await page.waitForTimeout(80);const before=await frame.locator('output').innerText();await page.waitForTimeout(400);assert.equal(await frame.locator('output').innerText(),before);
        await frame.getByRole('button',{name:'Resume',exact:true}).click();
      }
      await player.getByRole('button',{name:'Expand',exact:true}).click();await page.keyboard.press('Escape');
      await player.getByRole('button',{name:'Reset simulation',exact:true}).click();
      await page.waitForFunction(()=>document.querySelector('.simulation-player')?.dataset.simulationState==='ready');
      const audit=await new AxeBuilder({page}).include('.simulation-player').analyze();assert.deepEqual(audit.violations.map(v=>v.id),[]);
      await page.setViewportSize({width:390,height:844});
      assert(await player.evaluate(el=>el.scrollWidth<=el.clientWidth+1),'Simulation must fit mobile response width');
      await page.setViewportSize({width:1200,height:1000});
      const dir=path.resolve(cwd,'../../../work/f13');fs.mkdirSync(dir,{recursive:true});
      await player.evaluate(el=>el.scrollIntoView({block:'center'}));
      await player.screenshot({path:path.join(dir,spec.name+'.png')});
      await player.getByRole('button',{name:'Close',exact:true}).click();assert.equal(await player.locator('iframe').count(),0);for(let i=0;i<20&&page.workers().length;i++)await page.waitForTimeout(100);assert.equal(page.workers().length,0,'Closing must terminate physics/render workers');
      results.push({name:spec.name,engine:spec.engine,status:'passed'});console.log('INLINE RUNTIME PASSED',spec.name,spec.engine);
    }
    // A failed source request exits loading; explicit retry only retrieves the existing job.
    currentSpec={status:'ready',version:1,engine:'html5',title:'Recover source request',description:'Connection recovery',source:'export default ()=>({})'};
    failSimulation=true;simulationStarts=[];
    await page.goto(base,{waitUntil:'networkidle'});
    await page.locator('.desktop-sidebar').getByRole('button',{name:'Falling objects (study)',exact:true}).click();
    await page.getByRole('button',{name:'Check simulation',exact:true}).waitFor();
    assert.equal(await page.getByText('Preparing interactive simulation…',{exact:true}).count(),0);
    pendingReplies=1;
    await page.getByRole('button',{name:'Check simulation',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('.simulation-player')?.dataset.simulationState==='ready');
    assert.deepEqual(simulationStarts,[false,false,false]);
    console.log('Source request interruption and retrieval-only recovery: passed');
    // Reduced motion starts animation paused without removing manual controls.
    const reduced=await browser.newContext({viewport:{width:1200,height:1000},reducedMotion:'reduce'});
    await reduced.addCookies([{name:'flame_session',value:'rich-test-session',url:base,httpOnly:true}]);
    const reducedPage=await reduced.newPage();currentSpec={status:'ready',version:1,engine:'html5',title:'Reduced motion',description:'Paused initially',source:'export default ()=>({})'};
    await reducedPage.goto(base,{waitUntil:'networkidle'});
    const recent=reducedPage.getByRole('button',{name:'Falling objects (study)',exact:true});
    await recent.first().click();const reducedPlayer=reducedPage.locator('.simulation-player');await reducedPlayer.frameLocator('iframe').getByRole('button',{name:'Resume',exact:true}).waitFor();
    await reduced.close();
    // True text streaming remains usable when the independent compiler is slow/fails.
    streamFixture=true;
    currentSpec={status:'ready',version:1,engine:'html5',title:'Independent compile',description:'Separate compilation',source:'export default ()=>({})'};
    await page.goto(base,{waitUntil:'networkidle'});await page.locator('.desktop-sidebar').getByRole('button',{name:'Falling objects (study)',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('.simulation-player')?.dataset.simulationState==='ready');
    let releaseCompile,notifyCompile;let compilationHeld=false;
    const compilationStarted=new Promise(resolve=>notifyCompile=resolve);
    await page.route('**/api/simulations/compile',async route=>{compilationHeld=true;notifyCompile();await new Promise(r=>releaseCompile=r);await route.fulfill({status:422,json:{error:'synthetic_compile_failure'}}).catch(()=>{});});
    // Use the actual composer accessible textbox; fixture contracts stay identical to Study.
    const composer=page.locator('#flame-prompt');
    pendingReplies=2;simulationStarts=[];
    await composer.fill('Stream an independent explanation');await page.getByRole('button',{name:'Send learning request',exact:true}).click();
    await page.getByText('Streaming science explanation.',{exact:true}).waitFor();
    await page.getByText('Completed streaming science explanation.',{exact:true}).waitFor();
    await page.waitForFunction(()=>[...document.querySelectorAll('.simulation-player')].some(e=>e.dataset.simulationState==='compiling'));
    let compileTimer;
    try{await Promise.race([compilationStarted,new Promise((_,reject)=>{compileTimer=setTimeout(()=>reject(Error('Compiler request did not start')),15000);})]);}finally{clearTimeout(compileTimer);}
    assert(compilationHeld);assert(await page.getByText('Completed streaming science explanation.',{exact:true}).isVisible());
    const compilingProgress=page.locator('.simulation-player[data-simulation-state="compiling"]').getByRole('progressbar');
    const compilingValue=Number(await compilingProgress.getAttribute('aria-valuenow'));
    assert(compilingValue>=70&&compilingValue<90,'Held compilation must never report completion');
    assert.deepEqual(simulationStarts,[true,false,false],'Fresh response starts once, then polls without another generation request');
    releaseCompile();await page.getByText('This simulation could not run. Your explanation is still available.',{exact:true}).waitFor();
    assert.equal(await page.locator('.simulation-player[data-simulation-state="error"]').getByRole('progressbar').count(),0,'Failure must remove misleading progress');
    assert(await page.getByText('Completed streaming science explanation.',{exact:true}).isVisible());
    await page.unroute('**/api/simulations/compile');streamFixture=false;
    console.log('Text stream independent of slow/failed compilation: passed');
    // Runtime containment: a compiled infinite loop must terminate while host controls work.
    for(const source of ['export default ()=>{while(true){}}','throw Error("synthetic runtime failure");export default ()=>({})','postMessage({type:"ready"});export default ()=>{while(true){const t=performance.now();while(performance.now()-t<500){}postMessage({type:"heartbeat"});}}']){
      currentSpec={status:'ready',version:1,engine:'html5',title:'Failure probe',description:'Failure containment',source};
      await page.goto(base,{waitUntil:'networkidle'});await page.locator('.desktop-sidebar').getByRole('button',{name:'Falling objects (study)',exact:true}).click();
      await page.waitForFunction(()=>document.querySelector('.simulation-player')?.dataset.simulationState==='error',{},{timeout:22000});
      assert(await page.locator('.flame-message').getByText('Interactive science',{exact:false}).isVisible());
      await page.locator('.simulation-player').getByRole('button',{name:'Close',exact:true}).click();
    }
    if(process.argv.includes('--live'))assert.equal(results.length,4,'All four requested live demos must generate and execute');
    assert.equal(networkLeaks,0,'The sandbox must not reach the network sentinel');
    assert.deepEqual(external.filter(url=>!url.endsWith('/sandbox-network-probe')),[],'No unapproved external requests');
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({results,blockedNetworkAttempts:external.length,completedNetworkRequests:networkLeaks,hostResponsiveAfterInfiniteLoop:true},null,2));
  }finally{if(browser)await browser.close();server.kill();live?.kill();mock.closeAllConnections();await new Promise(r=>mock.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
