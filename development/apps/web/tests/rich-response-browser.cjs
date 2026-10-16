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
const base = 'http://localhost:3115';
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
  ...['math','latex','tex','katex'].map(lang=>'```'+lang+'\n\\frac{3}{4} + x^2 = 5\n```'),
  '```python\nprint("Hello learner")\n```',
  '```unknown-language\n<literal-code>\n```',
  '```json\n{"example": 2}\n```',
  '[Safe link](https://example.com) [Unsafe link](javascript:alert(1))',
  '![Omitted image](https://example.com/tracking.png)',
  '<script>window.__richAttack = true</script><iframe src="https://example.com"></iframe>',
  'Malformed math remains readable: $$\\notARealCommand{x}$$',
].join('\n\n');
function blocks() { return [
  {id:'markdown',kind:'markdown',text:markdown},
  ...['line','bar','pie'].map(chartType=>({id:chartType,kind:'chart',chartType,title:`${chartType} distance chart`,description:'An illustrative teaching example.',xKey:'seconds',xLabel:'Seconds',yLabel:'Metres',illustrative:true,series:[{key:'metres',label:'Distance'}],data:[{seconds:1,metres:2},{seconds:2,metres:4},{seconds:3,metres:6}]})),
  {id:'old',kind:'text',text:'Legacy text **stays literal**.'},
]; }
const messages = new Map(sessions.map(session=>[session.id,[{id:uid(20),role:'user',turn_number:1,blocks:[{kind:'text',text:session.first_question}]},{id:uid(21),role:'assistant',turn_number:1,blocks:blocks()}]]));
const json = (res,value,status=200)=>{res.writeHead(status,{'content-type':'application/json'});res.end(JSON.stringify(value));};
const body = async req=>{const chunks=[];for await(const chunk of req)chunks.push(chunk);return JSON.parse(Buffer.concat(chunks).toString()||'{}');};
let asks=0, failNext=false,lastAnswerRequest;
const mock = http.createServer(async(req,res)=>{
  const route=new URL(req.url,'http://fixture').pathname.replace('/api/v1/','');
  if(req.headers['x-bff-key']!=='rich-test-secret'||req.headers['x-flame-session']!=='rich-test-session')return json(res,{},401);
  if(route==='me')return json(res,{id:uid(99),role:'member',email:'rich@example.test'});
  if(route==='curricula')return json(res,{items:[{id:ids.c}]});
  if(route===`curricula/${ids.c}/tree`)return json(res,tree);
  if(route==='me/learning')return json(res,{items:[{id:uid(98),curriculum_id:ids.c,visible:true,version:1}]});
  if(route==='me/activity')return json(res,{recorded:true});
  if(route==='sessions')return json(res,{items:sessions,next_cursor:null});
  const match=route.match(/^sessions\/([^/]+)\/(recent|messages|recommendations|capability-check|ask)$/);
  if(match){
    const session=sessions.find(row=>row.id===match[1]);
    if(!session)return json(res,{},404);
    if(match[2]==='recent')return json(res,session);
    if(match[2]==='messages')return json(res,{items:messages.get(session.id),next_cursor:null});
    if(match[2]==='recommendations')return json(res,{status:'no_results',resources:[],teachers:[],activity_kits:[]});
    if(match[2]==='capability-check')return json(res,{status:'continue'});
    if(match[2]==='ask'){
      asks++;
      const submitted=await body(req);lastAnswerRequest=submitted;const question=submitted.question;
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
  await new Promise(resolve=>mock.listen(0,'127.0.0.1',resolve));
  const server=spawn(process.execPath,[path.join(cwd,'node_modules/next/dist/bin/next'),'start','-p','3115'],{cwd,windowsHide:true,env:{...process.env,FLAME_NEXT_DIST_DIR:process.env.FLAME_TEST_NEXT_DIST_DIR||'.next-f11',FLAME_API_URL:`http://127.0.0.1:${mock.address().port}`,FLAME_BFF_SHARED_KEY:'rich-test-secret',FLAME_WEB_ORIGIN:base}});
  let log='',browser;
  server.stdout.on('data',data=>log+=data);server.stderr.on('data',data=>log+=data);
  try{
    let ready=false;
    for(let i=0;i<60;i++){try{if((await fetch(base+'/sign-in')).ok){ready=true;break;}}catch{}await new Promise(resolve=>setTimeout(resolve,500));}
    assert(ready,log);
    browser=await chromium.launch({channel:'msedge',headless:true});
    const context=await browser.newContext({viewport:{width:1440,height:1000},permissions:['clipboard-read','clipboard-write']});
    await context.addCookies([{name:'flame_session',value:'rich-test-session',url:base,httpOnly:true}]);
    const page=await context.newPage(),errors=[],requests=[];
    page.on('pageerror',error=>errors.push(error.message));
    page.on('request',req=>{if(req.url().startsWith('https://example.com'))requests.push(req.url());});
    await page.goto(base,{waitUntil:'networkidle'});
    await page.locator('.desktop-sidebar').getByRole('button',{name:'Falling objects (study)',exact:true}).click();
    await page.locator('.response-markdown strong').filter({hasText:'Strong explanation'}).waitFor();
    assert.equal(await page.locator('.response-markdown input[type=checkbox]').count(),2);
    assert.equal(await page.locator('.response-markdown input[type=checkbox]:disabled').count(),2);
    assert(await page.locator('.response-markdown .katex').count()>=6);
    assert.equal(await page.locator('.response-code').count(),3,'Math fences must use KaTeX; only programming/unknown code uses Shiki');
    assert((await page.locator('.response-markdown').innerText()).includes('notARealCommand'), 'Malformed math must remain readable');
    assert((await page.locator('.response-markdown').innerText()).includes('$5 and $10'));
    assert.equal(await page.locator('.response-markdown img, .response-markdown iframe, .response-markdown script').count(),0);
    assert.equal(await page.locator('.response-markdown a[href^="javascript:"]').count(),0);
    assert.equal(await page.evaluate(()=>window.__richAttack),undefined);
    assert.deepEqual(requests,[]);
    await page.waitForFunction(()=>document.querySelectorAll('.response-code pre code span[style]').length>0);
    assert((await page.locator('.response-code').nth(1).innerText()).includes('<literal-code>'));
    await page.getByRole('button',{name:'Copy code',exact:true}).first().focus();
    await page.getByRole('button',{name:'Copy code',exact:true}).first().press('Enter');
    assert.equal(await page.evaluate(()=>navigator.clipboard.readText()),'print("Hello learner")');
    await page.waitForFunction(()=>document.querySelectorAll('.response-chart svg[role="application"]').length===3);
    const plot=page.locator('.response-chart svg[role="application"]').first();
    assert.equal(await plot.getAttribute('tabindex'),'0');
    await plot.focus();await plot.press('ArrowRight');
    assert.equal(await page.locator('.response-chart-example').count(),3);
    await page.getByText('View chart data',{exact:true}).first().focus();
    await page.getByText('View chart data',{exact:true}).first().press('Space');
    assert.equal(await page.locator('.response-chart details').first().locator('tbody tr').count(),3);
    assert((await page.locator('.content-text').allTextContents()).includes('Legacy text **stays literal**.'));
    const axe=await new AxeBuilder({page}).include('.learning-content').withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
    assert.deepEqual(axe.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)})),[]);
    const screenshotDir=path.resolve(cwd,'../../..','work','f11');fs.mkdirSync(screenshotDir,{recursive:true});
    await page.screenshot({path:path.join(screenshotDir,'rich-response-desktop.png'),fullPage:true});
    const input=page.locator('#flame-prompt');
    await input.fill('Show another example');await input.press('Enter');
    await page.waitForFunction(()=>document.querySelectorAll('.response-chart').length===6);
    assert.equal(asks,1);
    failNext=true;await input.fill('Retry this example');await input.press('Enter');
    await page.getByRole('button',{name:'Retry question',exact:true}).waitFor();
    await page.getByRole('button',{name:'Retry question',exact:true}).click();
    await page.waitForFunction(()=>document.querySelectorAll('.response-chart').length===9);
    assert.equal(asks,3);
    await page.reload({waitUntil:'networkidle'});
    await page.locator('.desktop-sidebar').getByRole('button',{name:'Falling objects (study)',exact:true}).click();
    await page.waitForFunction(()=>document.querySelectorAll('.response-chart').length===9);
    await page.locator('.desktop-sidebar').getByRole('button',{name:'Rich Curiosity answer (curiosity)',exact:true}).click();
    await page.waitForFunction(()=>document.querySelectorAll('.response-chart').length===3);
    await input.fill('Explain the chart');await input.press('Enter');
    await page.waitForFunction(()=>document.querySelectorAll('.response-chart').length===6);
    for(const width of [900,390]){
      await page.setViewportSize({width,height:900});
      await page.evaluate(()=>document.fonts.ready);
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Page overflow at ${width}`);
      assert(await page.locator('.response-chart').evaluateAll(els=>els.every(el=>el.scrollWidth<=el.clientWidth+1)),`Chart overflow at ${width}`);
    }
    await page.screenshot({path:path.join(screenshotDir,'rich-response-mobile.png'),fullPage:true});
    await page.locator('.response-chart').first().scrollIntoViewIfNeeded();
    await page.screenshot({path:path.join(screenshotDir,'rich-response-mobile-chart.png'),fullPage:true});
    await page.setViewportSize({width:1440,height:1000});
    await page.locator('.response-code').first().scrollIntoViewIfNeeded();
    await page.screenshot({path:path.join(screenshotDir,'rich-response-math-code.png'),fullPage:true});
    // Representative bounded long answer and maximum supported chart dimensions.
    const longText='## Longer code example\n\n'+('A bounded paragraph for reading and scrolling. '.repeat(18))+'\n\n```python\n'+('print("A teaching example")\n'.repeat(160))+'```';
    assert(longText.length<6000);
    const largeChart={...blocks()[1],id:'large-chart',chartType:'line',title:'Fifty-row, four-series example',series:['a','b','c','d'].map(key=>({key,label:key.toUpperCase()})),data:Array.from({length:50},(_,i)=>({seconds:i,a:i,b:i*2,c:i*3,d:i*4}))};
    messages.set(sessions[1].id,[{id:uid(70),role:'user',turn_number:1,blocks:[{kind:'text',text:'Long example'}]},{id:uid(71),role:'assistant',turn_number:1,blocks:[{id:'long-code',kind:'markdown',text:longText},largeChart]}]);
    await page.reload({waitUntil:'networkidle'});
    const renderStart=Date.now();
    await page.locator('.desktop-sidebar').getByRole('button',{name:'Rich Curiosity answer (curiosity)',exact:true}).click();
    await page.waitForFunction(()=>document.querySelectorAll('.response-code pre code span[style]').length>0 && document.querySelectorAll('.response-chart svg[role="application"]').length===1);
    const longRenderMs=Date.now()-renderStart;
    await page.setViewportSize({width:390,height:900});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    assert(await page.locator('.response-chart').evaluate(el=>el.scrollWidth<=el.clientWidth+1));
    const scripts=await page.evaluate(()=>performance.getEntriesByType('resource').filter(e=>e.name.includes('/_next/static/chunks/')&&e.name.endsWith('.js')).reduce((r,e)=>({count:r.count+1,bytes:r.bytes+e.encodedBodySize}),{count:0,bytes:0}));
    // Fifteen Indian-language choices plus English; wrapping list fits narrow and wide devices.
    for(const width of [320,390,768,1440]){
      await page.setViewportSize({width,height:900});
      await page.getByRole('button',{name:'Answer language: English',exact:true}).click();
      const languages=page.getByRole('group',{name:'Choose answer language',exact:true});
      assert.equal(await languages.getByRole('button').count(),16);
      assert.deepEqual(await languages.getByRole('button').evaluateAll(buttons=>buttons.map(button=>button.getAttribute('aria-label'))),['English','Tamil','Hindi','Malayalam','Kannada','Telugu','Marathi','Bengali','Gujarati','Urdu','Odia','Punjabi','Assamese','Konkani','Manipuri','Sanskrit']);
      const box=await languages.boundingBox();assert(box.x>=0&&box.x+box.width<=width+1);
      assert(await languages.evaluate(el=>el.scrollWidth<=el.clientWidth+1));
      await languages.getByRole('button',{name:'English',exact:true}).focus();await page.keyboard.press('Escape');
      assert.equal(await languages.count(),0);
      assert(await page.getByRole('button',{name:'Answer language: English',exact:true}).evaluate(el=>el===document.activeElement));
    }
    await page.setViewportSize({width:390,height:900});
    await page.getByRole('button',{name:'Answer language: English',exact:true}).click();
    await page.screenshot({path:path.join(screenshotDir,'answer-languages-mobile.png')});
    await page.getByRole('group',{name:'Choose answer language',exact:true}).getByRole('button',{name:'Tamil',exact:true}).click();
    await page.locator('#flame-prompt').fill('Explain gravity in English');
    await page.getByRole('button',{name:'Send learning request',exact:true}).click();
    await page.getByRole('button',{name:'Answer language: Tamil',exact:true}).waitFor({state:'visible'});
    await page.waitForFunction(()=>!document.querySelector('button[aria-label="Answer language: Tamil"]')?.disabled);
    assert.equal(lastAnswerRequest.response_language,'ta');
    assert.equal(lastAnswerRequest.question,'Explain gravity in English','Language selection never edits the saved question');
    await page.reload({waitUntil:'networkidle'});
    await page.getByRole('button',{name:'Answer language: Tamil',exact:true}).waitFor();
    await page.setViewportSize({width:1440,height:900});
    const expand=page.getByRole('button',{name:'Expand sidebar',exact:true});if(await expand.isVisible())await expand.click();
    await page.locator('.desktop-sidebar').getByRole('button',{name:'Rich Curiosity answer (curiosity)',exact:true}).click();
    await page.setViewportSize({width:390,height:900});
    await page.getByRole('button',{name:'Answer language: Tamil',exact:true}).click();
    await page.getByRole('group',{name:'Choose answer language',exact:true}).getByRole('button',{name:'Hindi',exact:true}).click();
    await page.locator('#flame-prompt').fill('ஈர்ப்பு விசை என்றால் என்ன?');
    await page.getByRole('button',{name:'Send learning request',exact:true}).click();
    await page.waitForFunction(()=>!document.querySelector('button[aria-label="Answer language: Hindi"]')?.disabled);
    for(let attempt=0;attempt<100&&lastAnswerRequest?.response_language!=='hi';attempt++)await new Promise(resolve=>setTimeout(resolve,50));
    assert.equal(lastAnswerRequest.response_language,'hi');
    await page.waitForFunction(()=>!document.querySelector('button[aria-label="Answer language: Hindi"]')?.disabled);
    assert.equal(lastAnswerRequest.question,'ஈர்ப்பு விசை என்றால் என்ன?');
    await page.getByRole('button',{name:'Answer language: Hindi',exact:true}).click();
    const languageAudit=await new AxeBuilder({page}).include('.prompt-form').withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
    assert.deepEqual(languageAudit.violations.map(v=>v.id),[]);
    await page.getByRole('group',{name:'Choose answer language',exact:true}).getByRole('button',{name:'English',exact:true}).click();
    console.log('Response languages: English plus 15 Indian choices, responsive menu, keyboard, persistence and unchanged multilingual question payloads passed');
    await page.emulateMedia({colorScheme:'light'});
    await page.getByRole('button',{name:'Switch to dark mode',exact:true}).click();
    assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
    assert.equal(await page.evaluate(()=>localStorage.getItem('flame.theme')),'dark');
    const themeArtifacts=path.resolve(cwd,'../../../work/theme');fs.mkdirSync(themeArtifacts,{recursive:true});
    for(const width of [1440,390,320]){
      await page.setViewportSize({width,height:900});
      const toggle=page.getByRole('button',{name:'Switch to light mode',exact:true});
      const box=await toggle.boundingBox();assert(box&&box.width>=40&&box.x+box.width<=width&&box.y<30,'Theme toggle must remain at the top right');
      const modes=await page.locator('.flame-topbar .workspace-modes').boundingBox();assert(modes&&modes.x+modes.width<=box.x,'Theme control must not overlap the mode selector');
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Dark layout must not scroll horizontally');
      await page.screenshot({path:path.join(themeArtifacts,'dark-'+width+'.png')});
    }
    const darkAudit=await new AxeBuilder({page}).include('.student-app').withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
    assert.deepEqual(darkAudit.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),[]);
    await page.reload({waitUntil:'networkidle'});
    await page.getByRole('button',{name:'Switch to light mode',exact:true}).waitFor();
    await page.getByRole('button',{name:'Switch to light mode',exact:true}).focus();
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('html').getAttribute('data-theme'),'light');
    await page.reload({waitUntil:'networkidle'});
    await page.getByRole('button',{name:'Switch to dark mode',exact:true}).waitFor();
    console.log('Theme toggle: dark/light, saved preference, keyboard, accessibility, top-right placement and 1440/390/320px layouts passed');
    console.log('F11 browser measurements',JSON.stringify({longAnswerCharacters:longText.length,longRenderMs,loadedScriptResources:scripts}));
    assert.deepEqual(errors,[]);
    console.log('F11 browser passed: Markdown/GFM/math/code/copy, 3 charts/data tables, safety/axe, Study/Curiosity ask, failure/retry, history reload, 1440/900/390px.');
  }finally{if(browser)await browser.close();server.kill();await new Promise(resolve=>mock.close(resolve));}
})().catch(error=>{console.error(error);process.exitCode=1;});
