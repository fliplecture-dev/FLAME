// Real production UI/BFF, synthetic local catalogue/API. No live accounts or provider/database writes.
const assert=require('node:assert/strict'),http=require('node:http'),path=require('node:path'),fs=require('node:fs');
const {spawn}=require('node:child_process');
const toolRoot=process.env.FLAME_UI_TOOLS||path.resolve(__dirname,'../../../../.kilo/ui-check/node_modules');
const {chromium}=require(path.join(toolRoot,'playwright'));
const AxeBuilder=require(path.join(toolRoot,'@axe-core/playwright')).default;
const cwd=path.resolve(__dirname,'..'),base='http://localhost:3128';
const uid=n=>`${String(n).padStart(8,'0')}-1111-4111-8111-111111111111`;
const output=path.resolve(cwd,'../../../work/discovery');fs.mkdirSync(output,{recursive:true});
const items=Array.from({length:30},(_,index)=>({id:uid(index+1),kind:'books',version:1,title:`Fraction book ${String(index).padStart(2,'0')}`,description:'Visual practice for learning fractions.',category:index%2?'Academic':'Reference',subject:'Mathematics',level:'Grade 5',language:index%2?'Tamil':'English',format:'Paperback',author:'Example author',location:null,schedule:null,availability:'Listed',price:'120.00',currency:'INR'}));
let asks=[],failSearch=false,adminRows=[];
const json=(res,data,status=200)=>{res.writeHead(status,{'content-type':'application/json'});res.end(JSON.stringify(data));};
const mock=http.createServer(async(req,res)=>{
  const url=new URL(req.url,'http://fixture');let route=url.pathname.replace('/api/v1/','');const isGuest=route.startsWith('guest/');
  if(req.headers['x-bff-key']!=='discovery-secret')return json(res,{},403);
  if(route==='catalogue'){
    if(failSearch)return json(res,{error:{message:'Catalogue temporarily unavailable.'}},503);
    const kind=url.searchParams.get('kind')||'books',q=url.searchParams.get('q')||'',category=url.searchParams.get('category'),language=url.searchParams.get('language'),offset=Number(url.searchParams.get('offset')||0);
    if(q==='slow')await new Promise(resolve=>setTimeout(resolve,700));
    const inventory=kind==='books'?items:[];
    const matches=inventory.filter(item=>(q==='slow'||item.title.toLowerCase().includes(q.toLowerCase()))&&(!category||item.category===category)&&(!language||item.language===language));
    return json(res,{items:matches.slice(offset,offset+24),total:matches.length,inventory_total:inventory.length,offset,limit:24,facets:{category:['Academic','Reference'],language:inventory.length?['English','Tamil']:[],subject:inventory.length?['Mathematics']:[],level:inventory.length?['Grade 5']:[],format:inventory.length?['Paperback']:[]}});
  }
  if(route.startsWith('catalogue/books/'))return json(res,items.find(item=>route.endsWith(item.id))||{},items.some(item=>route.endsWith(item.id))?200:404);
  if(route==='auth/login')return json(res,{session:'discovery-session'});
  if(route==='guest/identity')return json(res,{token:'discovery-guest-token'},201);
  if(isGuest){if(req.headers['x-flame-guest']!=='discovery-guest-token')return json(res,{},401);if(route==='guest/me')return json(res,{role:'guest'});if(route==='guest/usage')return json(res,{limit:10,used:asks.filter(a=>a.guest).length,remaining:10-asks.filter(a=>a.guest).length,timezone:'Asia/Kolkata'});route=route.slice(6);}
  if(!isGuest&&!['discovery-session','discovery-admin'].includes(req.headers['x-flame-session']))return json(res,{},401);
  if(route==='me/usage')return json(res,{limit:25,used:asks.filter(a=>!a.guest).length,remaining:25-asks.filter(a=>!a.guest).length,timezone:'Asia/Kolkata'});
  if(route==='me')return json(res,{id:uid(80),role:req.headers['x-flame-session']==='discovery-admin'?'admin':'member',email:'learner@example.test',display_name:'Learner'});
  if(route==='admin/curricula')return json(res,{items:[]});
  if(route.startsWith('admin/catalogue/')){
    if(req.method==='GET')return json(res,{items:adminRows,offset:0,limit:24});
    let raw='';for await(const chunk of req)raw+=chunk;const data=JSON.parse(raw),kind=route.split('/')[2];
    if(route.endsWith('/publication')){const row=adminRows[0];if(data.expected_version!==row.version)return json(res,{},409);row.published=data.published;row.version++;return json(res,row);}
    if(req.method==='POST'){const row={...data,id:uid(100),kind,published:false,version:1};adminRows=[row];return json(res,row,201);}
    const row=adminRows[0];if(data.expected_version!==row.version)return json(res,{},409);Object.assign(row,data,{version:row.version+1,published:false});return json(res,row);
  }
  if(route==='curricula'||route==='me/learning')return json(res,{items:[]});
  if(route==='me/activity')return json(res,{status:'ok'});
  if(route==='sessions'&&req.method==='POST')return json(res,{id:uid(90)});
  if(route==='sessions')return json(res,{items:[],next_cursor:null});
  if(route.endsWith('/capability-check'))return json(res,{status:'continue'});
  if(route.endsWith('/ask-stream'))return json(res,{},404);
  if(route.endsWith('/ask')){let raw='';for await(const chunk of req)raw+=chunk;const body=JSON.parse(raw);asks.push({...body,guest:isGuest});await new Promise(resolve=>setTimeout(resolve,100));const text=body.question==='What is algebra?'?'Algebra uses symbols to represent numbers.':body.question==='Recommend books for algebra'?'Algebra book guidance. '+('Practise one idea at a time. '.repeat(170)):'A clear explanation about fractions.';return json(res,{status:'ok',route:'direct_llm',knowledge_source:'model_generated',grounded:false,message_id:uid(91+asks.length),blocks:[{kind:'text',text}]});}
  if(route.endsWith('/simulation'))return json(res,{status:'ineligible'});
  if(route.endsWith('/recommendations'))return json(res,{status:'no_results',resources:[],teachers:[],kits:[]});
  if(route==='explore/summary')return json(res,{videos:0,images:0,interactives:0});
  return json(res,{},404);
});
async function assertCatalogueFocus(page) {
  for(const theme of ['light','dark'])for(const width of [1440,320])for(const kind of ['books','kits','teachers','classes']){
    await page.setViewportSize({width,height:900});await page.goto(`${base}/search?kind=${kind}`,{waitUntil:'networkidle'});
    await page.evaluate(theme=>document.documentElement.dataset.theme=theme,theme);
    const field=page.getByRole('textbox',{name:`Search ${kind}`,exact:true});
    await field.fill('Fractions');
    const focus=await field.evaluate(input=>{const form=input.closest('form'),inner=getComputedStyle(input),outer=getComputedStyle(form);return {inner:inner.outlineStyle,outer:outer.outlineStyle,width:outer.outlineWidth,radius:outer.borderRadius,active:document.activeElement===input};});
    assert.deepEqual(focus,{inner:'none',outer:'solid',width:'2px',radius:'30px',active:true},`Rounded ${kind} search focus in ${theme} at ${width}px`);
    assert.equal(await field.inputValue(),'Fractions');
    if(kind==='books'&&((theme==='light'&&width===1440)||(theme==='dark'&&width===320)))await page.screenshot({path:path.join(output,`search-focused-${theme}-${width}.png`)});
    await page.keyboard.press('Tab');
    assert(await page.locator('.catalogue-search-form').evaluate(form=>form.contains(document.activeElement)&&document.activeElement.tagName==='BUTTON'&&getComputedStyle(document.activeElement).outlineStyle!=='none'),'Search action retains keyboard focus indication');
    await field.evaluate(input=>input.blur());await page.evaluate(()=>document.activeElement.blur());
    assert.equal(await page.locator('.catalogue-search-form').evaluate(form=>getComputedStyle(form).outlineStyle),'none');
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`Search focus overflow ${kind}/${theme}/${width}`);
  }
}
async function assertSeamlessSearch(page, selector) {
  const field=page.locator(selector),original=await field.inputValue(),viewport=page.viewportSize();
  for(const width of [320,1440]){
    await page.setViewportSize({width,height:900});
    for(const value of ['', 'Explain fractions and recommend learning materials. '.repeat(4)]){
      await field.fill(value);await field.focus();
      for(const focused of [true,false]){
        if(!focused)await field.evaluate(element=>element.blur());
        const surface=await field.evaluate(element=>{const style=getComputedStyle(element);return {background:style.backgroundColor,image:style.backgroundImage};});
        assert.deepEqual(surface,{background:'rgba(0, 0, 0, 0)',image:'none'},`Unified dark search surface at ${width}px, focused=${focused}, empty=${!value}`);
      }
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`Dark search overflow ${width}`);
    }
  }
  await field.fill(original);await field.evaluate(element=>element.blur());await page.setViewportSize(viewport);
}
async function assertBrand(page) {
  const failures=await page.locator('.fliplecture-logo').evaluateAll(logos=>{
    const luminance=rgb=>rgb.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;}).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
    return logos.filter(logo=>logo.getBoundingClientRect().width>0).flatMap(logo=>{
      const image=logo.querySelector('img'),text=logo.querySelector('.fliplecture-logo-text'),bounds=logo.getBoundingClientRect(),issues=[];
      if(!image.complete||image.naturalWidth===0)issues.push('Symbol failed to load');
      if(bounds.left<0||bounds.right>innerWidth+1)issues.push('Logo overflows viewport');
      if(getComputedStyle(text).display!=='none'){
        let surface=text,bg=[];while(surface){const color=getComputedStyle(surface).backgroundColor,channels=color.match(/[\d.]+/g)?.map(Number)||[];if(channels.length===3||channels[3]===1){bg=channels.slice(0,3);break;}surface=surface.parentElement;}
        const fg=getComputedStyle(text).color.match(/[\d.]+/g).slice(0,3).map(Number),a=luminance(fg),b=luminance(bg.length?bg:[255,255,255]);
        if((Math.max(a,b)+.05)/(Math.min(a,b)+.05)<4.5)issues.push('Wordmark contrast below 4.5:1');
      }
      return issues;
    });
  });
  assert.deepEqual(failures,[],'Brand assets fit their surface and have readable text');
}
(async()=>{
  await new Promise(resolve=>mock.listen(0,'127.0.0.1',resolve));
  const server=spawn(process.execPath,[path.join(cwd,'node_modules/next/dist/bin/next'),'start','-p','3128'],{cwd,windowsHide:true,env:{...process.env,FLAME_NEXT_DIST_DIR:'.next-discovery',FLAME_BFF_SHARED_KEY:'discovery-secret',FLAME_API_URL:`http://127.0.0.1:${mock.address().port}`,FLAME_WEB_ORIGIN:base}});
  let browser,log='';server.stdout.on('data',data=>log+=data);server.stderr.on('data',data=>log+=data);
  try {
    let ready=false;for(let index=0;index<60;index++){try{if((await fetch(base)).ok){ready=true;break;}}catch{}await new Promise(resolve=>setTimeout(resolve,500));}assert(ready,log);
    browser=await chromium.launch({channel:'msedge',headless:true});
    const context=await browser.newContext({viewport:{width:1440,height:900}}),page=await context.newPage(),errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.goto(base,{waitUntil:'networkidle'});await page.getByRole('heading',{name:'Fliplecture'}).waitFor();assert.equal(await page.locator('.desktop-sidebar').count(),0);
    await assertBrand(page);assert.equal(await page.locator('link[rel=icon]').getAttribute('href'),'/brand/fliplecture-symbol.svg');await page.screenshot({path:path.join(output,'home-desktop.png')});
    await page.getByRole('button',{name:'Answer language: English',exact:true}).click();await page.getByRole('button',{name:'Tamil',exact:true}).click();
    await page.getByLabel('Ask FLAME a question or learning request').fill('Fraction');
    await page.getByRole('link',{name:'Books',exact:true}).click();await page.getByRole('status').filter({hasText:'30 results'}).waitFor();
    assert.equal(await page.getByRole('textbox',{name:'Search books',exact:true}).inputValue(),'Fraction');
    await page.getByRole('button',{name:'Next',exact:true}).click();await page.getByText('25–30 of 30',{exact:true}).waitFor();
    await page.goBack();await page.getByText('1–24 of 30',{exact:true}).waitFor();
    await page.getByRole('button',{name:'Academic',exact:true}).click();await page.getByRole('status').filter({hasText:'15 results'}).waitFor();
    await page.getByRole('button',{name:'Filters (1)',exact:true}).click();await page.getByLabel('Language',{exact:true}).selectOption('English');await page.getByRole('heading',{name:'No matching books'}).waitFor();
    await page.getByRole('button',{name:'Clear filters',exact:true}).first().click();await page.getByRole('status').filter({hasText:'30 results'}).waitFor();
    await page.screenshot({path:path.join(output,'books-desktop.png')});
    await page.getByRole('button',{name:'View Fraction book 00',exact:true}).click();const detail=page.getByRole('dialog',{name:'Listing details'});await detail.getByRole('heading',{name:'Fraction book 00'}).waitFor();
    await detail.getByRole('button',{name:'Close details',exact:true}).click();await detail.waitFor({state:'hidden'});await page.waitForFunction(()=>document.activeElement?.getAttribute('aria-label')==='View Fraction book 00');
    await page.getByRole('button',{name:'View Fraction book 00',exact:true}).click();await detail.getByRole('heading',{name:'Fraction book 00'}).waitFor();
    await detail.getByLabel('Ask FLAME about this book').fill('Would this help me practise?');await detail.getByRole('button',{name:'Ask FLAME',exact:true}).click();
    await page.getByText('A clear explanation about fractions.',{exact:true}).waitFor();assert.equal(asks.length,1);assert.equal(asks[0].guest,true);await page.locator('.workspace-modes').getByRole('button',{name:'Study',exact:true}).click();await page.waitForURL('**/sign-in?next=*');await assertBrand(page);
    await page.getByLabel('Email',{exact:true}).fill('learner@example.test');await page.getByLabel('Password',{exact:true}).fill('test-only-password');await page.getByRole('button',{name:'Sign in',exact:true}).click();
    await page.waitForURL('**/flame?mode=study');await page.locator('.workspace-modes').getByRole('button',{name:'Curiosity',exact:true}).click();assert.equal(asks.length,1);assert.equal(asks[0].mode,'curiosity');assert.equal(asks[0].catalogue_item.id,uid(1));assert.equal(asks[0].response_language,'ta');
    assert.equal(await page.evaluate(()=>sessionStorage.getItem('fliplecture.question-intent')),null);
    assert.equal(new URL(page.url()).pathname,'/flame');await assertBrand(page);await page.screenshot({path:path.join(output,'workspace-logo.png')});
    assert.equal(await page.locator('.answer-discovery').count(),0);
    const prompt=page.getByLabel('Ask FLAME a question or learning request');await prompt.fill('What is algebra?');await page.getByRole('button',{name:'Send learning request',exact:true}).click();await page.getByText('Algebra uses symbols to represent numbers.',{exact:true}).waitFor();assert.equal(await page.locator('.answer-discovery').count(),0);
    await prompt.fill('Recommend books for algebra');await page.getByRole('button',{name:'Send learning request',exact:true}).click();await page.locator('.answer-discovery').waitFor();assert.deepEqual(await page.locator('.answer-discovery a').allTextContents(),['Books']);
    await prompt.fill('Keep my draft while browsing');await page.locator('.answer-discovery').scrollIntoViewIfNeeded();const scrollBefore=await page.locator('.workspace-scroll').evaluate(element=>element.scrollTop);const asksBeforeBack=asks.length;
    await page.locator('.answer-discovery').getByRole('link',{name:'Books',exact:true}).click();await page.getByRole('heading',{name:'Books for “Recommend books for algebra”'}).waitFor();await page.goBack();await page.locator('.answer-discovery').waitFor();assert.equal(await page.locator('.workspace-modes').getByRole('button',{name:'Curiosity',exact:true}).getAttribute('aria-pressed'),'true');assert.equal(await prompt.inputValue(),'Keep my draft while browsing');assert.equal(asks.length,asksBeforeBack);const scrollAfter=await page.locator('.workspace-scroll').evaluate(element=>({top:element.scrollTop,height:element.scrollHeight,client:element.clientHeight}));assert(Math.abs(scrollAfter.top-Math.min(scrollBefore,scrollAfter.height-scrollAfter.client))<5,'Back restores the response scroll position within the available content');
    await page.getByRole('link',{name:'Fliplecture home',exact:true}).first().click();await page.getByRole('heading',{name:'Fliplecture'}).waitFor();
    await page.getByRole('link',{name:'Kits',exact:true}).click();await page.getByRole('heading',{name:'No kits listed yet'}).waitFor();
    for(const label of ['Teachers','Classes']){await page.getByRole('link',{name:label,exact:true}).click();await page.getByRole('heading',{name:`No ${label.toLowerCase()} listed yet`}).waitFor();}
    failSearch=true;await page.getByRole('link',{name:'Books',exact:true}).click();await page.locator('.catalogue-empty[role=alert]').waitFor();failSearch=false;await page.getByRole('button',{name:'Try again',exact:true}).click();await page.getByRole('status').filter({hasText:'30 results'}).waitFor();
    await page.getByRole('textbox',{name:'Search books',exact:true}).fill('slow');const slow=page.waitForRequest(request=>request.url().includes('/api/catalogue?')&&request.url().includes('q=slow'));await page.getByRole('button',{name:'Search books',exact:true}).click();await slow;
    await page.getByRole('textbox',{name:'Search books',exact:true}).fill('Fraction book 29');await page.getByRole('button',{name:'Search books',exact:true}).click();await page.getByRole('status').filter({hasText:'1 result'}).waitFor();await page.waitForTimeout(800);assert.equal(await page.locator('.catalogue-card h2').textContent(),'Fraction book 29');
    for(const width of [1440,768,390,320]){
      await page.setViewportSize({width,height:900});await page.goto(base,{waitUntil:'networkidle'});
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`Home overflow ${width}`);
      const aligned=await page.locator('.prompt-tools > .icon-button').evaluateAll(buttons=>buttons.every(button=>{const a=button.getBoundingClientRect(),b=button.querySelector('svg').getBoundingClientRect();return Math.abs(a.x+a.width/2-b.x-b.width/2)<1&&Math.abs(a.y+a.height/2-b.y-b.height/2)<1;}));assert(aligned,`Composer icons centred ${width}`);await assertBrand(page);
      const audit=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();assert.deepEqual(audit.violations.map(item=>({id:item.id,nodes:item.nodes.map(n=>n.target)})),[]);
      if(width===390)await page.screenshot({path:path.join(output,'home-mobile.png')});
      await page.getByRole('link',{name:'Books',exact:true}).click();await page.getByRole('status').filter({hasText:'30 results'}).waitFor();assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`Search overflow ${width}`);await assertBrand(page);
      const resultsAudit=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();assert.deepEqual(resultsAudit.violations.map(item=>({id:item.id,nodes:item.nodes.map(n=>n.target)})),[]);
      if(width===390)await page.screenshot({path:path.join(output,'books-mobile.png')});
    }
    await page.getByRole('button',{name:/Switch to dark/}).click();await assertSeamlessSearch(page,'.catalogue-search-form input');await assertBrand(page);await page.screenshot({path:path.join(output,'books-dark-mobile.png')});
    const darkAudit=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();assert.deepEqual(darkAudit.violations.map(item=>item.id),[]);
    await page.goto(base,{waitUntil:'networkidle'});await assertSeamlessSearch(page,'.home-composer textarea');await assertBrand(page);await page.screenshot({path:path.join(output,'home-dark-mobile.png')});await page.setViewportSize({width:1440,height:900});await assertBrand(page);await page.screenshot({path:path.join(output,'home-dark-desktop.png')});
    const admin=await browser.newContext({viewport:{width:1440,height:900}});await admin.addCookies([{name:'flame_session',value:'discovery-admin',url:base,httpOnly:true}]);const adminPage=await admin.newPage();await adminPage.goto(base+'/admin',{waitUntil:'networkidle'});await assertBrand(adminPage);await adminPage.evaluate(()=>document.documentElement.dataset.theme='dark');await assertBrand(adminPage);
    await adminPage.getByRole('button',{name:'Books',exact:true}).click();await adminPage.getByLabel('Title',{exact:true}).fill('New fractions book');await adminPage.getByLabel('Description',{exact:true}).fill('A practice collection.');await adminPage.getByLabel('Category',{exact:true}).fill('Academic');await adminPage.getByRole('button',{name:'Save draft',exact:true}).click();await adminPage.getByRole('button',{name:'Publish listing',exact:true}).waitFor();assert.equal(adminRows[0].published,false);
    await adminPage.getByLabel('Title',{exact:true}).fill('Updated fractions book');assert(await adminPage.getByRole('button',{name:'Publish listing',exact:true}).isDisabled());await adminPage.getByRole('button',{name:'Save draft',exact:true}).click();await adminPage.waitForFunction(()=>!Array.from(document.querySelectorAll('button')).find(button=>button.textContent==='Publish listing')?.disabled);
    await adminPage.getByRole('button',{name:'Publish listing',exact:true}).click();await adminPage.getByRole('button',{name:'Withdraw listing',exact:true}).waitFor();assert.equal(adminRows[0].published,true);await adminPage.getByRole('button',{name:'Withdraw listing',exact:true}).click();await adminPage.getByRole('button',{name:'Publish listing',exact:true}).waitFor();assert.equal(adminRows[0].published,false);
    await adminPage.getByRole('button',{name:'Classes',exact:true}).click();await adminPage.getByRole('button',{name:'New class',exact:true}).waitFor();await admin.close();
    await assertCatalogueFocus(page);await page.goto(base+'/about');await assertBrand(page);await page.getByText('FLAME is Fliplecture’s agentic model engine, developed by Fliplecture.',{exact:true}).waitFor();
    await page.goto(base+'/learn');await page.waitForURL('**/flame');
    assert.deepEqual(errors,[]);console.log('PASS: public home, catalogue queries/filters/paging/Back, details, sign-in intent, one item-aware Curiosity answer, empty collections, search recovery, responsive layouts and light/dark accessibility.');
    console.log('PASS: Books draft/publication/withdrawal and Classes admin entry through the real BFF with synthetic records.');
  } finally {await browser?.close();server.kill();mock.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
