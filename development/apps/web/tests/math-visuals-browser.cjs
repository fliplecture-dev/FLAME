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
const base = 'http://localhost:3116';
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
function blocks() { return [{id:'intro',kind:'markdown',text:'**Interactive mathematics** with $$x^2$$.'},...Object.keys(templates).map(mathBlock),{id:'legacy',kind:'text',text:'Legacy text remains readable.'}]; }
const messages = new Map(sessions.map(session=>[session.id,[{id:uid(20),role:'user',turn_number:1,blocks:[{kind:'text',text:session.first_question}]},{id:uid(21),role:'assistant',turn_number:1,blocks:blocks()}]]));
const json = (res,value,status=200)=>{res.writeHead(status,{'content-type':'application/json'});res.end(JSON.stringify(value));};
const body = async req=>{const chunks=[];for await(const chunk of req)chunks.push(chunk);return JSON.parse(Buffer.concat(chunks).toString()||'{}');};
let asks=0, failNext=false;
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
  await new Promise(resolve=>mock.listen(0,'127.0.0.1',resolve));
  const server=spawn(process.execPath,[path.join(cwd,'node_modules/next/dist/bin/next'),'start','-p','3116'],{cwd,windowsHide:true,env:{...process.env,FLAME_NEXT_DIST_DIR:process.env.FLAME_TEST_NEXT_DIST_DIR||'.next-f11',FLAME_API_URL:`http://127.0.0.1:${mock.address().port}`,FLAME_BFF_SHARED_KEY:'rich-test-secret',FLAME_WEB_ORIGIN:base}});
  let log='',browser;
  server.stdout.on('data',data=>log+=data);server.stderr.on('data',data=>log+=data);
  try{
    let ready=false;
    for(let i=0;i<60;i++){try{if((await fetch(base+'/sign-in')).ok){ready=true;break;}}catch{}await new Promise(resolve=>setTimeout(resolve,500));}
    assert(ready,log);
    browser=await chromium.launch({channel:'msedge',headless:true});
    const context=await browser.newContext({viewport:{width:1440,height:1000},hasTouch:true});
    await context.addCookies([{name:'flame_session',value:'rich-test-session',url:base,httpOnly:true}]);
    const page=await context.newPage(),errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.goto(base,{waitUntil:'networkidle'});
    const started=Date.now();
    await page.locator('.desktop-sidebar').getByRole('button',{name:'Falling objects (study)',exact:true}).click();
    await page.waitForFunction(()=>document.querySelectorAll('.math-activity').length===17 && document.querySelectorAll('.math-geometry-board svg').length===7 && document.querySelectorAll('.math-activity .MafsView').length===4 && document.querySelectorAll('.math-activity canvas').length>=6);
    console.log('F12 all-engine mount ms',Date.now()-started);
    assert.equal(await page.locator('.flame-message > .message-author').count(),0,'Response must show only the flame icon');
    const activity=template=>page.locator(`.math-activity[data-template="${template}"]`);
    const fraction=activity('fraction_bar');
    await fraction.getByLabel('Shaded parts',{exact:true}).fill('2');
    assert((await fraction.locator('.math-activity-state').innerText()).includes('2 of 4'));
    await fraction.getByLabel('Equal parts',{exact:true}).fill('1');
    assert((await fraction.locator('.math-activity-state').innerText()).includes('1 of 1'));
    await fraction.getByRole('button',{name:'Reset activity',exact:true}).click();
    assert((await fraction.locator('.math-activity-state').innerText()).includes('3 of 4'));
    await fraction.getByRole('button',{name:'Expand activity',exact:true}).focus();
    await fraction.getByRole('button',{name:'Expand activity',exact:true}).press('Enter');
    assert.equal(await fraction.locator('.math-activity-drawing').evaluate(el=>el.clientHeight),438);
    await fraction.getByRole('button',{name:'Restore activity',exact:true}).click();
    await activity('counting_groups').getByLabel('Objects',{exact:true}).fill('40');
    assert((await activity('counting_groups').locator('.math-activity-state').innerText()).includes('40 objects'));
    await activity('shape_explorer').getByLabel('Shape',{exact:true}).selectOption('triangle');
    await activity('number_line').getByLabel('Position',{exact:true}).fill('7');
    await activity('ruler_measurement').getByLabel('Length',{exact:true}).fill('7.5');
    const triangle=activity('triangle_angles');
    await triangle.getByLabel('C y',{exact:true}).fill('4');
    assert((await triangle.locator('.math-activity-state').innerText()).includes('Sum 180°'));
    await triangle.getByLabel('C y',{exact:true}).fill('-2');
    assert((await triangle.locator('.math-activity-state').innerText()).includes('collinear'));
    await triangle.getByRole('button',{name:'Reset activity',exact:true}).click();
    await triangle.scrollIntoViewIfNeeded();
    const vertex=triangle.locator('svg ellipse[fill="#345c9c"]:visible').first();
    await vertex.waitFor({state:'visible'});
    const vertexBox=await vertex.boundingBox();assert(vertexBox);
    await page.mouse.move(vertexBox.x+vertexBox.width/2,vertexBox.y+vertexBox.height/2);
    await page.mouse.down();await page.mouse.move(vertexBox.x+vertexBox.width/2+35,vertexBox.y+vertexBox.height/2-20,{steps:8});await page.mouse.up();
    assert.notEqual(await triangle.getByLabel('A x',{exact:true}).inputValue(),'-3','Dragging a geometry point must update its coordinates');
    await triangle.getByRole('button',{name:'Reset activity',exact:true}).click();
    const linear=activity('linear_function');
    await linear.getByLabel('Slope m',{exact:true}).fill('2');
    await linear.getByLabel('Intercept b',{exact:true}).fill('1');
    await linear.getByRole('slider',{name:'Slope m slider',exact:true}).focus();
    await linear.getByRole('slider',{name:'Slope m slider',exact:true}).press('ArrowRight');
    assert.equal(await linear.getByLabel('Slope m',{exact:true}).inputValue(),'2.5');
    await linear.getByLabel('Slope m',{exact:true}).fill('2');
    assert((await linear.locator('.math-activity-state').innerText()).includes('y = 2x + 1'));
    assert((await linear.locator('.math-activity-state').innerText()).includes('y = 3'));
    await activity('quadratic_function').getByLabel('Quadratic coefficient a',{exact:true}).fill('-2');
    const trig=activity('trigonometric_function');
    await trig.getByLabel('Function',{exact:true}).selectOption('cos');
    await trig.getByLabel('Amplitude a',{exact:true}).fill('2');
    await trig.getByLabel('Vertical shift d',{exact:true}).fill('1');
    assert((await trig.locator('.math-activity-state').innerText()).includes('y = 3'));
    assert((await trig.locator('.math-activity-state').innerText()).includes('radians'));
    const movable=activity('coordinate_points').locator('[tabindex="0"]').last();
    await movable.focus();await movable.press('ArrowRight');
    const axe=await new AxeBuilder({page}).include('.learning-content').withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
    assert.deepEqual(axe.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)})),[]);
    const screenshots=path.resolve(cwd,'../../..','work/f12');fs.mkdirSync(screenshots,{recursive:true});
    for(const template of ['fraction_bar','triangle_angles','linear_function','trigonometric_function']){
      await activity(template).scrollIntoViewIfNeeded();
      await activity(template).screenshot({path:path.join(screenshots,template+'-desktop.png')});
    }
    for(const width of [900,390]){
      await page.setViewportSize({width,height:1000});
      await page.waitForTimeout(150);
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Page overflow ${width}`);
      assert(await page.locator('.math-activity').evaluateAll(els=>els.every(el=>el.scrollWidth<=el.clientWidth+1)),`Activity overflow ${width}`);
    }
    await fraction.scrollIntoViewIfNeeded();
    const canvas=fraction.locator('canvas').first();
    const box=await canvas.boundingBox();assert(box);
    const scale=Math.min(box.width/600,box.height/300);
    await canvas.tap({position:{x:(box.width-600*scale)/2+502.5*scale,y:box.height/2}});
    assert((await fraction.locator('.math-activity-state').innerText()).includes('4 of 4'),'Touch state: '+await fraction.locator('.math-activity-state').innerText());
    await activity('fraction_circle').screenshot({path:path.join(screenshots,'fraction-circle-mobile.png')});
    // Reload restores saved initial parameters, not local changes.
    await page.setViewportSize({width:1440,height:1000});
    await page.reload({waitUntil:'networkidle'});
    await page.locator('.desktop-sidebar').getByRole('button',{name:'Falling objects (study)',exact:true}).click();
    await fraction.getByLabel('Shaded parts',{exact:true}).waitFor();
    assert.equal(await fraction.getByLabel('Shaded parts',{exact:true}).inputValue(),'3');
    const input=page.locator('#flame-prompt');
    await input.fill('Explore another activity');await page.getByRole('button',{name:'Send learning request',exact:true}).click();
    await page.waitForFunction(()=>document.querySelectorAll('.math-activity').length===34);
    // A failed lazy engine download must leave the controls and description usable.
    const chunks=path.join(cwd,process.env.FLAME_TEST_NEXT_DIST_DIR||'.next-f11','static/chunks');
    const mafsChunk=fs.readdirSync(chunks).find(name=>name.endsWith('.js')&&fs.readFileSync(path.join(chunks,name),'utf8').includes('MafsView'));
    assert(mafsChunk);
    const failedContext=await browser.newContext({viewport:{width:1200,height:1000}});
    await failedContext.addCookies([{name:'flame_session',value:'rich-test-session',url:base,httpOnly:true}]);
    await failedContext.route('**/'+mafsChunk,route=>route.abort());
    const failedPage=await failedContext.newPage();await failedPage.goto(base,{waitUntil:'networkidle'});
    await failedPage.locator('.desktop-sidebar').getByRole('button',{name:'Rich Curiosity answer (curiosity)',exact:true}).click();
    const failedActivity=failedPage.locator('.math-activity[data-template="linear_function"]').first();
    await failedActivity.getByText('The drawing is unavailable.',{exact:false}).waitFor();
    await failedActivity.getByLabel('Slope m',{exact:true}).fill('3');
    assert((await failedActivity.locator('.math-activity-state').innerText()).includes('y = 3x'));
    await failedContext.close();
    failNext=true;await input.fill('Try this again');await page.getByRole('button',{name:'Send learning request',exact:true}).click();
    await page.getByRole('button',{name:'Retry question',exact:true}).click();
    await page.waitForFunction(()=>document.querySelectorAll('.math-activity').length===51);
    assert.equal(asks,3);
    // Switching sessions exercises full engine unmount/reinitialization.
    for(let i=0;i<2;i++){
      await page.locator('.desktop-sidebar').getByRole('button',{name:'Rich Curiosity answer (curiosity)',exact:true}).click();
      await page.waitForFunction(()=>document.querySelectorAll('.math-activity').length===17);
      await page.locator('.desktop-sidebar').getByRole('button',{name:'Falling objects (study)',exact:true}).click();
      await page.waitForFunction(()=>document.querySelectorAll('.math-activity').length===51);
    }
    await page.locator('.desktop-sidebar').getByRole('button',{name:'Rich Curiosity answer (curiosity)',exact:true}).click();
    await input.fill('Show a fraction');await page.getByRole('button',{name:'Send learning request',exact:true}).click();
    await page.waitForFunction(()=>document.querySelectorAll('.math-activity').length===34);
    assert.deepEqual(errors,[]);
    console.log('F12 browser passed: 17 templates / 3 engines, controls/reset/expand, invariants/degeneracy, keyboard, axe, 1440/900/390px, history/retry/Study/Curiosity, repeated cleanup.');
  }finally{if(browser)await browser.close();server.kill();mock.closeAllConnections();await new Promise(resolve=>mock.close(resolve));}
})().catch(error=>{console.error(error);process.exitCode=1;});
