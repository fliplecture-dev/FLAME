/* Detached local development session; no Windows startup/service registration. */
const fs=require('node:fs'),path=require('node:path');
const {spawn}=require('node:child_process');
const {randomUUID}=require('node:crypto');
const web=path.resolve(__dirname,'..');
const directory=path.resolve(web,'../../../work');
const statePath=path.join(directory,'dev-session.json');
const stopPath=path.join(directory,'dev-session.stop');
function running(state){try{process.kill(state.pid,0);return true;}catch{return false;}}
async function main(){
 fs.mkdirSync(directory,{recursive:true});
 let state;try{state=JSON.parse(fs.readFileSync(statePath,'utf8'));}catch{}
 const action=process.argv[2]??'start';
 if(!['start','stop','status'].includes(action))throw Error('Use start, stop or status.');
 if(state&&!running(state)){fs.unlinkSync(statePath);state=null;}
 if(action==='status'){
  console.log(state?'[FLAME] Background launcher is running (PID '+state.pid+').':'[FLAME] Background session is stopped.');return;
 }
 if(action==='stop'){
  if(!state){console.log('[FLAME] Background session is already stopped.');return;}
  fs.writeFileSync(stopPath,state.token);
  for(let i=0;i<100&&fs.existsSync(statePath);i++)await new Promise(r=>setTimeout(r,200));
  if(fs.existsSync(statePath))throw Error('Stop request is pending. Check work/dev-session.stderr.log.');
  console.log('[FLAME] Background session stopped.');return;
 }
 if(state){console.log('[FLAME] Background session already running; no duplicate servers started.');return;}
 const token=randomUUID();
 // Reserve the session before launching so two starts cannot race.
 fs.writeFileSync(statePath,JSON.stringify({pid:process.pid,token}),{flag:'wx'});
 const out=fs.openSync(path.join(directory,'dev-session.stdout.log'),'a');
 const err=fs.openSync(path.join(directory,'dev-session.stderr.log'),'a');
 try{
  const child=spawn(process.execPath,[path.join(__dirname,'dev.cjs'),'--background-session',token],
   {cwd:web,detached:true,windowsHide:true,stdio:['ignore',out,err]});
  await new Promise((resolve,reject)=>{child.once('spawn',resolve);child.once('error',reject);});
  fs.writeFileSync(statePath,JSON.stringify({pid:child.pid,token}));
  child.unref();
 }catch(e){fs.unlinkSync(statePath);throw e;}finally{fs.closeSync(out);fs.closeSync(err);}
 console.log('[FLAME] Independent background session started. API 8000; web 3000 after readiness.');
 console.log('[FLAME] Logs: work/dev-session.stdout.log and work/dev-session.stderr.log');
 console.log('[FLAME] Stop: ./Start-FLAME.ps1 stop; status: ./Start-FLAME.ps1 status');
}
main().catch(e=>{console.error('[FLAME] '+e.message);process.exitCode=1;});
