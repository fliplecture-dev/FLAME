// Trusted iframe adapter. Model code NEVER executes in this DOM realm.
(()=>{
const cfg=FLAME_CONFIG, canvas=document.querySelector('canvas'), status=document.querySelector('[role=status]');
let worker,game,rivePlayer,deadline=performance.now()+12000,ready=false,paused=!!cfg.reducedMotion,userPaused=!!cfg.reducedMotion,externallyHidden=false,disposed=false,messages=0,down=false,last={x:0,y:0},worldBodies=[],challenge=null,workerStarted=false;
const tell=(type,value)=>parent.postMessage({channel:'flame-simulation',nonce:cfg.nonce,type,value},'*');
const post=value=>worker?.postMessage(value);
const finite=(v,min,max)=>typeof v==='number'&&Number.isFinite(v)&&v>=min&&v<=max;
function stop(){if(disposed)return;disposed=true;post({type:'dispose'});worker?.terminate();game?.destroy(true);rivePlayer?.cleanup();clearInterval(watch);}
function fail(){stop();status.textContent='This simulation stopped. You can reset it.';tell('error');}
function markReady(){ready=true;status.textContent='';tell('ready');}
function phaserScene(value){
 if(game||!value||!Array.isArray(value.bodies)||value.bodies.length>50||!finite(value.gravity,0,3))throw Error();
 const bodies=value.bodies.map(b=>{
   if(!b||!finite(b.x,0,800)||!finite(b.y,0,450)||!finite(b.color,0,0xffffff)||!finite(b.restitution??.5,0,1)||!finite(b.friction??.1,0,1)||
      !(finite(b.radius,2,100)||(finite(b.width,2,200)&&finite(b.height,2,200)))||typeof(b.static??false)!=='boolean')throw Error();
   return b;
 });
 game=new Phaser.Game({type:Phaser.CANVAS,canvas,width:800,height:450,banner:false,audio:{noAudio:true},backgroundColor:'#f3f6fc',
  physics:{default:'matter',matter:{gravity:{y:value.gravity},debug:false}},
  scene:{create(){const scene=this;scene.matter.world.setBounds(0,0,800,450);worldBodies=bodies.map(b=>{const shape=b.radius?scene.add.circle(b.x,b.y,b.radius,b.color):scene.add.rectangle(b.x,b.y,b.width,b.height,b.color);return scene.matter.add.gameObject(shape,b.radius?{shape:{type:'circle',radius:b.radius},restitution:b.restitution??.5,friction:b.friction??.1,isStatic:b.static??false}:{restitution:b.restitution??.5,friction:b.friction??.1,isStatic:b.static??false});});scene.matter.add.mouseSpring({length:0,stiffness:.2});scene.matter.world.enabled=!paused;markReady();}}});
}
function riveInputs(v){
 if(!v||!finite(v.weather,0,4)||!Number.isInteger(v.weather)||!finite(v.wind??0,0,1))throw Error();
 const model=rivePlayer?.viewModelInstance;if(model){model.number('weatherIndex').value=v.weather;model.number('gustBend').value=(v.wind??0)*.3;}
}
function startRive(){
 const bytes=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0)).buffer;
 rive.RuntimeLoader.setWasmBinary(bytes(cfg.wasm));
 rivePlayer=new rive.Rive({buffer:bytes(cfg.art),canvas,artboard:'Weather World',stateMachines:'Weather States',autoplay:!paused,autoBind:true,enableRiveAssetCDN:false,
  layout:new rive.Layout({fit:rive.Fit.Contain}),onLoad:()=>{rivePlayer.resizeDrawingSurfaceToCanvas();if(!rivePlayer.viewModelInstance?.number('weatherIndex')){fail();return;}riveInputs({weather:0,wind:0});markReady();},onLoadError:fail});
}
const watch=setInterval(()=>{if(performance.now()>deadline){fail();return;}messages=0;if(workerStarted&&!challenge){challenge=Array.from(crypto.getRandomValues(new Uint32Array(4))).join('-');post({type:'ping',token:challenge});}},500);
const harden=`for(const name of ['Worker','SharedWorker','importScripts','fetch','XMLHttpRequest','WebSocket','EventSource','BroadcastChannel','indexedDB','caches','SharedArrayBuffer']){try{Object.defineProperty(globalThis,name,{value:undefined,writable:false,configurable:false});}catch{}}\n`;
try{
 if(!window.Worker||!canvas.transferControlToOffscreen)throw Error();
 const url=URL.createObjectURL(new Blob([harden,cfg.worker],{type:'text/javascript'}));
 worker=new Worker(url);URL.revokeObjectURL(url);
 worker.onerror=fail;worker.onmessage=({data})=>{
  try{
   if(++messages>160||!data||typeof data.type!=='string')throw Error();
   if(data.type==='heartbeat')return;
   if(data.type==='pong'){if(challenge&&data.token===challenge){challenge=null;deadline=performance.now()+2500;}return;}
   if(data.type==='runtime-error')throw Error();
   if(data.type==='ready'){if(workerStarted)return;workerStarted=true;deadline=performance.now()+2500;if(!['phaser','rive'].includes(cfg.engine))markReady();return;}
   if(data.type==='phaser'&&cfg.engine==='phaser'){phaserScene(data.value);return;}
   if(data.type==='rive'&&cfg.engine==='rive'){riveInputs(data.value);return;}
   if(data.type==='measurements'&&data.value&&typeof data.value==='object'&&!Array.isArray(data.value)){
    const fields=Object.entries(data.value);if(fields.length>12||!fields.every(([k,v])=>/^[a-zA-Z][a-zA-Z0-9_]{0,30}$/.test(k)&&finite(v,-1e9,1e9)))throw Error();
    document.querySelector('output').textContent=fields.map(([k,v])=>k+': '+v.toFixed(2)).join(' · ');tell('measurements',data.value);return;
   }
   throw Error();
  }catch{fail();}
 };
 if(cfg.engine==='rive')startRive();
 if(['phaser','rive'].includes(cfg.engine)){const offscreen=new OffscreenCanvas(800,450);worker.postMessage({type:'init',canvas:offscreen},[offscreen]);}
 else{const offscreen=canvas.transferControlToOffscreen();worker.postMessage({type:'init',canvas:offscreen},[offscreen]);}
}catch{fail();}
function pointer(e){const r=canvas.getBoundingClientRect(),x=(e.clientX-r.left)*800/r.width,y=(e.clientY-r.top)*450/r.height;
 if(e.type==='pointerdown'){down=true;canvas.setPointerCapture(e.pointerId);}
 if(e.type==='pointerup'||e.type==='pointercancel')down=false;
 post({type:'pointer',value:{type:e.type.replace('pointer',''),x,y,dx:x-last.x,dy:y-last.y,down}});last={x,y};}
for(const type of ['pointerdown','pointermove','pointerup','pointercancel'])canvas.addEventListener(type,pointer);
canvas.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();post({type:'pointer',value:{type:'move',x:400,y:225,dx:e.key==='ArrowLeft'?-15:e.key==='ArrowRight'?15:0,dy:e.key==='ArrowUp'?-15:e.key==='ArrowDown'?15:0,down:true,keyboard:true}});});
function pause(value,external=false){if(external)externallyHidden=value;else userPaused=value;paused=userPaused||externallyHidden;value=paused;post({type:'pause',value});if(game){for(const scene of game.scene.scenes)scene.matter.world.enabled=!value;}if(rivePlayer){if(value)rivePlayer.pause();else rivePlayer.play();}document.querySelector('#pause').textContent=value?'Resume':'Pause';}
document.querySelector('#pause').onclick=()=>pause(!paused);if(paused)pause(true);
const weather=document.querySelector('#weather');if(weather)weather.onchange=()=>riveInputs({weather:Number(weather.value),wind:Number(weather.value)===3?.6:0});
for(const name of ['gravity','friction'])document.querySelector('#'+name).oninput=e=>{const value=Number(e.target.value);document.querySelector('#'+name+'-value').textContent=value.toFixed(2);post({type:'control',name,value});if(game)for(const scene of game.scene.scenes){if(name==='gravity')scene.matter.world.setGravity(0,value);else{for(const b of worldBodies)b.setFriction(value);for(const b of scene.matter.world.localWorld.bodies)if(b.isStatic)b.friction=value;}}};
window.addEventListener('message',e=>{if(e.source!==parent||!e.data||e.data.nonce!==cfg.nonce)return;if(e.data.type==='dispose')stop();if(e.data.type==='visibility')pause(!!e.data.hidden,true);});
window.addEventListener('pagehide',stop);
})();
