// Production Next/BFF with synthetic API. No real accounts, messages or provider calls.
const assert=require('node:assert/strict'),http=require('node:http'),path=require('node:path'),fs=require('node:fs');
const {spawn}=require('node:child_process');
const root=process.env.FLAME_UI_TOOLS||path.resolve(__dirname,'../../../../.kilo/ui-check/node_modules');
const {chromium}=require(path.join(root,'playwright')),AxeBuilder=require(path.join(root,'@axe-core/playwright')).default;
const cwd=path.resolve(__dirname,'..'),base='http://localhost:3134',output=path.resolve(cwd,'../../../work/access');fs.mkdirSync(output,{recursive:true});
const uid=n=>`${String(n).padStart(8,'0')}-1111-4111-8111-111111111111`;
const guests=new Map(),answered=new Map();let loginPhone=null,registered=null,memberUsed=0,failProfile=false,guestNumber=0;
let profile={display_name:'Student',email:'student@example.test',phone_number:null,contact_number:null,address:null,city:null,state:null,country:null,pincode:null};
const json=(res,data,status=200)=>{res.writeHead(status,{'content-type':'application/json'});res.end(JSON.stringify(data));};
const mock=http.createServer(async(req,res)=>{let route=new URL(req.url,'http://fixture').pathname.replace('/api/v1/',''),body={};if(req.method!=='GET'){let raw='';for await(const c of req)raw+=c;if(raw)body=JSON.parse(raw);}
  if(req.headers['x-bff-key']!=='policy-secret')return json(res,{},403);
  if(route==='catalogue')return json(res,{items:[],total:0,inventory_total:0,offset:0,limit:24,facets:{}});
  if(route==='auth/register'){registered=body;return json(res,{status:'verification_pending'});}
  if(route==='auth/login'){loginPhone=body.phone_number;if(loginPhone)profile.phone_number=loginPhone;return json(res,{session:'policy-member'});}
  if(route==='guest/identity'){const token='policy-guest-'+(++guestNumber);guests.set(token,{used:0,id:uid(100+guestNumber)});return json(res,{token},201);}
  const guestRoute=route.startsWith('guest/'),guest=guests.get(req.headers['x-flame-guest']);
  if(guestRoute){if(!guest)return json(res,{},401);route=route.slice(6);}else if(req.headers['x-flame-session']!=='policy-member')return json(res,{},401);
  if(route==='me')return json(res,guestRoute?{role:'guest'}:{id:uid(1),role:'member',display_name:profile.display_name,email:profile.email});
  if(route==='usage'||route==='me/usage'){const limit=guestRoute?10:25,used=guestRoute?guest.used:memberUsed;return json(res,{limit,used,remaining:Math.max(0,limit-used),timezone:'Asia/Kolkata',resets_at:'2026-10-18T18:30:00Z'});}
  if(route==='me/profile'){if(req.method==='PATCH'){if(failProfile)return json(res,{},503);profile={...profile,...body};}return json(res,profile);}
  if(route==='curricula'||route==='me/learning'||route==='sessions'&&req.method==='GET')return json(res,{items:[],next_cursor:null});
  if(route==='me/activity')return json(res,{status:'ok'});
  if(route==='sessions')return json(res,{id:guestRoute?guest.id:uid(2)},201);
  if(route.endsWith('/capability-check'))return json(res,{status:'continue'});
  if(route.endsWith('/ask-stream'))return json(res,{},404);
  if(route.endsWith('/ask')){
    const identity=guestRoute?req.headers['x-flame-guest']:'member',key=identity+':'+req.headers['idempotency-key'];if(answered.has(key))return json(res,answered.get(key));
    if(guestRoute&&body.mode!=='curiosity')return json(res,{},403);
    if((guestRoute?guest.used:memberUsed)>=(guestRoute?10:25))return json(res,{error:{code:'daily_limit_reached'}},429);
    if(guestRoute)guest.used++;else memberUsed++;
    const answer={status:'ok',route:'direct_llm',knowledge_source:'model_generated',grounded:false,message_id:uid(answered.size+10),blocks:[{kind:'text',text:'Explanation for '+body.question}]};answered.set(key,answer);return json(res,answer);
  }
  if(route.endsWith('/simulation'))return json(res,{status:'ineligible'});
  if(route.endsWith('/recommendations'))return json(res,{status:'no_results',resources:[],teachers:[],kits:[]});
  if(route==='explore/summary')return json(res,{videos:0,images:0,interactives:0});
  return json(res,{},404);
});
(async()=>{await new Promise(r=>mock.listen(0,'127.0.0.1',r));const server=spawn(process.execPath,[path.join(cwd,'node_modules/next/dist/bin/next'),'start','-p','3134'],{cwd,windowsHide:true,env:{...process.env,FLAME_NEXT_DIST_DIR:'.next-discovery',FLAME_BFF_SHARED_KEY:'policy-secret',FLAME_API_URL:`http://127.0.0.1:${mock.address().port}`,FLAME_WEB_ORIGIN:base}});server.stdout.resume();server.stderr.resume();let browser;
try{let ready=false;for(let i=0;i<60;i++){try{if((await fetch(base)).ok){ready=true;break;}}catch{}await new Promise(r=>setTimeout(r,500));}assert(ready);browser=await chromium.launch({channel:'msedge',headless:true});const context=await browser.newContext({viewport:{width:1440,height:900}}),page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  async function checkAllowance(text) {
    assert.equal(await page.locator('#learning-workspace .question-allowance').count(),0);
    await page.getByLabel('Open profile details',{exact:true}).click();
    await page.locator('.profile-popover').getByText(text,{exact:false}).waitFor();
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('.question-allowance:visible').count(),0);
  }
  for(const kind of ['books','kits','teachers','classes']){await page.goto(base+'/search?kind='+kind,{waitUntil:'networkidle'});await page.getByRole('heading',{name:`No ${kind} listed yet`}).waitFor();assert.equal(new URL(page.url()).pathname,'/search');}
  await page.goto(base);await page.getByLabel('Ask FLAME a question or learning request').fill('Guest question 1');await page.getByRole('button',{name:'Send learning request',exact:true}).click();await page.getByText('Explanation for Guest question 1',{exact:true}).waitFor();assert.equal(new URL(page.url()).pathname,'/flame');assert.equal(await page.locator('.workspace-modes').getByRole('button',{name:'Curiosity',exact:true}).getAttribute('aria-pressed'),'true');await checkAllowance('9 of 10 questions left today');
  const cookies=await context.cookies();const capability=cookies.find(c=>c.name==='flame_guest');assert(capability?.httpOnly&&capability.sameSite==='Lax');assert(!cookies.some(c=>c.name==='flame_session'));
  const prompt=page.getByLabel('Ask FLAME a question or learning request');for(let i=2;i<=10;i++){await prompt.fill('Guest question '+i);await page.getByRole('button',{name:'Send learning request',exact:true}).click();await page.getByText('Explanation for Guest question '+i,{exact:true}).waitFor();}
  await checkAllowance('0 of 10 questions left today');await prompt.fill('Keep question 11');await page.getByRole('button',{name:'Send learning request',exact:true}).click();await page.getByText(/allowance resets at midnight India time/).waitFor();assert.equal(await prompt.inputValue(),'Keep question 11');assert.equal([...guests.values()][0].used,10);
  await page.screenshot({path:path.join(output,'guest-limit-desktop.png')});
  const csrf=(await (await page.request.get(base+'/api/auth/csrf')).json()).csrf;
  const bad=await page.request.patch(base+'/api/me/profile',{headers:{origin:base,'x-flame-csrf':csrf},data:{city:'Wrong'}});assert.equal(bad.status(),401);
  const bypass=await page.request.post(base+'/api/guest/admin/students',{headers:{origin:base,'x-flame-csrf':csrf},data:{}});assert.equal(bypass.status(),404);
  const noCsrf=await page.request.post(base+'/api/auth/guest');assert.equal(noCsrf.status(),403);
  await page.locator('.workspace-modes').getByRole('button',{name:'Study',exact:true}).click();await page.waitForURL('**/sign-in?next=*');assert(new URL(page.url()).searchParams.get('next').includes('mode=study'));const optional=page.getByLabel('Phone number (optional)',{exact:true});assert.equal(await optional.getAttribute('required'),null);await page.goBack();await page.getByLabel('Ask FLAME a question or learning request').waitFor();assert.equal(await prompt.inputValue(),'Keep question 11');await page.getByLabel('Open profile details',{exact:true}).click();await page.getByRole('link',{name:'Sign in for 25 questions and Study',exact:true}).click();await page.waitForURL('**/sign-in?next=*');
  await page.getByLabel('Email',{exact:true}).fill('student@example.test');await page.getByLabel('Password',{exact:true}).fill('test-password');await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.waitForURL('**/flame');await page.getByText('Explanation for Keep question 11',{exact:true}).waitFor();assert.equal(memberUsed,1);assert.equal(loginPhone,null);assert.equal((await page.request.get(base+'/api/guest/usage')).status(),403);await checkAllowance('24 of 25 questions left today');await page.locator('.workspace-modes').getByRole('button',{name:'Study',exact:true}).click();assert.equal(await page.locator('.workspace-modes').getByRole('button',{name:'Study',exact:true}).getAttribute('aria-pressed'),'true');
  // Exercise the account menu against synthetic accounts; never submit deletion.
  for(const width of [1440,900,390,320]) {
    await page.setViewportSize({width,height:900});
    if(width<768) await page.getByRole('button',{name:'Open navigation',exact:true}).click();
    const menu=page.locator('.sidebar-account .profile-section');
    await menu.locator('summary').click();
    await menu.getByRole('link',{name:'Student profile',exact:true}).waitFor();
    await menu.getByRole('button',{name:'Sign out',exact:true}).waitFor();
    await menu.getByRole('button',{name:'Delete account',exact:true}).click();
    assert(await menu.getByRole('button',{name:'Cancel',exact:true}).evaluate(el=>el===document.activeElement));
    await menu.getByRole('button',{name:'Cancel',exact:true}).click();
    assert.equal(await menu.getByRole('group',{name:'Confirm account deletion'}).count(),0);
    for(const theme of ['light','dark']) {
      await page.evaluate(t=>document.documentElement.dataset.theme=t,theme);
      const bounds=await menu.locator('.profile-popover').boundingBox();assert(bounds.x>=0&&bounds.x+bounds.width<=width+1);
      const audit=await new AxeBuilder({page}).include('.profile-popover').withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();assert.deepEqual(audit.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)})),[]);
      if(width!==320)await page.screenshot({path:path.join(output,`account-menu-${theme}-${width}.png`)});
    }
    await page.keyboard.press('Escape');assert.equal(await menu.getAttribute('open'),null);
    assert(await menu.locator('summary').evaluate(el=>el===document.activeElement));
    if(width<768) await page.getByRole('button',{name:'Close navigation',exact:true}).click();
  }
  await page.goto(base+'/profile',{waitUntil:'networkidle'});await page.getByRole('heading',{name:'Student profile'}).waitFor();await page.getByLabel('Display name',{exact:true}).fill('Updated student');const values={'Phone number (optional)':'+91 98765 43210','Contact number (optional)':'044 2345 6789','Address (optional)':'12 Learning Road','City (optional)':'Chennai','State (optional)':'Tamil Nadu','Country (optional)':'India','Pincode / postal code (optional)':'600001'};for(const [name,value] of Object.entries(values))await page.getByLabel(name,{exact:true}).fill(value);
  failProfile=true;await page.getByRole('button',{name:'Save profile',exact:true}).click();await page.getByRole('alert').waitFor();assert.equal(await page.getByLabel('City (optional)',{exact:true}).inputValue(),'Chennai');failProfile=false;await page.getByRole('button',{name:'Save profile',exact:true}).click();await page.getByText('Your profile has been saved.',{exact:true}).waitFor();await page.reload({waitUntil:'networkidle'});assert.equal(await page.getByLabel('Phone number (optional)',{exact:true}).inputValue(),'+91 98765 43210');assert.equal(await page.getByLabel('Country (optional)',{exact:true}).inputValue(),'India');assert.equal(await page.getByLabel('Email',{exact:true}).getAttribute('readonly'),'');
  for(const width of [1440,390,320]){await page.setViewportSize({width,height:900});for(const theme of ['light','dark']){await page.evaluate(t=>document.documentElement.dataset.theme=t,theme);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));const audit=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();assert.deepEqual(audit.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)})),[]);if(width===390)await page.screenshot({path:path.join(output,`profile-${theme}-mobile.png`)});}}
  await page.getByLabel('Phone number (optional)',{exact:true}).fill('');await page.getByLabel('Address (optional)',{exact:true}).fill('');await page.getByRole('button',{name:'Save profile',exact:true}).click();await page.getByText('Your profile has been saved.',{exact:true}).waitFor();assert.equal(profile.phone_number,null);assert.equal(profile.address,null);
  await page.goto(base+'/sign-in');await page.getByLabel('Email',{exact:true}).fill('student@example.test');await page.getByLabel('Password',{exact:true}).fill('test-password');await page.getByLabel('Phone number (optional)',{exact:true}).fill('+91 98765 43210');await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.waitForURL(base+'/');assert.equal(loginPhone,'+91 98765 43210');
  const anonymous=await browser.newContext({viewport:{width:390,height:900}}),registration=await anonymous.newPage();await registration.goto(base+'/profile');await registration.waitForURL('**/sign-in?next=%2Fprofile');await registration.goto(base+'/sign-up');await registration.getByLabel('Display name',{exact:true}).fill('New student');await registration.getByLabel('Email',{exact:true}).fill('new@example.test');await registration.getByLabel('Password',{exact:true}).fill('long-test-password');await registration.getByLabel('Phone number (optional)',{exact:true}).fill('+91 98765 43210');await registration.getByRole('button',{name:'Create account',exact:true}).click();await registration.getByRole('status').waitFor();assert.equal(registered.phone_number,'+91 98765 43210');await anonymous.close();
  assert.deepEqual(errors,[]);console.log('PASS: public catalogues, guest Curiosity/10-question cap/draft retention, HttpOnly capability and BFF guards, Study sign-in, optional phone, 25-question allowance, private profile save/reload/clear/failure recovery and responsive light/dark accessibility.');
}finally{await browser?.close();server.kill();mock.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
