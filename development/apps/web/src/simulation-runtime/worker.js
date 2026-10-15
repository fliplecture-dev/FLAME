// Everything in this bundle, including model top-level code, runs in a disposable worker.
import * as Fiber from 'flame-fiber';
import * as THREE from 'flame-three';
import Matter from 'flame-matter';
let api, instance, root, store, paused=false, tick=0, total=0;
let physics,dragged,lastReport,ownedRenderer;
function guardedRenderer(canvas){
 const renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:false});
 const render=renderer.render.bind(renderer),size=renderer.setSize.bind(renderer);
 renderer.setPixelRatio=()=>{};
 renderer.setSize=(w,h,style=false)=>{if(w>800||h>450||w<1||h<1)throw Error('canvas_limit');size(w,h,style);};
 renderer.render=(scene,camera)=>{let objects=0,vertices=0;scene.traverse(node=>{objects++;vertices+=node.geometry?.attributes?.position?.count??0;if(objects>200||vertices>200000)throw Error('scene_limit');});render(scene,camera);};
 return renderer;
}
const send = self.postMessage.bind(self);
const listen = self.addEventListener.bind(self);
const schedule = self.setInterval.bind(self);
const fail=()=>send({type:'runtime-error'});
listen('error',fail); listen('unhandledrejection',fail);
listen('message',async ({data})=>{
  try {
    if(data.type==='ping'){send({type:'pong',token:data.token});return;}
    if(data.type==='init') {
      const canvas=data.canvas;
      api={canvas,threeRenderer(){if(FLAME_ENGINE!=='three'||ownedRenderer)throw Error('renderer_limit');ownedRenderer=guardedRenderer(canvas);ownedRenderer.setSize(800,450,false);return ownedRenderer;},controls:{gravity:1,friction:.1},orbit:{azimuth:0,elevation:.4},
        matterWorld(){
          if(FLAME_ENGINE!=='matter'||physics)throw Error('physics_world_unavailable');
          physics=Matter.Engine.create();
          Matter.Composite.add(physics.world,[Matter.Bodies.rectangle(400,435,800,30,{isStatic:true,friction:.1}),Matter.Bodies.rectangle(-10,225,20,450,{isStatic:true}),Matter.Bodies.rectangle(810,225,20,450,{isStatic:true})]);
          return physics;
        },
        report(value){lastReport=value;if(tick%15===0)send({type:'measurements',value});},
        phaser(value){send({type:'phaser',value});},rive(value){send({type:'rive',value});},
        async render(element){
          Fiber.extend(THREE);
          root=Fiber.createRoot(canvas);
          await root.configure({size:{width:800,height:450,top:0,left:0},dpr:1,frameloop:'never',
            gl:()=>guardedRenderer(canvas),camera:{position:[0,6,12],fov:50},events:undefined});
          store=root.render(element);
        }};
      instance=await mount(api)||{};
      send({type:'ready'});
      schedule(()=>{
        try {
          tick++;
          if(!paused){total+=1/60;
            if(physics){const bodies=Matter.Composite.allBodies(physics.world);if(bodies.length>100)throw Error('body_limit');Matter.Engine.update(physics,1000/60);const c=canvas.getContext('2d');c.clearRect(0,0,800,450);for(const b of bodies){c.beginPath();for(const v of b.vertices)c.lineTo(v.x,v.y);c.closePath();c.fillStyle=b.isStatic?'#63738a':b.render.fillStyle||'#527bd8';c.fill();}}
            instance.update?.(1/60);if(store){const state=store.getState();const a=api.orbit.azimuth,e=api.orbit.elevation;state.camera.position.set(14*Math.sin(a)*Math.cos(e),14*Math.sin(e),14*Math.cos(a)*Math.cos(e));state.camera.lookAt(0,0,0);Fiber.advance(total,true);api.report({azimuth:a,elevation:e,objects:state.scene.children.length});}}
          // Heartbeats come from the work loop, not an independent timer hiding a stuck update.
          if(tick%15===0)send({type:'heartbeat'});
        }catch{fail();paused=true;}
      },1000/60);
    } else if(data.type==='pause'){paused=!!data.value;if(paused&&lastReport)send({type:'measurements',value:lastReport});}
    else if(data.type==='control'&&['gravity','friction'].includes(data.name)&&Number.isFinite(data.value)){
      api.controls[data.name]=data.value;instance.control?.(data.name,data.value);
      if(physics){if(data.name==='gravity')physics.gravity.y=data.value;else for(const b of Matter.Composite.allBodies(physics.world))b.friction=data.value;}
    } else if(data.type==='pointer'){
      if(paused)return;
      if(data.value.type==='move'&&data.value.down){api.orbit.azimuth+=data.value.dx*.01;api.orbit.elevation=Math.max(-1.3,Math.min(1.3,api.orbit.elevation+data.value.dy*.01));}
      if(physics){const p=data.value;if(p.keyboard){const b=Matter.Composite.allBodies(physics.world).find(b=>!b.isStatic);if(b){Matter.Body.translate(b,{x:p.dx,y:p.dy});Matter.Body.setVelocity(b,{x:0,y:0});}}if(p.type==='down')dragged=Matter.Query.point(Matter.Composite.allBodies(physics.world),p).find(b=>!b.isStatic);if(p.type==='move'&&dragged){Matter.Body.setPosition(dragged,{x:Math.max(0,Math.min(800,p.x)),y:Math.max(0,Math.min(420,p.y))});Matter.Body.setVelocity(dragged,{x:0,y:0});}if(p.type==='up'||p.type==='cancel')dragged=null;}
      instance.pointer?.(data.value);
    } else if(data.type==='dispose'){instance?.dispose?.();if(physics){Matter.Composite.clear(physics.world,false);Matter.Engine.clear(physics);}root?.unmount();ownedRenderer?.dispose();ownedRenderer?.forceContextLoss();self.close();}
  }catch{fail();}
});
