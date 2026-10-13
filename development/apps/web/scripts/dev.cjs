/* One local entry point: backend readiness before the frontend can accept requests. */
const path=require('node:path'),fs=require('node:fs'),net=require('node:net');
const {spawn,spawnSync}=require('node:child_process');
const {createHash}=require('node:crypto');
const API_URL='http://127.0.0.1:8000',WEB_URL='http://localhost:3000';
const web=path.resolve(__dirname,'..'),api=path.resolve(web,'../flame-api');
const python=path.join(api,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');

async function health(url,fetcher=fetch){
 try{const r=await fetcher(url,{signal:AbortSignal.timeout(5000)});return r.ok?await r.json():null;}catch{return null;}
}
async function occupied(port){return new Promise(resolve=>{const socket=net.connect(port,'127.0.0.1');socket.setTimeout(1000);socket.once('connect',()=>{socket.destroy();resolve(true);});socket.once('error',()=>resolve(false));socket.once('timeout',()=>{socket.destroy();resolve(false);});});}
async function ready(url,timeoutMs=45000,fetcher=fetch,alive=()=>true){
 const until=Date.now()+timeoutMs;
 do{if(!alive())throw Error('Backend exited before becoming ready. Read its error above.');
  const live=await health(url+'/health/live',fetcher);
  if(live?.service==='flame-api'&&(await health(url+'/health/ready',fetcher))?.checks?.database==='ok')return;
  if(Date.now()>=until)break;
  await new Promise(r=>setTimeout(r,500));
 }while(Date.now()<until);
 throw Error('Backend/database did not become ready. Check the backend .env database connection and network; the frontend was not started.');
}
function stop(child){
 if(!child||child.exitCode!==null)return;
 if(process.platform==='win32')spawnSync('taskkill',['/PID',String(child.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});
 else{try{process.kill(-child.pid,'SIGTERM');}catch{child.kill('SIGTERM');}}
}
class RestartBudget {
 constructor(){this.attempts=[];}
 allow(now=Date.now()){
  this.attempts=this.attempts.filter(time=>now-time<60000);
  if(this.attempts.length>=3)return false;
  this.attempts.push(now);return true;
 }
}
async function main(){
 const sessionIndex=process.argv.indexOf('--background-session');
 if(sessionIndex!==-1){
  const token=process.argv[sessionIndex+1],directory=path.resolve(web,'../../../work');
  const statePath=path.join(directory,'dev-session.json'),stopPath=path.join(directory,'dev-session.stop');
  const cleanup=()=>{try{if(JSON.parse(fs.readFileSync(statePath,'utf8')).token===token)fs.unlinkSync(statePath);}catch{}};
  process.once('exit',cleanup);
  // An authenticated local stop request targets this session, never a reused PID.
  const control=setInterval(()=>{try{if(process.listenerCount('SIGTERM')&&fs.readFileSync(stopPath,'utf8')===token){fs.unlinkSync(stopPath);process.emit('SIGTERM');}}catch{}},250);
  control.unref();
  console.log('[FLAME] Background launcher '+process.pid+' started at '+new Date().toISOString());
 }
 const apiEnv={...process.env}; // Keep backend .env separate from Next's .env.local.
 require('@next/env').loadEnvConfig(web,true);
 if(!fs.existsSync(python))throw Error('Backend virtual environment missing. Follow development/apps/flame-api/README.md setup first.');
 const hash=value=>createHash('sha256').update(value??'').digest('hex');
 const probe=spawnSync(python,['-c',
  'import json,hashlib,os; from app.core.config import Settings; s=Settings(); h=lambda v:hashlib.sha256((v.get_secret_value() if v else "").encode()).hexdigest(); print(json.dumps({"database":bool(s.database_url),"bff":bool(s.bff_shared_key),"encryption":bool(s.session_encryption_key),"bff_matches":h(s.bff_shared_key)==os.environ["FLAME_CHECK_BFF"]}))'],
  {cwd:api,env:{...apiEnv,FLAME_CHECK_BFF:hash(process.env.FLAME_BFF_SHARED_KEY)},encoding:'utf8',windowsHide:true});
 // Never echo configuration validation exceptions: they can contain secret input values.
 if(probe.status!==0)throw Error('Backend configuration could not load. Check required settings in flame-api/.env; credentials were not printed.');
 const config=JSON.parse(probe.stdout);
 if(!config.database||!config.bff||!config.encryption)throw Error('Backend database, BFF shared key and session encryption key are required for local sign-in.');
 if(!config.bff_matches)throw Error('Frontend and backend BFF shared keys differ. Match FLAME_BFF_SHARED_KEY in web/.env.local and flame-api/.env, then restart.');
 if(process.argv.includes('--check')){
  await ready(API_URL,6000);console.log('[FLAME] Configuration matches; API and database ready on 8000.');return;
 }
 if(await occupied(3000))throw Error('Port 3000 is already in use. Stop the previous FLAME dev session before starting another; automatic port switching is disabled.');
 let backend,frontend,timer,shutting=false;
 const recoveryTimers=new Set(), budgets={backend:new RestartBudget(),frontend:new RestartBudget()};
 const shutdown=code=>{if(shutting)return;shutting=true;console.log('[FLAME] Launcher shutting down at '+new Date().toISOString()+' (code '+code+').');clearInterval(timer);for(const t of recoveryTimers)clearTimeout(t);stop(frontend);stop(backend);process.exit(code);};
 function recover(name,start){
  if(shutting)return;
  if(!budgets[name].allow()){
   console.error('[FLAME] '+name+' repeatedly failed. Automatic retries paused; fix the error above and restart npm run dev.');
   // Keep the other server available for diagnosis; never spin on a persistent error.
   return;
  }
  console.warn('[FLAME] '+name+' exited unexpectedly. Restarting in 2 seconds; the other server stays running.');
  const t=setTimeout(()=>{recoveryTimers.delete(t);if(!shutting)start();},2000);recoveryTimers.add(t);
 }
 function startBackend(){
  const args=process.platform==='win32'&&sessionIndex!==-1
   ?[path.join(__dirname,'dev-api.py')]
   :['-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000','--reload','--reload-dir','app','--no-access-log'];
  backend=spawn(python,args,
   {cwd:api,env:{...apiEnv,FLAME_WEB_ORIGIN:WEB_URL,FLAME_RESOURCE_LOCAL_DELIVERY_ORIGIN:API_URL},stdio:'inherit',windowsHide:true,detached:process.platform!=='win32'});
  backend.once('error',()=>recover('backend',startBackend));
  backend.once('exit',()=>recover('backend',startBackend));
 }
 function startFrontend(){
  frontend=spawn(process.execPath,[path.join(web,'node_modules/next/dist/bin/next'),'dev','--hostname','localhost','--port','3000'],
   {cwd:web,env:{...process.env,FLAME_API_URL:API_URL,FLAME_WEB_ORIGIN:WEB_URL},stdio:'inherit',windowsHide:true,detached:process.platform!=='win32'});
  frontend.once('error',()=>recover('frontend',startFrontend));
  frontend.once('exit',()=>recover('frontend',startFrontend));
 }
 process.once('SIGINT',()=>shutdown(0));process.once('SIGTERM',()=>shutdown(0));
 try{
  if(await occupied(8000)){
   if((await health(API_URL+'/health/live'))?.service!=='flame-api')throw Error('Port 8000 belongs to another service. Free it before starting FLAME; no fallback to 8001.');
   console.log('[FLAME] Reusing FLAME API on 8000. Restart that API after backend .env changes.');
  }else{
   console.log('[FLAME] Starting API on 8000…');
   startBackend();
  }
  await ready(API_URL,45000,fetch,()=>!backend||backend.exitCode===null);
  console.log('[FLAME] API/database ready. Starting web on 3000. Local API URL is fixed to 8000.');
  startFrontend();
  // Reloads and temporary dependency outages must not close the student's frontend.
  let failures=0,checking=false,warned=false;
  timer=setInterval(async()=>{if(checking||shutting)return;checking=true;try{
   const live=await health(API_URL+'/health/live');
   if(live?.service==='flame-api'){failures=0;if(warned)console.log('[FLAME] API recovered on 8000.');warned=false;}
   else if(++failures>=3&&!warned){warned=true;console.warn('[FLAME] API temporarily unavailable; web stays running. Backend reload/recovery remains active. Check backend errors if this persists.');}
  }finally{checking=false;}},10000);
 }catch(e){console.error('[FLAME] '+e.message);shutdown(1);}
}
module.exports={API_URL,WEB_URL,health,ready,RestartBudget};
if(require.main===module)main().catch(e=>{console.error('[FLAME] '+e.message);process.exitCode=1;});
